# Standalone PDF Parser Testing

This folder contains standalone scripts to test and debug PDF parsing functionality without involving the main application or database.

## Quick Start

### Option 1: Interactive Runner (Easiest)
```bash
cd ElectOMate-Backend/test_parsing
python run_test.py
```
Then follow the prompts to enter your PDF file path.

### Option 2: Direct Command
```bash
cd ElectOMate-Backend/test_parsing
python run_test.py /path/to/your/document.pdf
```

### Option 3: Advanced Usage
```bash
cd ElectOMate-Backend/test_parsing
python standalone_parser.py /path/to/your/document.pdf --output-dir ./my_results
```

## Features

### 🔍 Enhanced Debugging
- **Page Number Extraction**: Deep debugging of why page numbers might be "unknown"
- **Provenance Analysis**: Detailed inspection of chunk provenance information
- **Attribute Discovery**: Automatic discovery of all available attributes on chunk objects
- **Debug Logging**: Comprehensive logging to both console and `debug.log` file

### 💾 Local Storage
- **JSON Results**: Complete parsing results saved as JSON
- **Markdown Content**: Extracted content saved as Markdown
- **Debug Information**: Detailed provenance debugging info
- **Organized Output**: All results stored in timestamped, organized structure

### 📊 Comprehensive Analysis
- **Token Counting**: Exact token counts for each chunk
- **Confidence Reporting**: Document parsing confidence metrics
- **Page Range Analysis**: Summary of page number extraction success
- **Chunk Statistics**: Detailed statistics about chunking results

## Files

- `run_test.py` - Interactive test runner (easiest to use)
- `standalone_parser.py` - Full-featured standalone parser with debugging
- `README.md` - This documentation
- `results/` - Output directory (created automatically)

## Output Structure

When you run a test, the following files are created in the `results/` directory:

```
results/
├── result_[uuid].json          # Complete parsing results
├── content_[uuid].md           # Extracted markdown content
├── debug_provenance.json       # Debug information (if debug mode enabled)
└── debug.log                   # Detailed debug logs
```

## Understanding the Results

### Main Result File (`result_[uuid].json`)
```json
{
  "result_id": "unique-identifier",
  "timestamp": "2025-10-20T...",
  "file_path": "/path/to/your/file.pdf",
  "confidence": {
    "mean_grade": "GOOD",
    "num_pages": 10
  },
  "chunk_count": 45,
  "chunks": [
    {
      "chunk_id": "unique-chunk-id",
      "text": "Actual chunk text...",
      "page_number": 1,  // or null if unknown
      "chunk_index": 0,
      "token_count": 247,
      "debug_info": { ... }  // if debug mode enabled
    }
  ]
}
```

### Debug Information
If debug mode is enabled, each chunk includes detailed debug information:

```json
{
  "debug_info": {
    "chunk_index": 0,
    "has_prov_attr": true,
    "prov_value": "...",
    "prov_type": "...",
    "page_extraction_attempts": [
      {
        "attribute": "page_no",
        "exists": true,
        "value": 1
      }
    ]
  }
}
```

## Troubleshooting Page Number Issues

If you're seeing "page unknown" in the logs, the debug information will help you understand why:

1. **Check `has_prov_attr`**: Does the chunk have provenance information at all?
2. **Check `page_extraction_attempts`**: Which attribute names were tried and what were their values?
3. **Check `debug.log`**: Look for detailed attribute dumps showing all available properties

Common issues and solutions:

- **No provenance**: The document structure doesn't include page information
- **Different attribute names**: The page number might be stored under a different attribute name
- **Null values**: Provenance exists but page numbers are null/empty

## Advanced Usage

### Custom Output Directory
```bash
python standalone_parser.py /path/to/file.pdf --output-dir /custom/output/path
```

### Disable Debug Mode (for faster processing)
```bash
python standalone_parser.py /path/to/file.pdf --no-debug
```

### Process Multiple Files
```bash
for file in /path/to/pdfs/*.pdf; do
    python standalone_parser.py "$file"
done
```

## Integration with Main System

Once you've identified and fixed page number extraction issues using this test system, you can apply the fixes to the main `DocumentParser` class in:
```
ElectOMate-Backend/src/em_backend/vector/parser.py
```

The standalone parser is designed to use the same chunking and parsing logic as the main system, so fixes should transfer directly.

## Requirements

This script uses the same dependencies as the main backend:
- docling
- docling-core
- tiktoken
- All other dependencies from the main backend

Make sure you're running this from within the backend's virtual environment:
```bash
cd ElectOMate-Backend
source venv/bin/activate  # or your venv activation command
cd test_parsing
python run_test.py
```



