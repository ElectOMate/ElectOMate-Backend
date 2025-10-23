#!/usr/bin/env python3
"""
Download Docling Models

This script downloads the required docling models for PDF parsing.
Run this before using the standalone parser for the first time.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_docling_models():
    """Download docling models."""
    logger.info("🔽 Starting docling model download...")
    
    try:
        from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
        
        cache_path = Path.home() / ".cache" / "docling" / "models"
        logger.info(f"📁 Model cache path: {cache_path}")
        
        # This will trigger the download if models don't exist
        logger.info("🔧 Initializing LayoutPredictor (this will download models)...")
        predictor = LayoutPredictor(artifact_path=str(cache_path))
        
        logger.info("✅ SUCCESS: Docling models downloaded successfully!")
        logger.info(f"📦 Models stored in: {cache_path}")
        
        # Check what files were created
        if cache_path.exists():
            logger.info("📋 Downloaded files:")
            for file in cache_path.rglob("*"):
                if file.is_file():
                    size = file.stat().st_size / (1024 * 1024)  # MB
                    logger.info(f"   ✅ {file.name} ({size:.2f} MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ FAILED: Could not download models: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DOCLING MODEL DOWNLOADER")
    print("=" * 60)
    print()
    
    success = download_docling_models()
    
    print()
    if success:
        print("✅ SUCCESS: Models downloaded successfully!")
        print("You can now run the standalone parser.")
    else:
        print("❌ FAILED: Model download failed.")
        print("Please check the error messages above.")
        print()
        print("Alternative solution:")
        print("Run this command to download models:")
        print("  python -c 'from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor; LayoutPredictor()'")
    
    print("=" * 60)




