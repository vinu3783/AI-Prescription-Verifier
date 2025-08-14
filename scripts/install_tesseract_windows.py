#!/usr/bin/env python3
"""
Tesseract OCR Installer for Windows
Automatically downloads and guides installation of Tesseract OCR
"""

import os
import sys
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

def check_tesseract_installed():
    """Check if Tesseract is already installed and working"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tesseract is already installed and in PATH")
            print(f"Version: {result.stdout.split()[1] if len(result.stdout.split()) > 1 else 'Unknown'}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Check common installation paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Tesseract found at: {path}")
            print("Adding to environment...")
            update_env_file(path)
            return True
    
    return False

def update_env_file(tesseract_path):
    """Update .env file with correct Tesseract path"""
    env_file = Path(".env")
    
    if env_file.exists():
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add Tesseract path
        if 'TESSERACT_CMD_PATH' in content:
            # Replace existing line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('TESSERACT_CMD_PATH'):
                    lines[i] = f'TESSERACT_CMD_PATH={tesseract_path}'
                    break
            content = '\n'.join(lines)
        else:
            # Add new line
            content += f'\nTESSERACT_CMD_PATH={tesseract_path}\n'
        
        # Write back
        with open(env_file, 'w') as f:
            f.write(content)
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write(f"""# AI Prescription Verifier Environment
APP_NAME="AI Prescription Verifier"
DEBUG=false
TESSERACT_CMD_PATH={tesseract_path}
MAX_FILE_SIZE_MB=10
""")
    
    print(f"✅ Updated .env file with Tesseract path")

def download_tesseract():
    """Guide user to download Tesseract"""
    print("\n📥 Downloading Tesseract OCR for Windows...")
    print("=" * 50)
    
    # Tesseract download URLs
    download_urls = {
        "Official GitHub (Recommended)": "https://github.com/UB-Mannheim/tesseract/wiki",
        "Direct Download (Latest)": "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    }
    
    print("Choose download method:")
    print("1. Open GitHub page (recommended - see all versions)")
    print("2. Direct download latest version")
    print("3. Manual instructions only")
    
    while True:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            print("Opening Tesseract GitHub page...")
            webbrowser.open(download_urls["Official GitHub (Recommended)"])
            break
        elif choice == "2":
            print("Opening direct download...")
            webbrowser.open(download_urls["Direct Download (Latest)"])
            break
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print("\n📝 Installation Instructions:")
    print("=" * 30)
    print("1. Download the .exe file")
    print("2. Run as Administrator")
    print("3. During installation:")
    print("   ✅ Note the installation path (usually C:\\Program Files\\Tesseract-OCR\\)")
    print("   ✅ Choose 'Add to PATH' if available")
    print("4. Complete the installation")
    print("5. Restart your command prompt")
    print("6. Run this script again to verify")

def test_python_tesseract():
    """Test if Python can access Tesseract"""
    try:
        import pytesseract
        from PIL import Image
        
        # Try to set path from .env
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TESSERACT_CMD_PATH'):
                        path = line.split('=', 1)[1].strip()
                        pytesseract.pytesseract.tesseract_cmd = path
                        print(f"Using Tesseract path from .env: {path}")
                        break
        
        # Create test image
        test_image = Image.new('RGB', (200, 50), color='white')
        
        # Test OCR
        text = pytesseract.image_to_string(test_image)
        print("✅ Python can access Tesseract OCR!")
        return True
        
    except ImportError:
        print("❌ pytesseract not installed. Run: pip install pytesseract")
        return False
    except Exception as e:
        print(f"❌ Tesseract access error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Tesseract is installed")
        print("2. Check the path in .env file")
        print("3. Restart your terminal/IDE")
        return False

def run_demo_without_ocr():
    """Run the app in demo mode without OCR"""
    print("\n🚀 Running Demo Mode (No OCR Required)")
    print("=" * 40)
    print("The app will use sample prescription text for demonstration.")
    print("All other AI features (NER, DDI, Severity, Summary) work normally.")
    print()
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running app: {e}")
        print("Try manually: streamlit run app.py")

def main():
    """Main installer process"""
    print("🔧 Tesseract OCR Installer for Windows")
    print("=" * 40)
    print()
    
    # Check if already installed
    if check_tesseract_installed():
        print("\n🧪 Testing Python integration...")
        if test_python_tesseract():
            print("\n🎉 Tesseract setup is complete!")
            print("You can now run: streamlit run app.py")
            return
    
    print("\n❌ Tesseract OCR not found or not accessible")
    print("\nOptions:")
    print("1. Install Tesseract (recommended for full functionality)")
    print("2. Run demo without OCR (quick start)")
    print("3. Exit and install manually")
    
    while True:
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == "1":
            download_tesseract()
            print("\n⏳ After installation, run this script again to verify setup.")
            break
        elif choice == "2":
            run_demo_without_ocr()
            break
        elif choice == "3":
            print("\n📝 Manual installation guide:")
            print("1. Visit: https://github.com/UB-Mannheim/tesseract/wiki")
            print("2. Download tesseract-ocr-w64-setup-*.exe")
            print("3. Install as Administrator")
            print("4. Add to PATH: C:\\Program Files\\Tesseract-OCR")
            print("5. Restart terminal and run: tesseract --version")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()