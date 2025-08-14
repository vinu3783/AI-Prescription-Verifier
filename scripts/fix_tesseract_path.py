#!/usr/bin/env python3
"""
Fix Tesseract Path Configuration
Updates .env file and tests Tesseract installation
"""

import os
from pathlib import Path
import subprocess

def update_env_file():
    """Update .env file with correct Tesseract path"""
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # Check if tesseract.exe exists
    if not os.path.exists(tesseract_path):
        print(f"❌ Tesseract not found at: {tesseract_path}")
        
        # Check alternative paths
        alt_paths = [
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe"
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                tesseract_path = alt_path
                print(f"✅ Found Tesseract at: {tesseract_path}")
                break
        else:
            print("❌ Tesseract executable not found in common locations")
            return False
    else:
        print(f"✅ Found Tesseract at: {tesseract_path}")
    
    # Update .env file
    env_file = Path(".env")
    
    if env_file.exists():
        # Read existing content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update or add Tesseract path
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('TESSERACT_CMD_PATH'):
                lines[i] = f'TESSERACT_CMD_PATH={tesseract_path}\n'
                updated = True
                break
        
        if not updated:
            lines.append(f'TESSERACT_CMD_PATH={tesseract_path}\n')
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(lines)
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
    return True

def test_tesseract_command():
    """Test Tesseract command line"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tesseract command line works!")
            print(f"Version: {result.stdout.splitlines()[0]}")
            return True
        else:
            print("❌ Tesseract command failed")
            return False
    except Exception as e:
        print(f"❌ Tesseract command error: {e}")
        return False

def test_python_tesseract():
    """Test Python pytesseract integration"""
    try:
        import pytesseract
        from PIL import Image
        
        # Set explicit path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # Create test image
        test_image = Image.new('RGB', (300, 100), color='white')
        from PIL import ImageDraw
        
        draw = ImageDraw.Draw(test_image)
        draw.text((10, 30), "TEST OCR 123", fill='black')
        
        # Test OCR
        text = pytesseract.image_to_string(test_image)
        print(f"✅ Python Tesseract works!")
        print(f"Test OCR result: '{text.strip()}'")
        return True
        
    except ImportError:
        print("❌ pytesseract not installed. Run: pip install pytesseract")
        return False
    except Exception as e:
        print(f"❌ Python Tesseract error: {e}")
        return False

def add_to_system_path():
    """Add Tesseract to system PATH"""
    tesseract_dir = r"C:\Program Files\Tesseract-OCR"
    
    print("🔧 Adding Tesseract to system PATH...")
    print("Run this command as Administrator in Command Prompt:")
    print(f'setx PATH "%PATH%;{tesseract_dir}" /M')
    print()
    print("Or manually add to PATH:")
    print("1. Open System Properties → Environment Variables")
    print(f"2. Add to System PATH: {tesseract_dir}")
    print("3. Restart Command Prompt/IDE")

def main():
    """Main fix process"""
    print("🔧 Fixing Tesseract Path Configuration")
    print("=" * 40)
    print()
    
    # Step 1: Update .env file
    print("Step 1: Updating .env file...")
    if not update_env_file():
        return
    
    print()
    
    # Step 2: Test command line
    print("Step 2: Testing Tesseract command...")
    cmd_works = test_tesseract_command()
    
    if not cmd_works:
        print()
        add_to_system_path()
    
    print()
    
    # Step 3: Test Python integration
    print("Step 3: Testing Python integration...")
    python_works = test_python_tesseract()
    
    print()
    print("=" * 40)
    
    if python_works:
        print("🎉 Tesseract is now configured correctly!")
        print("✅ You can run: streamlit run app.py")
        print("✅ OCR will work with uploaded images")
    elif cmd_works:
        print("⚠️  Tesseract command works but Python integration has issues")
        print("💡 The app may still work - try running: streamlit run app.py")
    else:
        print("❌ Tesseract still has issues")
        print("🔄 Try restarting your terminal/IDE and run this script again")
        print("📝 Or manually add to PATH and restart")

if __name__ == "__main__":
    main()