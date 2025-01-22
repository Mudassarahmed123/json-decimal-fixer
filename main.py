from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from typing import List
import shutil
from pathlib import Path
import tempfile

app = FastAPI(title="GeoJSON Decimal Places Fixer")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def count_decimal_places(num: float) -> int:
    str_num = str(abs(num))
    if '.' in str_num:
        return len(str_num.split('.')[1])
    return 0

def fix_coordinates(coordinates, min_decimals: int):
    if isinstance(coordinates, (int, float)):
        decimals = count_decimal_places(coordinates)
        if decimals < min_decimals:
            adjustment = 0.0000001 if coordinates >= 0 else -0.0000001
            return coordinates + adjustment
        return coordinates
    return [fix_coordinates(coord, min_decimals) for coord in coordinates]

def process_geojson(data: dict, min_decimals: int) -> dict:
    result = data.copy()
    for feature in result['features']:
        if 'geometry' in feature and 'coordinates' in feature['geometry']:
            feature['geometry']['coordinates'] = fix_coordinates(
                feature['geometry']['coordinates'],
                min_decimals
            )
    return result

@app.post("/process")
async def process_files(
    files: List[UploadFile] = File(...),
    min_decimals: int = 6,
    prefix: str = "fixed_"
):
    try:
        processed_files = []
        
        for file in files:
            # Read and process file
            content = await file.read()
            data = json.loads(content)
            processed_data = process_geojson(data, min_decimals)
            
            # Create processed filename
            processed_filename = f"{prefix}{file.filename}"
            
            # Store processed file info
            processed_files.append({
                "original_name": file.filename,
                "processed_name": processed_filename,
                "processed_data": processed_data
            })
        
        return JSONResponse({
            "status": "success",
            "message": f"Successfully processed {len(processed_files)} files",
            "processed_files": processed_files
        })
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)