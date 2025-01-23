# GeoJSON Tools

A web application that provides tools for working with GeoJSON files:
1. **GeoJSON Decimal Fixer**: Fix decimal places in GeoJSON coordinates to meet EUDR requirements
2. **GeoJSON Validator**: Validate GeoJSON structure and geometry

## Features

### GeoJSON Decimal Fixer
- 🌐 Web-based interface accessible from any browser
- 📁 Drag-and-drop file upload
- 📂 Process multiple files simultaneously
- 📁 Support for both individual files and directory uploads
- ⚙️ Configurable decimal places (1-10) and output prefix
- 💾 Immediate file download after processing
- 📱 Responsive design works on all devices
- 🚀 Fast processing with progress tracking
- ❌ Comprehensive error handling

### GeoJSON Validator
- Comprehensive validation of GeoJSON files:
  - JSON structure validation
  - GeoJSON format validation
  - Geometry validation
- Detailed validation results including:
  - Feature count and types
  - Invalid geometry issues
  - Interactive map preview of valid geometries
- Visual feedback with color-coded results
- OpenStreetMap integration for geometry visualization

## Live Demo

Access the live application at: [https://json-decimal-fixer.onrender.com]

## Local Development

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Mudassarahmed123/json-decimal-fixer.git
cd json-decimal-fixer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn main:app --reload
```

4. Open your browser and navigate to:
```
http://localhost:8000
```

### Docker Setup

1. Build the Docker image:
```bash
docker build -t geojson-fixer .
```

2. Run the container:
```bash
docker run -p 8000:8000 geojson-fixer
```

## Usage

### Decimal Fixer
1. Upload files:
   - Drag and drop files or click to select
   - Select a directory for batch processing
2. Configure settings:
   - Set minimum decimal places (1-10)
   - Set output file prefix (optional)
3. Click "Process Files"
4. Download processed files

### JSON Validator
1. Select a GeoJSON file
2. Click "Validate File"
3. View validation results and map preview

## API Documentation

### Endpoints

`POST /process`
- Process GeoJSON files to fix decimal places

Parameters:
- `files`: List of GeoJSON files (multipart/form-data)
- `min_decimals`: Minimum number of decimal places (default: 6)
- `prefix`: Prefix for processed files (default: "fixed_")

Response:
```json
{
    "status": "success",
    "message": "Successfully processed X files",
    "processed_files": [
        {
            "original_name": "input.geojson",
            "processed_name": "fixed_input.geojson",
            "processed_data": {...}
        }
    ]
}
```

## Project Structure
```
geojson-decimal-fixer/
├── main.py              # FastAPI backend
├── static/
│   └── index.html      # Frontend interface
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
└── README.md           # Documentation
```

## Dependencies
- FastAPI
- Uvicorn
- Python Multipart
- Shapely
- OpenLayers (for map visualization)

## Error Handling
The application handles various types of errors:
- Invalid JSON structure
- Invalid GeoJSON format
- Invalid geometries
- File processing errors
- Coordinate system issues

## Deployment

### Deploying to Render
1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Configure:
   - Environment: Docker
   - Build Command: `docker build -t app .`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For support, please open an issue in the GitHub repository.

## Acknowledgments
- Built with FastAPI
- Frontend styled with Tailwind CSS
- Deployed on Render

## Author
Mudassar Ahmad

---
⭐ Star this repository if you find it helpful!
