from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from typing import List
import shutil
from pathlib import Path

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
app.mount("/", StaticFiles(directory="static", html=True), name="root")

# Process directory function
def process_directory(directory_path: str, min_decimals: int) -> List[dict]:
    processed_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(('.json', '.geojson')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    processed_data = process_geojson(data, min_decimals)
                    processed_files.append({
                        "original_name": file,
                        "processed_name": f"fixed_{file}",
                        "processed_data": processed_data
                    })
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")
    return processed_files

@app.post("/process")
async def process_files(
    files: List[UploadFile] = File(...),
    min_decimals: int = Form(6),
    prefix: str = Form("fixed_")
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    try:
        processed_files = []
        
        for file in files:
            if not (file.filename.endswith('.json') or file.filename.endswith('.geojson')):
                continue

            try:
                content = await file.read()
                try:
                    data = json.loads(content.decode())
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a valid text file")
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not valid JSON")

                if 'features' not in data:
                    raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a valid GeoJSON file")

                processed_data = process_geojson(data, min_decimals)
                
                processed_files.append({
                    "original_name": file.filename,
                    "processed_name": f"{prefix}{file.filename}",
                    "processed_data": processed_data
                })
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        if not processed_files:
            raise HTTPException(status_code=400, detail="No valid GeoJSON files were found to process")
            
        return JSONResponse({
            "status": "success",
            "message": f"Successfully processed {len(processed_files)} files",
            "processed_files": processed_files
        })
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

def count_decimal_places(num):
    str_num = str(abs(num))
    if '.' in str_num:
        return len(str_num.split('.')[1])
    return 0

def fix_coordinates(coordinates, min_decimals):
    if isinstance(coordinates, (int, float)):
        decimals = count_decimal_places(coordinates)
        if decimals < min_decimals:
            adjustment = 0.0000001 if coordinates >= 0 else -0.0000001
            return coordinates + adjustment
        return coordinates
    return [fix_coordinates(coord, min_decimals) for coord in coordinates]

def process_geojson(data, min_decimals):
    result = data.copy()
    for feature in result['features']:
        if 'geometry' in feature and 'coordinates' in feature['geometry']:
            feature['geometry']['coordinates'] = fix_coordinates(
                feature['geometry']['coordinates'],
                min_decimals
            )
    return result



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)