#!/usr/bin/env python3
"""
Setup Script for New AI Prescription Verifier Features
Sets up Therapy Doctor (Gemini AI) and Smart Reminders
"""

import os
import sys
from pathlib import Path
import subprocess
import webbrowser

def print_header():
    """Print setup header"""
    print("🎯 AI Prescription Verifier - New Features Setup")
    print("=" * 60)
    print("Adding: 🧠 Therapy Doctor + ⏰ Smart Reminders")
    print()

def check_existing_setup():
    """Check if the main app is working"""
    try:
        # Check if main files exist
        required_files = [
            "app.py",
            "requirements.txt", 
            "core/ocr.py",
            "core/ner.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print("❌ Missing core files:")
            for file in missing_files:
                print(f"   • {file}")
            return False
        
        print("✅ Core application files found")
        return True
        
    except Exception as e:
        print(f"❌ Error checking setup: {e}")
        return False

def install_new_dependencies():
    """Install new dependencies"""
    print("\n📦 Installing New Dependencies...")
    print("-" * 30)
    
    new_packages = [
        "google-generativeai>=0.3.0",
        "schedule>=1.2.0", 
        "pytz>=2023.3",
        "dataclasses-json>=0.6.0"
    ]
    
    try:
        for package in new_packages:
            print(f"Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package
            ], stdout=subprocess.DEVNULL)
            print(f"✅ {package} installed")
        
        print("\n✅ All new dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("\n💡 Try manually: pip install google-generativeai schedule pytz")
        return False

def setup_gemini_api():
    """Setup Gemini API configuration"""
    print("\n🤖 Google Gemini AI Setup")
    print("-" * 30)
    
    print("The Therapy Doctor feature uses Google's Gemini AI.")
    print("You need a free API key from Google AI Studio.")
    print()
    
    # Check if API key already exists
    env_file = Path(".env")
    has_key = False
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GEMINI_API_KEY' in content and 'your_gemini_api_key_here' not in content:
                print("✅ Gemini API key already configured in .env file")
                has_key = True
    
    if not has_key:
        print("🔑 You need to get a Gemini API key:")
        print("   1. Visit: https://makersuite.google.com/app/apikey")
        print("   2. Click 'Create API Key'")
        print("   3. Copy your API key")
        print()
        
        choice = input("📖 Open the API key page in your browser? (y/N): ").lower()
        if choice == 'y':
            webbrowser.open("https://makersuite.google.com/app/apikey")
        
        print("\n💡 After getting your API key:")
        print("   1. Copy the key")
        print("   2. Open .env file")
        print("   3. Replace 'your_gemini_api_key_here' with your actual key")
        print("   4. Save the file")
        print()
        
        # Option to enter key now
        api_key = input("🔑 Enter your Gemini API key now (or press Enter to skip): ").strip()
        
        if api_key:
            update_env_file(api_key)
            print("✅ API key saved to .env file")
            return True
        else:
            print("⚠️  API key setup skipped. You can configure it later in .env file.")
            return False
    
    return True

def update_env_file(api_key=None):
    """Update or create .env file"""
    env_file = Path(".env")
    
    # Read existing content or create new
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add Gemini API key
    if api_key:
        found = False
        for i, line in enumerate(lines):
            if line.startswith('GEMINI_API_KEY'):
                lines[i] = f'GEMINI_API_KEY={api_key}\n'
                found = True
                break
        
        if not found:
            lines.append(f'GEMINI_API_KEY={api_key}\n')
    
    # Add other new environment variables if missing
    new_vars = [
        'THERAPY_BOT_ENABLED=true',
        'DEFAULT_WATER_TARGET=8', 
        'DEFAULT_WATER_INTERVAL=120',
        'NOTIFICATION_SOUND=true'
    ]
    
    existing_vars = set()
    for line in lines:
        if '=' in line:
            var_name = line.split('=')[0]
            existing_vars.add(var_name)
    
    for var_line in new_vars:
        var_name = var_line.split('=')[0]
        if var_name not in existing_vars:
            lines.append(f'{var_line}\n')
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)

def create_directories():
    """Create necessary directories for new features"""
    print("\n📁 Creating Directories...")
    print("-" * 30)
    
    dirs = [
        "data/reminders",
        "logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")

def test_new_features():
    """Test if new features work"""
    print("\n🧪 Testing New Features...")
    print("-" * 30)
    
    try:
        # Test Gemini API import
        print("Testing Gemini AI integration...")
        sys.path.append('.')
        from core.gemini_api import TherapyDoctorBot
        
        bot = TherapyDoctorBot()
        if bot.model:
            print("✅ Therapy Doctor: API connected")
        else:
            print("⚠️  Therapy Doctor: API key needed")
        
        # Test reminder system
        print("Testing Smart Reminders...")
        from core.reminder_system import SmartReminderSystem
        
        reminder_system = SmartReminderSystem()
        print("✅ Smart Reminders: Working")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_feature_overview():
    """Show what was added"""
    print("\n🎉 New Features Added!")
    print("=" * 30)
    
    print("🧠 **Therapy Doctor (Dr. Sarah)**:")
    print("   • AI-powered mental health support")
    print("   • Medical guidance and advice")
    print("   • Stress and anxiety management")
    print("   • Crisis support resources")
    print("   • Medication counseling")
    print()
    
    print("⏰ **Smart Reminders**:")
    print("   • Automatic medication reminders")
    print("   • Water intake tracking")
    print("   • Adherence analytics")
    print("   • Streak tracking")
    print("   • Weekly reports")
    print()
    
    print("📱 **Enhanced UI**:")
    print("   • New sidebar notifications")
    print("   • Therapy chat interface")
    print("   • Reminder management")
    print("   • Analytics dashboard")

def show_next_steps():
    """Show what user should do next"""
    print("\n🚀 Next Steps:")
    print("-" * 15)
    print("1. 🔑 Configure Gemini API key in .env file (if skipped)")
    print("2. 🏃 Run: streamlit run app.py")
    print("3. 🧠 Try the new 'Therapy Doctor' page")
    print("4. ⏰ Set up reminders in 'Smart Reminders' page")
    print("5. 🔍 Analyze a prescription to auto-create reminders")
    print()
    
    print("💡 **Pro Tips:**")
    print("   • Upload a prescription to auto-create medication reminders")
    print("   • Chat with Dr. Sarah about medication questions")
    print("   • Check sidebar notifications for due reminders")
    print("   • Export weekly adherence reports")

def main():
    """Main setup process"""
    print_header()
    
    # Step 1: Check existing setup
    if not check_existing_setup():
        print("❌ Please ensure your main AI Prescription Verifier is set up first")
        return 1
    
    # Step 2: Install new dependencies
    if not install_new_dependencies():
        print("⚠️  Continue with manual installation if needed")
    
    # Step 3: Setup directories
    create_directories()
    
    # Step 4: Setup Gemini API
    api_configured = setup_gemini_api()
    
    # Step 5: Update environment file
    if not Path(".env").exists():
        update_env_file()
        print("✅ Created .env file with new settings")
    
    # Step 6: Test new features
    features_work = test_new_features()
    
    # Step 7: Show results
    print("\n" + "=" * 60)
    
    if features_work:
        show_feature_overview()
        show_next_steps()
        
        print("\n✅ Setup completed successfully!")
        
        if api_configured:
            print("🎉 Ready to use all new features!")
        else:
            print("⚠️  Remember to configure Gemini API key for Therapy Doctor")
        
        return 0
    else:
        print("❌ Setup completed with issues")
        print("💡 Check error messages above and try manual installation")
        return 1

if __name__ == "__main__":
    sys.exit(main())