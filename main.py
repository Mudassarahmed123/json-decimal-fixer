from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from typing import List, Dict, Any, Tuple, Union
from pathlib import Path
from shapely.geometry import shape

app = FastAPI(title="GeoJSON Tools")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a router for API endpoints
from fastapi import APIRouter
router = APIRouter()

class UnifiedValidator:
    ERROR_CODES = {
        'DUPLICATE_KEY': 23,
        'MULTIPLE_ROOT': 22,
        'UNEXPECTED_BRACKET_CLOSE': 7,
        'UNEXPECTED_BRACE_CLOSE': 6,
        'MISSING_QUOTES': 4,
        'TRAILING_COMMA': 5
    }

    VALIDATION_CRITERIA = {
        'invalid': {
            'unclosed': {'relevant': ['Polygon'], 'input': 'json_geometry'},
            'less_three_unique_nodes': {'relevant': ['Polygon'], 'input': 'json_geometry'},
            'exterior_not_ccw': {'relevant': ['Polygon'], 'input': 'shapely_geom'},
            'interior_not_cw': {'relevant': ['Polygon'], 'input': 'shapely_geom'},
            'inner_and_exterior_ring_intersect': {'relevant': ['Polygon'], 'input': 'shapely_geom'}
        },
        'problematic': {
            'holes': {'relevant': ['Polygon'], 'input': 'shapely_geom'},
            'self_intersection': {'relevant': ['Polygon'], 'input': 'shapely_geom'},
            'duplicate_nodes': {'relevant': ['LineString', 'Polygon'], 'input': 'json_geometry'},
            'excessive_coordinate_precision': {'relevant': ['Point', 'LineString', 'Polygon'], 'input': 'json_geometry'},
            'excessive_vertices': {'relevant': ['LineString', 'Polygon'], 'input': 'json_geometry'},
            '3d_coordinates': {'relevant': ['Point', 'LineString', 'Polygon'], 'input': 'json_geometry'},
            'outside_lat_lon_boundaries': {'relevant': ['Point', 'LineString', 'Polygon'], 'input': 'json_geometry'},
            'crosses_antimeridian': {'relevant': ['LineString', 'Polygon'], 'input': 'json_geometry'}
        }
    }

    def get_line_col(self, text: str, pos: int) -> Tuple[int, int]:
        """Convert character position to line and column numbers."""
        lines = text[:pos+1].splitlines()
        if not lines:
            return 1, 1
        line_num = len(lines)
        col_num = len(lines[-1])
        return line_num, col_num

    def format_error_message(self, code: int, pos: int, json_input: str, context: str = "") -> str:
        """Format error message with location and context."""
        line_num, col_num = self.get_line_col(json_input, pos)
        desc = self.ERROR_DESCRIPTIONS.get(code, "Unknown error")
        
        lines = json_input.splitlines()
        if 0 <= line_num-1 < len(lines):
            error_line = lines[line_num-1]
            if len(error_line) > 100:
                if col_num > 80:
                    error_line = "..." + error_line[col_num-40:col_num+40] + "..."
                    col_num = 43
                else:
                    error_line = error_line[:100] + "..."
            
            pointer = " " * (col_num-1) + "^"
            context_msg = f"\nAt line {line_num}, column {col_num}:\n{error_line}\n{pointer}"
            if context:
                context_msg += f"\nContext: {context}"
        else:
            context_msg = f"\nAt position {pos}"
        
        return f"{desc}{context_msg}"

    def validate_json_structure(self, json_input: str) -> List[Dict]:
        """Validate JSON structure and return list of errors."""
        errors = []
        structure_count = 0
        error_count = 0
        ERROR_LIMIT = 500

        try:
            # Quick validation attempt first
            try:
                json.loads(json_input)
                return []  # Return empty list if JSON is valid
            except json.JSONDecodeError as e:
                errors.append({
                    'code': 1,
                    'structure': structure_count,
                    'position': e.pos,
                    'context': e.msg
                })
                structure_count += 1
                error_count += 1

            # Additional structure validation
            stack = []
            positions = []
            root_count = 0
            
            for i, char in enumerate(json_input):
                if char in '{[':
                    if not stack:
                        root_count += 1
                        if root_count > 1:
                            errors.append({
                                'code': self.ERROR_CODES['MULTIPLE_ROOT'],
                                'structure': structure_count,
                                'position': i,
                                'context': f"Found another root element starting with '{char}'"
                            })
                            structure_count += 1
                            error_count += 1
                    stack.append(char)
                    positions.append(i)
                elif char in '}]':
                    if not stack:
                        code = self.ERROR_CODES['UNEXPECTED_BRACE_CLOSE'] if char == '}' else self.ERROR_CODES['UNEXPECTED_BRACKET_CLOSE']
                        errors.append({
                            'code': code,
                            'structure': structure_count,
                            'position': i,
                            'context': f"Found closing '{char}' without matching opening bracket/brace"
                        })
                        structure_count += 1
                        error_count += 1
                    elif stack and ((stack[-1] == '{' and char == '}') or (stack[-1] == '[' and char == ']')):
                        stack.pop()
                        positions.pop()
                    else:
                        errors.append({
                            'code': self.ERROR_CODES['UNEXPECTED_BRACKET_CLOSE'],
                            'structure': structure_count,
                            'position': i,
                            'context': f"Expected closing '{']' if stack[-1] == '[' else '}'}'  but found '{char}'"
                        })
                        structure_count += 1
                        error_count += 1
                        if stack:
                            stack.pop()
                            positions.pop()

                if error_count >= ERROR_LIMIT:
                    break

        except Exception as e:
            errors.append({
                'code': 1,
                'structure': structure_count,
                'position': 0,
                'context': str(e)
            })

        return errors

    def validate_geometry(self, geojson_data: Dict) -> Dict[str, Any]:
        """Validate GeoJSON geometry and return validation results."""
        results = {
            "valid": True,
            "errors": [],
            "problematic": {},
            "invalid": {},
            "feature_count": 0,
            "geometry_types": {},
            "skipped_validation": []
        }
        
        try:
            if geojson_data.get("type") == "FeatureCollection":
                features = geojson_data.get("features", [])
                results["feature_count"] = len(features)
                
                for i, feature in enumerate(features):
                    if "geometry" not in feature:
                        results["invalid"].setdefault("missing_geometry", []).append(i)
                        results["valid"] = False
                        continue
                        
                    geometry = feature.get("geometry", {})
                    geom_type = geometry.get("type")
                    
                    if geom_type:
                        results["geometry_types"][geom_type] = results["geometry_types"].get(geom_type, 0) + 1
                    
                    try:
                        if geometry and geometry.get("coordinates"):
                            # Check for less than three unique nodes in polygons
                            if geom_type == "Polygon":
                                coords = geometry["coordinates"][0]  # Exterior ring
                                unique_coords = {tuple(c) for c in coords}
                                if len(unique_coords) < 3:
                                    results["invalid"].setdefault("less_three_unique_nodes", []).append(i)
                                    results["valid"] = False
                            
                            # Create Shapely geometry for additional checks
                            geom = shape(geometry)
                            
                            # Check if geometry is valid
                            if not geom.is_valid:
                                results["invalid"].setdefault("invalid_geometry", []).append(i)
                                results["valid"] = False
                            
                            # Check for self-intersections
                            if geom_type in ["LineString", "Polygon"] and not geom.is_simple:
                                results["problematic"].setdefault("self_intersection", []).append(i)
                            
                            # Check for holes in polygons
                            if geom_type == "Polygon" and len(geometry["coordinates"]) > 1:
                                results["problematic"].setdefault("holes", []).append(i)
                            
                            # Check coordinate precision and boundaries
                            self._check_coordinates(geometry["coordinates"], i, results)
                            
                    except Exception as e:
                        results["invalid"].setdefault("geometry_error", []).append(i)
                        results["errors"].append(f"❌ Feature {i}: {str(e)}")
                        results["valid"] = False
            
            elif geojson_data.get("type") == "Feature":
                results["feature_count"] = 1
                geometry = geojson_data.get("geometry", {})
                geom_type = geometry.get("type")
                
                if geom_type:
                    results["geometry_types"][geom_type] = 1
                
                try:
                    if geometry and geometry.get("coordinates"):
                        # Similar checks as above for single feature
                        if geom_type == "Polygon":
                            coords = geometry["coordinates"][0]
                            unique_coords = {tuple(c) for c in coords}
                            if len(unique_coords) < 3:
                                results["invalid"].setdefault("less_three_unique_nodes", []).append(0)
                                results["valid"] = False
                        
                        geom = shape(geometry)
                        if not geom.is_valid:
                            results["invalid"].setdefault("invalid_geometry", []).append(0)
                            results["valid"] = False
                        
                        self._check_coordinates(geometry["coordinates"], 0, results)
                        
                except Exception as e:
                    results["invalid"].setdefault("geometry_error", []).append(0)
                    results["errors"].append(f"❌ Error: {str(e)}")
                    results["valid"] = False
        
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"❌ Error validating geometry: {str(e)}")
        
        return results

    def _check_coordinates(self, coordinates: Union[List, Tuple], feature_index: int, results: Dict):
        """Check coordinates for various issues."""
        def check_coord(coord):
            # Check coordinate precision
            if any(len(str(c).split('.')[-1]) > 7 for c in coord[:2]):
                results["problematic"].setdefault("excessive_coordinate_precision", []).append(feature_index)
            
            # Check for 3D coordinates
            if len(coord) > 2:
                results["problematic"].setdefault("3d_coordinates", []).append(feature_index)
            
            # Check lat/lon boundaries
            if abs(coord[1]) > 90 or abs(coord[0]) > 180:
                results["problematic"].setdefault("outside_lat_lon_boundaries", []).append(feature_index)

        if isinstance(coordinates[0], (int, float)):
            check_coord(coordinates)
        else:
            for coord in coordinates:
                if isinstance(coord[0], (int, float)):
                    check_coord(coord)
                else:
                    self._check_coordinates(coord, feature_index, results)

validator = UnifiedValidator()

@router.post("/validate")
async def validate_file(file: UploadFile = File(...)):
    """Endpoint to validate JSON/GeoJSON files."""
    try:
        content = await file.read()
        content_str = content.decode()
        
        # Validate JSON structure
        structure_errors = validator.validate_json_structure(content_str)
        
        if structure_errors:
            error_messages = []
            for error in structure_errors:
                error_msg = validator.format_error_message(
                    error['code'],
                    error['position'],
                    content_str,
                    error.get('context', '')
                )
                error_messages.append(f"Error [Code {error['code']}]:\n{error_msg}")
            
            return JSONResponse({
                "structure_valid": False,
                "structure_errors": "\n\n".join(error_messages),
                "is_geojson": False
            })
        
        # Parse JSON and check if it's GeoJSON
        data = json.loads(content_str)
        is_geojson = isinstance(data, dict) and data.get("type") in ["Feature", "FeatureCollection"]
        
        if is_geojson:
            # Validate geometry
            geometry_validation = validator.validate_geometry(data)
            
            # Format geometry validation results
            geometry_details = []
            
            if geometry_validation["invalid"]:
                geometry_details.append("\n🔴 Invalid Geometry Issues:")
                for issue, features in geometry_validation["invalid"].items():
                    issue_name = ' '.join(word.capitalize() for word in issue.split('_'))
                    geometry_details.append(f"  • {issue_name} in feature(s): {', '.join(map(str, features))}")
            
            if geometry_validation["problematic"]:
                geometry_details.append("\n🟡 Problematic Geometry Issues:")
                for issue, features in geometry_validation["problematic"].items():
                    issue_name = ' '.join(word.capitalize() for word in issue.split('_'))
                    geometry_details.append(f"  • {issue_name} in feature(s): {', '.join(map(str, features))}")
            
            if geometry_validation["errors"]:
                geometry_details.extend(geometry_validation["errors"])
            
            # Add feature summary
            geometry_details.append(f"\n📊 Feature Summary:")
            geometry_details.append(f"  • Total Features: {geometry_validation['feature_count']}")
            for geom_type, count in geometry_validation["geometry_types"].items():
                geometry_details.append(f"  • {geom_type}: {count} feature(s)")
            
            # Add final validation result
            if not geometry_validation["valid"]:
                geometry_details.append("\n❌ Final Result: Some geometries need fixing.")
            else:
                geometry_details.append("\n✅ Final Result: All geometries are valid.")
            
            return JSONResponse({
                "structure_valid": True,
                "is_geojson": True,
                "geometry_valid": geometry_validation["valid"],
                "feature_count": geometry_validation["feature_count"],
                "geometry_types": geometry_validation["geometry_types"],
                "invalid": geometry_validation["invalid"],
                "problematic": geometry_validation["problematic"],
                "errors": geometry_validation["errors"]
            })
        else:
            return JSONResponse({
                "structure_valid": True,
                "is_geojson": False,
                "message": "This is a valid JSON file but not a GeoJSON file"
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def count_decimal_places(num):
    """Count the number of decimal places in a number."""
    str_num = str(abs(float(num)))
    if '.' in str_num:
        decimals = len(str_num.split('.')[1])
        # Remove trailing zeros
        str_decimals = str_num.split('.')[1].rstrip('0')
        return len(str_decimals) if str_decimals else 0
    return 0

def fix_coordinates(coordinates, min_decimals):
    """Fix coordinates to have exactly the specified number of decimal places."""
    if isinstance(coordinates, (int, float)):
        str_num = str(abs(float(coordinates)))
        parts = str_num.split('.')
        
        # Handle cases with no decimal point
        if len(parts) == 1:
            parts.append('0')
            
        whole = parts[0]
        decimal = parts[1] if len(parts) > 1 else ''
        
        # If we have fewer decimals than required
        if len(decimal) < min_decimals:
            # Pad with zeros first
            decimal = decimal.ljust(min_decimals - 1, '0')
            # Add '1' at the end
            decimal = decimal + '1'
            # Construct the new number
            result = float(f"{whole}.{decimal}")
            # Apply original sign
            return -result if coordinates < 0 else result
        else:
            # Just format to required decimals
            format_str = f"{{:.{min_decimals}f}}"
            return float(format_str.format(float(coordinates)))
    elif isinstance(coordinates, list):
        return [fix_coordinates(coord, min_decimals) for coord in coordinates]
    return coordinates

def process_geojson(data: Dict, min_decimals: int) -> Dict:
    """Process GeoJSON coordinates to fix decimal places."""
    if not isinstance(data, dict):
        return data
        
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        for feature in features:
            if feature.get("geometry") and feature["geometry"].get("coordinates"):
                feature["geometry"]["coordinates"] = fix_coordinates(
                    feature["geometry"]["coordinates"],
                    min_decimals
                )
    elif data.get("type") == "Feature":
        if data.get("geometry") and data["geometry"].get("coordinates"):
            data["geometry"]["coordinates"] = fix_coordinates(
                data["geometry"]["coordinates"],
                min_decimals
            )
    
    return data

@router.post("/process")
async def process_files(
    files: List[UploadFile] = File(...),
    min_decimals: int = Form(...),
    prefix: str = Form(...)
):
    """Process uploaded GeoJSON files."""
    results = {}
    
    # Ensure prefix ends with underscore
    if not prefix:
        prefix = "fixed_"
    elif not prefix.endswith('_'):
        prefix = f"{prefix}_"
    
    for file in files:
        try:
            content = await file.read()
            content_str = content.decode()
            
            # Parse JSON
            try:
                data = json.loads(content_str)
            except json.JSONDecodeError as e:
                results[file.filename] = {
                    "success": False,
                    "message": f"Invalid JSON: {str(e)}"
                }
                continue
            
            # Validate if it's a GeoJSON file
            if not isinstance(data, dict) or data.get("type") not in ["Feature", "FeatureCollection"]:
                results[file.filename] = {
                    "success": False,
                    "message": "File is not a valid GeoJSON file"
                }
                continue
            
            # Process GeoJSON
            try:
                processed_data = process_geojson(data, min_decimals)
                
                # Create output filename with prefix
                output_filename = f"{prefix}{file.filename}"
                
                # Convert processed data back to JSON string
                processed_json = json.dumps(processed_data, indent=2)
                
                results[file.filename] = {
                    "success": True,
                    "message": f"Successfully processed file",
                    "filename": output_filename,
                    "data": processed_json
                }
            except Exception as e:
                results[file.filename] = {
                    "success": False,
                    "message": f"Error processing file: {str(e)}"
                }
                
        except Exception as e:
            results[file.filename] = {
                "success": False,
                "message": f"Error reading file: {str(e)}"
            }
    
    return results

@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a processed file."""
    try:
        return FileResponse(
            file_path,
            media_type='application/json',
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

# Mount static files and router
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

@app.get("/")
async def root():
    """Serve the main HTML page."""
    with open("static/index.html") as f:
        content = f.read()
    return HTMLResponse(content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)