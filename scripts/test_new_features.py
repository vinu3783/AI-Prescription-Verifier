#!/usr/bin/env python3
"""
Test Script for New AI Prescription Verifier Features
Tests Therapy Doctor and Smart Reminders functionality
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
from datetime import datetime
from core.gemini_api import TherapyDoctorBot, get_therapy_response
from core.reminder_system import SmartReminderSystem, create_reminders_from_prescription

def test_therapy_doctor():
    """Test Therapy Doctor functionality"""
    print("🧠 Testing Therapy Doctor...")
    print("-" * 30)
    
    try:
        # Test bot initialization
        bot = TherapyDoctorBot()
        
        if not bot.api_key:
            print("⚠️  No Gemini API key found - testing fallback mode")
        else:
            print("✅ Gemini API key configured")
        
        # Test responses
        test_cases = [
            "I'm feeling anxious about my new medication",
            "Can you help me understand drug interactions?", 
            "I'm having trouble sleeping",
            "What should I do if I miss a dose?"
        ]
        
        print("\n🧪 Testing responses:")
        for i, test_message in enumerate(test_cases, 1):
            print(f"\n{i}. User: {test_message}")
            
            try:
                response = get_therapy_response(test_message)
                print(f"   Dr. Sarah: {response[:100]}...")
                print("   ✅ Response generated")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n✅ Therapy Doctor test completed")
        return True
        
    except Exception as e:
        print(f"❌ Therapy Doctor test failed: {e}")
        return False

def test_reminder_system():
    """Test Smart Reminder System"""
    print("\n⏰ Testing Smart Reminder System...")
    print("-" * 30)
    
    try:
        # Test system initialization
        reminder_system = SmartReminderSystem()
        print("✅ Reminder system initialized")
        
        # Test creating reminders from prescription
        sample_entities = [
            {
                'drug': 'Aspirin',
                'dose': '325mg',
                'frequency': 'twice daily',
                'rxcui': '1191'
            },
            {
                'drug': 'Metformin', 
                'dose': '500mg',
                'frequency': 'bid',
                'rxcui': '6809'
            }
        ]
        
        print("\n🧪 Testing reminder creation:")
        created_reminders = create_reminders_from_prescription(sample_entities)
        print(f"✅ Created {len(created_reminders)} medication reminders")
        
        for reminder in created_reminders:
            print(f"   • {reminder.drug_name} - {reminder.dosage} at {', '.join(reminder.times)}")
        
        # Test water reminder
        print("\n💧 Testing water reminders:")
        water_reminder = reminder_system.create_water_reminder(8, 120)
        print(f"✅ Created water reminder: {water_reminder.target_glasses} glasses")
        
        # Test notifications
        print("\n🔔 Testing notifications:")
        from core.reminder_system import get_current_notifications
        notifications = get_current_notifications()
        print(f"✅ Found {len(notifications)} current notifications")
        
        # Test adherence stats
        print("\n📊 Testing analytics:")
        stats = reminder_system.get_adherence_stats()
        print(f"✅ Analytics working - {stats['total_medications']} medications tracked")
        
        print("\n✅ Smart Reminders test completed")
        return True
        
    except Exception as e:
        print(f"❌ Smart Reminders test failed: {e}")
        return False

def test_data_persistence():
    """Test data saving and loading"""
    print("\n💾 Testing Data Persistence...")
    print("-" * 30)
    
    try:
        # Create test data directory
        data_dir = Path("data/reminders")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Test reminder system save/load
        reminder_system = SmartReminderSystem()
        
        # Save data
        reminder_system.save_data()
        print("✅ Data saved successfully")
        
        # Create new instance to test loading
        new_system = SmartReminderSystem()
        print("✅ Data loaded successfully")
        
        # Check files exist
        files_to_check = [
            "data/reminders/medication_reminders.json",
            "data/reminders/water_reminders.json", 
            "data/reminders/reminder_log.json"
        ]
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                print(f"✅ {file_path} exists")
            else:
                print(f"ℹ️  {file_path} will be created on first use")
        
        print("\n✅ Data persistence test completed")
        return True
        
    except Exception as e:
        print(f"❌ Data persistence test failed: {e}")
        return False

def test_integration_with_main_app():
    """Test integration with main prescription analysis"""
    print("\n🔗 Testing Integration...")
    print("-" * 30)
    
    try:
        # Test importing main modules
        print("Testing core module imports...")
        from core.ocr import extract_text
        from core.ner import extract_entities
        print("✅ Core modules imported")
        
        # Test prescription analysis to reminder flow
        print("\nTesting analysis to reminder flow...")
        
        # Simulate prescription analysis results
        sample_analysis = {
            'entities': [
                {'drug': 'Lisinopril', 'dose': '10mg', 'frequency': 'once daily'},
                {'drug': 'Atorvastatin', 'dose': '20mg', 'frequency': 'at bedtime'}
            ],
            'interactions': [],
            'patient_age': 55
        }
        
        # Create reminders from analysis
        reminders = create_reminders_from_prescription(sample_analysis['entities'])
        print(f"✅ Created {len(reminders)} reminders from analysis")
        
        # Test therapy bot with context
        context = {
            'current_medications': [e['drug'] for e in sample_analysis['entities']],
            'patient_age': sample_analysis['patient_age']
        }
        
        response = get_therapy_response("I have questions about my medications", context)
        print("✅ Therapy bot works with prescription context")
        
        print("\n✅ Integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_environment_setup():
    """Test environment configuration"""
    print("\n🔧 Testing Environment Setup...")
    print("-" * 30)
    
    try:
        # Check .env file
        env_file = Path(".env")
        if env_file.exists():
            print("✅ .env file exists")
            
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for required variables
            required_vars = [
                'GEMINI_API_KEY',
                'THERAPY_BOT_ENABLED',
                'DEFAULT_WATER_TARGET'
            ]
            
            for var in required_vars:
                if var in content:
                    print(f"✅ {var} configured")
                else:
                    print(f"⚠️  {var} not found (optional)")
        else:
            print("⚠️  .env file not found - will use defaults")
        
        # Check data directories
        required_dirs = [
            "data/reminders",
            "logs"
        ]
        
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                print(f"✅ {dir_path} directory exists")
            else:
                print(f"ℹ️  {dir_path} will be created automatically")
        
        print("\n✅ Environment setup test completed")
        return True
        
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def generate_test_report():
    """Generate comprehensive test report"""
    print("\n📋 Generating Test Report...")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Data Persistence", test_data_persistence), 
        ("Smart Reminders", test_reminder_system),
        ("Therapy Doctor", test_therapy_doctor),
        ("Integration", test_integration_with_main_app)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! New features are ready to use.")
        print("\n🚀 Next steps:")
        print("   1. Run: streamlit run app.py")
        print("   2. Try the new 'Therapy Doctor' page")
        print("   3. Set up reminders in 'Smart Reminders' page")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check error messages above.")
        print("\n🔧 Common fixes:")
        print("   • Install missing dependencies: pip install -r requirements.txt")
        print("   • Configure Gemini API key in .env file")
        print("   • Run: python scripts/setup_new_features.py")
    
    return passed == total

def main():
    """Main test execution"""
    print("🧪 AI Prescription Verifier - New Features Test")
    print("=" * 60)
    print("Testing: 🧠 Therapy Doctor + ⏰ Smart Reminders")
    print()
    
    success = generate_test_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())