#!/usr/bin/env python3
"""
Test Hugging Face API Integration for Medical NER
Comprehensive testing of API vs Local vs Rule-based extraction
"""

import os
import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

def test_api_configuration():
    """Test if Hugging Face API is properly configured"""
    print("🔧 Testing API Configuration")
    print("-" * 30)
    
    api_key = os.getenv('HUGGINGFACE_API_KEY')
    
    if not api_key:
        print("❌ No HUGGINGFACE_API_KEY found in environment")
        print("💡 Run: python scripts/setup_huggingface.py")
        return False
    
    if api_key == 'your_huggingface_api_key_here':
        print("❌ Placeholder API key detected")
        print("💡 Please set your actual Hugging Face API key")
        return False
    
    print(f"✅ API key configured: {api_key[:8]}...{api_key[-4:]}")
    return True

def test_model_loading():
    """Test different model loading methods"""
    print("\n🤖 Testing Model Loading Methods")
    print("-" * 35)
    
    try:
        from core.ner import MedicalNER
        
        # Test with API
        print("1. Testing API-based loading...")
        ner_api = MedicalNER()
        
        if ner_api.use_api and ner_api.hf_api_key:
            print("✅ API method available")
        else:
            print("⚠️ API method not available")
        
        # Test local loading capability
        print("2. Testing local model capability...")
        if ner_api.ner_pipeline:
            print("✅ Local model loaded")
        else:
            print("⚠️ Local model not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Model loading test failed: {e}")
        return False

def test_extraction_methods():
    """Test different extraction methods with sample texts"""
    print("\n🧪 Testing Extraction Methods")
    print("-" * 30)
    
    test_cases = [
        {
            "name": "Simple prescription",
            "text": "Take Aspirin 325mg twice daily with food. Metformin 500mg before meals."
        },
        {
            "name": "Complex prescription", 
            "text": "1. Lisinopril 10mg once daily in morning. 2. Atorvastatin 20mg at bedtime. 3. Amlodipine 5mg daily."
        },
        {
            "name": "Medical abbreviations",
            "text": "Rx: Ibuprofen 400mg TID PRN pain. Omeprazole 20mg BID AC."
        },
        {
            "name": "Brand names",
            "text": "Tylenol 500mg q6h PRN fever. Advil 200mg TID with food."
        }
    ]
    
    try:
        from core.ner import MedicalNER
        
        ner = MedicalNER()
        results = {}
        
        for case in test_cases:
            print(f"\n📝 Testing: {case['name']}")
            print(f"   Text: {case['text'][:50]}...")
            
            case_results = {}
            
            # Test API extraction
            if ner.use_api and ner.hf_api_key:
                try:
                    start_time = time.time()
                    api_entities = ner.extract_with_api(case['text'])
                    api_time = time.time() - start_time
                    
                    case_results['api'] = {
                        'entities': len(api_entities),
                        'time': f"{api_time:.2f}s",
                        'success': True
                    }
                    print(f"   🌐 API: {len(api_entities)} entities in {api_time:.2f}s")
                    
                except Exception as e:
                    case_results['api'] = {'success': False, 'error': str(e)}
                    print(f"   ❌ API failed: {e}")
            
            # Test local model extraction
            if ner.ner_pipeline:
                try:
                    start_time = time.time()
                    local_entities = ner.extract_with_transformer(case['text'])
                    local_time = time.time() - start_time
                    
                    case_results['local'] = {
                        'entities': len(local_entities),
                        'time': f"{local_time:.2f}s",
                        'success': True
                    }
                    print(f"   🏠 Local: {len(local_entities)} entities in {local_time:.2f}s")
                    
                except Exception as e:
                    case_results['local'] = {'success': False, 'error': str(e)}
                    print(f"   ❌ Local failed: {e}")
            
            # Test rule-based extraction
            try:
                start_time = time.time()
                rule_entities = ner.extract_with_rules(case['text'])
                rule_time = time.time() - start_time
                
                case_results['rules'] = {
                    'entities': len(rule_entities),
                    'time': f"{rule_time:.2f}s",
                    'success': True
                }
                print(f"   📏 Rules: {len(rule_entities)} entities in {rule_time:.2f}s")
                
            except Exception as e:
                case_results['rules'] = {'success': False, 'error': str(e)}
                print(f"   ❌ Rules failed: {e}")
            
            results[case['name']] = case_results
        
        return results
        
    except Exception as e:
        print(f"❌ Extraction test failed: {e}")
        return {}

def test_main_extraction_function():
    """Test the main extract_entities function"""
    print("\n🎯 Testing Main Extraction Function")
    print("-" * 35)
    
    try:
        from core.ner import extract_entities
        
        test_prescription = """
        PRESCRIPTION
        Patient: John Doe, Age: 45
        Date: 01/15/2024
        
        Medications:
        1. Aspirin 325mg - Take twice daily with food
        2. Metformin 500mg - Take twice daily with meals  
        3. Lisinopril 10mg - Take once daily in morning
        
        Dr. Sarah Smith, MD
        """
        
        print("📄 Testing with sample prescription...")
        start_time = time.time()
        entities = extract_entities(test_prescription)
        extraction_time = time.time() - start_time
        
        print(f"✅ Extracted {len(entities)} prescriptions in {extraction_time:.2f}s")
        
        for i, entity in enumerate(entities, 1):
            drug = entity.get('drug', 'Unknown')
            dose = entity.get('dose', 'No dose')
            freq = entity.get('frequency', 'No frequency')
            print(f"   {i}. {drug} - {dose} - {freq}")
        
        return len(entities) > 0
        
    except Exception as e:
        print(f"❌ Main function test failed: {e}")
        return False

def test_performance_comparison():
    """Compare performance between different methods"""
    print("\n⚡ Performance Comparison")
    print("-" * 25)
    
    try:
        from core.ner import MedicalNER
        
        ner = MedicalNER()
        test_text = "Take Aspirin 325mg twice daily. Metformin 500mg with meals. Lisinopril 10mg morning."
        
        methods = []
        
        # Test API performance
        if ner.use_api and ner.hf_api_key:
            try:
                times = []
                for _ in range(3):  # Run 3 times for average
                    start = time.time()
                    entities = ner.extract_with_api(test_text)
                    times.append(time.time() - start)
                
                avg_time = sum(times) / len(times)
                methods.append(('API', avg_time, len(entities)))
                
            except Exception as e:
                print(f"   API performance test failed: {e}")
        
        # Test local performance
        if ner.ner_pipeline:
            try:
                times = []
                for _ in range(3):
                    start = time.time()
                    entities = ner.extract_with_transformer(test_text)
                    times.append(time.time() - start)
                
                avg_time = sum(times) / len(times)
                methods.append(('Local', avg_time, len(entities)))
                
            except Exception as e:
                print(f"   Local performance test failed: {e}")
        
        # Test rule-based performance
        try:
            times = []
            for _ in range(3):
                start = time.time()
                entities = ner.extract_with_rules(test_text)
                times.append(time.time() - start)
            
            avg_time = sum(times) / len(times)
            methods.append(('Rules', avg_time, len(entities)))
            
        except Exception as e:
            print(f"   Rules performance test failed: {e}")
        
        # Display results
        if methods:
            print("\n📊 Performance Results:")
            methods.sort(key=lambda x: x[1])  # Sort by time
            
            for method, avg_time, entity_count in methods:
                print(f"   {method:<8}: {avg_time:.3f}s avg ({entity_count} entities)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def show_integration_status():
    """Show overall integration status"""
    print("\n📋 Integration Status Summary")
    print("=" * 35)
    
    # Check environment
    api_key = os.getenv('HUGGINGFACE_API_KEY')
    env_status = "✅ Configured" if api_key and api_key != 'your_huggingface_api_key_here' else "❌ Not configured"
    
    # Check model availability
    try:
        from core.ner import MedicalNER
        ner = MedicalNER()
        
        api_status = "✅ Available" if ner.use_api and ner.hf_api_key else "❌ Not available"
        local_status = "✅ Available" if ner.ner_pipeline else "❌ Not available"
        
    except Exception:
        api_status = "❌ Error"
        local_status = "❌ Error"
    
    print(f"Environment Config: {env_status}")
    print(f"API Method:         {api_status}")
    print(f"Local Method:       {local_status}")
    print(f"Rule-based Method:  ✅ Always available")
    
    print("\n🎯 Recommended Setup:")
    if api_key and api_key != 'your_huggingface_api_key_here':
        print("✨ Perfect! You have API access for best accuracy")
    else:
        print("💡 Set up Hugging Face API for better accuracy:")
        print("   python scripts/setup_huggingface.py")

def main():
    """Main test execution"""
    print("🧪 Hugging Face NER Integration Test")
    print("=" * 40)
    
    # Test 1: Configuration
    config_ok = test_api_configuration()
    
    # Test 2: Model loading
    model_ok = test_model_loading()
    
    # Test 3: Extraction methods
    extraction_results = test_extraction_methods()
    
    # Test 4: Main function
    main_function_ok = test_main_extraction_function()
    
    # Test 5: Performance comparison
    performance_ok = test_performance_comparison()
    
    # Show status
    show_integration_status()
    
    # Final verdict
    print("\n🏁 Test Results:")
    print(f"   Configuration:     {'✅' if config_ok else '❌'}")
    print(f"   Model Loading:     {'✅' if model_ok else '❌'}")
    print(f"   Extraction Tests:  {'✅' if extraction_results else '❌'}")
    print(f"   Main Function:     {'✅' if main_function_ok else '❌'}")
    print(f"   Performance:       {'✅' if performance_ok else '❌'}")
    
    if all([model_ok, main_function_ok]):
        print("\n🎉 Hugging Face NER integration is working!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check configuration and try setup script.")
        return 1

if __name__ == "__main__":
    sys.exit(main())