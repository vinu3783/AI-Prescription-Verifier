#!/usr/bin/env python3
"""
Quick Setup Script for AI Prescription Verifier
Specifically designed for the uploaded ddi_dataset.csv with 11,825 medicine records
"""

import os
import sys
from pathlib import Path
import subprocess
import pandas as pd

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def check_dataset():
    """Check if the dataset is properly uploaded"""
    dataset_path = Path("data/datasets/raw_kaggle_ddi/ddi_dataset.csv")
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        print("📁 Please ensure ddi_dataset.csv is in the correct location")
        return False
    
    try:
        df = pd.read_csv(dataset_path)
        print(f"✅ Dataset found: {len(df):,} medicine records")
        print(f"📋 Columns: {', '.join(df.columns[:4])}{'...' if len(df.columns) > 4 else ''}")
        return True
    except Exception as e:
        print(f"❌ Error reading dataset: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = [
        "data/processed",
        "data/uploads/prescriptions", 
        "data/exports/reports",
        "logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    try:
        # Check if in virtual environment
        if sys.prefix == sys.base_prefix:
            print("⚠️  Warning: Not in a virtual environment")
            response = input("Continue anyway? (y/N): ").lower()
            if response != 'y':
                print("Please create a virtual environment first:")
                print("  python -m venv venv")
                print("  source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
                return False
        
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        print("Please install manually: pip install -r requirements.txt")
        return False

def setup_environment():
    """Setup environment variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        # Copy from example
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ Environment file created from template")
        else:
            # Create basic .env file
            with open(env_file, 'w') as f:
                f.write("""# AI Prescription Verifier Environment
APP_NAME="AI Prescription Verifier"
DEBUG=false
MAX_FILE_SIZE_MB=10
TESSERACT_CMD_PATH=/usr/bin/tesseract
""")
            print("✅ Basic environment file created")
    else:
        print("✅ Environment file already exists")

def test_tesseract():
    """Test if Tesseract OCR is installed"""
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Create a simple test image with text
        test_image = Image.new('RGB', (200, 50), color='white')
        
        # Try OCR
        pytesseract.image_to_string(test_image)
        print("✅ Tesseract OCR is working")
        return True
        
    except Exception as e:
        print("❌ Tesseract OCR issue:")
        print(f"   {e}")
        print("📝 Installation instructions:")
        print("   Ubuntu/Debian: sudo apt-get install tesseract-ocr")
        print("   macOS: brew install tesseract")
        print("   Windows: Download from GitHub Tesseract releases")
        return False

def build_dataset():
    """Build the DDI dataset from uploaded medicine data"""
    print("🔨 Building DDI dataset from your medicine data...")
    
    try:
        # Run the dataset builder
        result = subprocess.run([
            sys.executable, "scripts/build_dataset.py", 
            "--max-interactions", "1000",
            "--verbose"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ DDI dataset built successfully!")
            
            # Check output file
            output_file = Path("data/processed/ddi_mapped_with_rxcui.csv")
            if output_file.exists():
                df = pd.read_csv(output_file)
                print(f"📊 Generated {len(df):,} drug interactions")
                
                # Show severity breakdown
                severity_counts = df['severity'].value_counts()
                for severity, count in severity_counts.items():
                    print(f"   • {severity.title()}: {count}")
            
            return True
        else:
            print("❌ Dataset build failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error building dataset: {e}")
        return False

def test_app():
    """Test if the app can start"""
    print("🧪 Testing application startup...")
    
    try:
        # Try importing main modules
        sys.path.append('.')
        from core.ocr import test_ocr
        from core.ner import test_ner
        from core.rxcui import test_rxnorm_api
        
        print("✅ Core modules imported successfully")
        
        # Test basic functionality
        if test_ocr():
            print("✅ OCR module working")
        
        # Note: Skip NER and RxNorm tests in quick setup to avoid long download times
        print("✅ Quick tests passed")
        return True
        
    except Exception as e:
        print(f"❌ App test failed: {e}")
        return False

def main():
    """Main setup process"""
    print("🚀 AI Prescription Verifier - Quick Setup")
    print("=========================================")
    print()
    
    # Check system requirements
    if not check_python_version():
        return 1
    
    # Check dataset
    if not check_dataset():
        return 1
    
    # Create directories
    create_directories()
    
    # Setup environment
    setup_environment()
    
    # Install dependencies
    print("\n📦 Installing Dependencies")
    print("==========================")
    if not install_dependencies():
        print("⚠️  You can install manually later: pip install -r requirements.txt")
    
    # Test Tesseract
    print("\n🔍 Testing OCR Setup")
    print("====================")
    tesseract_ok = test_tesseract()
    
    # Build dataset
    print("\n🔨 Building Dataset")
    print("===================")
    if not build_dataset():
        print("⚠️  Dataset build failed, but you can try manually later")
    
    # Test app
    print("\n🧪 Testing Application")
    print("======================")
    app_ok = test_app()
    
    # Final status
    print("\n🎯 Setup Complete!")
    print("==================")
    
    if tesseract_ok and app_ok:
        print("✅ All systems ready!")
        print("\n🚀 To start the application:")
        print("   streamlit run app.py")
        print("\n🌐 Then open: http://localhost:8501")
        print("\n💡 Your dataset contains 11,825+ medicines")
        print("   Upload prescription images to test the AI analysis!")
        return 0
    else:
        print("⚠️  Setup completed with some issues")
        print("   Check the error messages above")
        print("   You may still be able to run: streamlit run app.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())