# GeoJSON Tools

A web application that provides tools for working with GeoJSON files:
1. **GeoJSON Decimal Fixer**: Fix decimal places in GeoJSON coordinates
2. **GeoJSON Validator**: Validate GeoJSON structure and geometry

## Features

### GeoJSON Decimal Fixer
- Fix decimal places in GeoJSON coordinates to a specified precision
- Batch processing of multiple files
- Support for both individual files and directory uploads
- Drag and drop interface
- Customizable output file prefix
- Download processed files directly

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

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Mudassarahmed123/json-decimal-fixer.git
cd json-decimal-fixer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Open your browser and navigate to:
```
http://localhost:8080
```

3. Use the tools:
   - **Decimal Fixer**:
     - Select files or a directory
     - Set minimum decimal places (1-10)
     - Set output file prefix (optional)
     - Click "Process Files"
     - Download processed files
   
   - **JSON Validator**:
     - Select a GeoJSON file
     - Click "Validate File"
     - View validation results and map preview

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

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

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
