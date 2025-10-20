# Setup Instructions for PDF Parsing Tests

## 🔴 Important: Model Requirements

The docling library requires AI models that are ~500MB and need to be downloaded. The easiest way to use this testing framework is **within your Docker container** where models are already configured.

##  Quick Start (Recommended: Use Docker)

```bash
# 1. Start your backend Docker container
docker-compose up -d

# 2. Copy test script into container
docker cp test_parsing/standalone_parser.py electomate-backend:/app/test_parsing/

# 3. Run inside Docker where models are configured
docker exec electomate-backend python /app/test_parsing/standalone_parser.py /path/to/your/pdf
```

## ⚙️ What We Created

### 1. **standalone_parser.py** - Full Testing Script
- ✅ Enhanced logging with emojis (✅/❌) for success/failure
- ✅ Deep page number extraction debugging
- ✅ Detailed chunk previews (first 5 chunks)
- ✅ Comprehensive statistics
- ✅ Multiple extraction methods
- ✅ Uses GPT-4o tokenization

### 2. **Features**
- **📋 Chunk Previews**: Shows first 5 chunks with all metadata
- **🔍 Provenance Debugging**: Deep analysis of why page numbers are/aren't extracted
- **📊 Statistics**: Token counts, page ranges, success rates
- **💾 Local Storage**: All results saved as JSON + Markdown + Summary
- **📝 Human-Readable Summary**: Easy-to-read .txt file with key info

### 3. **Output Files**
When you run a test, you'll get:
- `result_[uuid].json` - Complete results with all chunks
- `content_[uuid].md` - Extracted markdown content
- `summary_[uuid].txt` - Human-readable summary
- `debug_provenance.json` - Detailed provenance debugging
- `debug.log` - Full debug logs
- `detailed_debug.log` - Even more detailed logs

## 📊 What You'll See

### Console Output
```
🚀 INITIALIZING StandaloneDocumentParser...
✅ SUCCESS: DocumentConverter initialized successfully
✅ SUCCESS: Tiktoken encoding initialized for model: gpt-4o
✅ SUCCESS: HybridChunker initialized successfully

📁 Starting document parsing from file: document.pdf
📊 File info:
   - Name: document.pdf
   - Size: 477,357 bytes (466.2 KB)
✅ Document conversion completed successfully!

🧩 STARTING DOCUMENT CHUNKING...
✅ SUCCESS: Generated chunk 0.0: 247 tokens, page 1
📋 CHUNK PREVIEW
   🔢 Chunk ID: abc-123
   📍 Position: Chunk 0, Segment 0
   📄 Page Number: 1
   🔤 Token Count: 247
   📖 Text Preview: "This is the beginning of the document..."

📊 CHUNKING SUMMARY
   ✅ Chunks with page numbers: 85 (81.7%)
   ❌ Chunks without page numbers: 19 (18.3%)
```

### Debug Information
For each chunk without a page number, you'll see:
- Whether provenance exists
- All provenance attributes and their values
- Which page extraction methods were tried
- Why each method failed

## 🐛 Troubleshooting

### Problem: Missing model.safetensors

**Solution**: Run in Docker where models are configured, OR install models manually (see below)

### Problem: Can't use Docker

If you must run locally, you need to download docling models. This is complex and not officially documented. The models are part of IBM's DocLayout system.

### Problem: Page numbers showing as "unknown"

This is exactly what we're debugging! The test script will show you:
1. Whether chunks have provenance data
2. What attributes are available
3. Which extraction methods were tried
4. Why they failed

## 📝 Example Usage in Docker

```bash
# Start your backend
cd ElectOMate-Backend
docker-compose up -d

# Run test on a PDF
docker exec -it electomate-backend bash
cd /app
python test_parsing/standalone_parser.py /path/to/manifesto.pdf

# Check results
ls -lh test_parsing/results/
cat test_parsing/results/summary_*.txt
```

## 🎯 Next Steps

1. **Run a test in Docker** on one of your problematic PDFs
2. **Check the logs** - look for the detailed provenance analysis
3. **Check `debug_provenance.json`** - see exactly what attributes are available
4. **Apply the fix** - once you understand why page numbers aren't extracted, update the main `DocumentParser`

## 💡 Key Features for Debugging

### Multi-Method Page Extraction
The script tries multiple ways to get page numbers:
1. `provenance.page_no`
2. `provenance.page_number`
3. `provenance.page`
4. `provenance.page_num`
5. `provenance.page_idx`
6. `chunk.page` (direct attribute)
7. Parent/container analysis

### Detailed Attribute Dumping
For each chunk, it logs:
- ALL available attributes (not just page-related)
- Attribute types
- Attribute values
- Whether they're callable or data

### Success Rate Tracking
- Percentage of chunks with pages
- Percentage without pages
- Page ranges
- Unique page count

## 📞 Support

If you're still having issues:
1. Check `debug.log` in the test_parsing folder
2. Check `detailed_debug.log` for even more info
3. Look at the provenance dump in `debug_provenance.json`
4. The emoji logging (✅/❌) makes it easy to spot where things fail

##  Files in This Folder

- `standalone_parser.py` - Main test script (full featured)
- `run_test.py` - Interactive test runner
- `test.sh` - Shell script wrapper
- `example_usage.py` - Programmatic usage examples
- `download_models.py` - Model download helper (doesn't work without proper HF repo)
- `use_backend_parser.py` - Uses actual backend parser (requires env vars)
- `README.md` - General documentation
- `SETUP_INSTRUCTIONS.md` - This file

## ✅ Summary

**Best Practice**: Run these tests in your Docker environment where everything is configured. The standalone parser provides extensive debugging to help you understand why page numbers aren't being extracted, which you can then fix in the main backend code.

