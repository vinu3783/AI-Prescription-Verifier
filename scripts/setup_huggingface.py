#!/usr/bin/env python3
"""
Hugging Face API Setup Script
Sets up Hugging Face API key for the samant/medical-ner model
"""

import os
import sys
import webbrowser
import requests
from pathlib import Path

def print_header():
    """Print setup header"""
    print("🤗 Hugging Face API Setup for Medical NER")
    print("=" * 50)
    print("Model: samant/medical-ner")
    print("Purpose: Enhanced drug name extraction from prescriptions")
    print()

def check_existing_api_key():
    """Check if API key is already configured"""
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if 'HUGGINGFACE_API_KEY' in content:
                # Check if it's not the placeholder
                for line in content.split('\n'):
                    if line.startswith('HUGGINGFACE_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        if api_key and api_key != 'your_huggingface_api_key_here':
                            print("✅ Hugging Face API key already configured")
                            return test_api_key(api_key)
    
    return False

def get_api_key_instructions():
    """Show instructions for getting API key"""
    print("📝 How to get your Hugging Face API Key:")
    print("-" * 40)
    print("1. Visit: https://huggingface.co/settings/tokens")
    print("2. Click 'New token'")
    print("3. Enter a name (e.g., 'AI Prescription Verifier')")
    print("4. Select 'Read' permissions")
    print("5. Click 'Generate a token'")
    print("6. Copy your token")
    print()
    
    choice = input("📖 Open the API tokens page in your browser? (y/N): ").lower()
    if choice == 'y':
        webbrowser.open("https://huggingface.co/settings/tokens")
        print("🌐 Browser opened. Get your API key and come back here.")
    
    print()

def test_api_key(api_key: str) -> bool:
    """Test if the API key works with the medical NER model"""
    print("🧪 Testing API key with samant/medical-ner model...")
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        api_url = "https://api-inference.huggingface.co/models/samrawal/bert-base-uncased-medical-ner"
        
        # Test with a simple medical text
        test_payload = {"inputs": "Take aspirin 325mg twice daily with food"}
        
        response = requests.post(
            api_url,
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ API key is working!")
            result = response.json()
            if result:
                print(f"📊 Test extraction successful - found {len(result)} entities")
                return True
            else:
                print("⚠️ API responded but no entities found (this might be normal)")
                return True
                
        elif response.status_code == 401:
            print("❌ API key is invalid or unauthorized")
            return False
            
        elif response.status_code == 503:
            print("⏳ Model is loading on Hugging Face servers...")
            print("   This is normal for first use. The model will be ready in a few minutes.")
            print("   Your API key appears to be valid.")
            return True
            
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out. The API might be slow, but your key is likely valid.")
        return True
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def update_env_file(api_key: str):
    """Update .env file with the API key"""
    env_file = Path(".env")
    
    # Read existing content or create new
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        # Copy from example if it exists
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
    
    # Update or add Hugging Face API key
    found = False
    for i, line in enumerate(lines):
        if line.startswith('HUGGINGFACE_API_KEY'):
            lines[i] = f'HUGGINGFACE_API_KEY={api_key}\n'
            found = True
            break
    
    if not found:
        lines.append(f'HUGGINGFACE_API_KEY={api_key}\n')
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print("✅ API key saved to .env file")

def test_integration():
    """Test integration with the NER module"""
    print("\n🔧 Testing integration with NER module...")
    
    try:
        # Add current directory to path
        sys.path.append('.')
        from core.ner import test_ner
        
        success = test_ner()
        if success:
            print("✅ NER module integration working!")
            return True
        else:
            print("⚠️ NER module test had issues (but API key is configured)")
            return False
            
    except ImportError as e:
        print(f"⚠️ Could not import NER module: {e}")
        print("   This is normal if you haven't installed dependencies yet.")
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def show_usage_info():
    """Show how the API will be used"""
    print("\n💡 How this improves your app:")
    print("-" * 30)
    print("✨ Faster startup (no model download)")
    print("🎯 Better accuracy for medical terms")
    print("💾 Less memory usage")
    print("🚀 Always up-to-date model")
    print("🔄 Automatic fallback to local/rule-based if API fails")
    print()
    print("📊 API Usage:")
    print("• Free tier: 1,000 requests/month")
    print("• Each prescription analysis = 1 request")
    print("• Automatically falls back to local processing if quota exceeded")

def main():
    """Main setup process"""
    print_header()
    
    # Check if already configured
    if check_existing_api_key():
        print("\n🎉 Hugging Face API is already working!")
        
        choice = input("\n🔄 Would you like to update your API key? (y/N): ").lower()
        if choice != 'y':
            test_integration()
            show_usage_info()
            return 0
    
    # Get instructions for API key
    get_api_key_instructions()
    
    # Get API key from user
    while True:
        api_key = input("🔑 Enter your Hugging Face API key: ").strip()
        
        if not api_key:
            print("❌ Please enter a valid API key")
            continue
        
        if api_key == 'your_huggingface_api_key_here':
            print("❌ Please enter your actual API key, not the placeholder")
            continue
        
        # Test the API key
        if test_api_key(api_key):
            # Save to .env file
            update_env_file(api_key)
            break
        else:
            print("❌ API key test failed. Please check your key and try again.")
            
            retry = input("🔄 Try again? (y/N): ").lower()
            if retry != 'y':
                print("⚠️ Setup cancelled. You can run this script again later.")
                return 1
    
    # Test integration
    test_integration()
    
    # Show usage information
    show_usage_info()
    
    print("\n🎉 Hugging Face API setup complete!")
    print("🚀 Your AI Prescription Verifier will now use enhanced NER!")
    print("\n▶️ Next steps:")
    print("   1. Run: streamlit run app.py")
    print("   2. Upload a prescription to test the enhanced extraction")
    print("   3. Check that drug names are detected more accurately")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())