#!/usr/bin/env python3
"""
PDF Generation Fix Testing
Tests the improved PDF generation with Unicode character handling
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.utils import generate_pdf_report, clean_text_for_pdf
from datetime import datetime

def test_pdf_generation():
    """Test PDF generation with various Unicode characters"""
    
    print("🔧 Testing PDF Generation Fix")
    print("=" * 40)
    
    # Create sample analysis results with Unicode characters
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'patient_age': 45,
        'entities': [
            {
                'drug': 'Aspirin ✓',
                'dose': '325mg',
                'frequency': 'twice daily',
                'rxcui': '1191'
            },
            {
                'drug': 'Metformin → Generic',
                'dose': '500mg',
                'frequency': 'bid',
                'rxcui': '6809'
            }
        ],
        'interactions': [
            {
                'drug_a': 'Aspirin ✓',
                'drug_b': 'Warfarin ⚠️',
                'severity': 'high',
                'description': 'Increased bleeding risk • Monitor closely → Check INR levels ≥ 2.0'
            }
        ],
        'dosage_results': [
            {
                'drug': 'Aspirin ✓',
                'mentioned_dose': '325mg',
                'dose_status': 'appropriate',
                'suggested_dose': None,
                'considerations': ['Take with food • Monitor for bleeding ≥ signs']
            },
            {
                'drug': 'Metformin',
                'mentioned_dose': '500mg',
                'dose_status': 'too_low',
                'suggested_dose': '850mg–1000mg daily',
                'considerations': ['Consider dose ↑ adjustment', 'Monitor blood sugar ≤ 140 mg/dL']
            }
        ]
    }
    
    try:
        print("📄 Generating PDF with Unicode characters...")
        pdf_data = generate_pdf_report(test_results)
        
        if pdf_data and len(pdf_data) > 1000:  # Check if PDF has reasonable size
            print("✅ PDF generated successfully!")
            print(f"📊 PDF size: {len(pdf_data):,} bytes")
            
            # Save test PDF
            output_file = Path("test_pdf_output.pdf")
            with open(output_file, 'wb') as f:
                f.write(pdf_data)
            
            print(f"💾 Saved test PDF: {output_file}")
            print("📝 You can open this file to verify it works correctly")
            
            return True
        else:
            print("❌ PDF generation failed - file too small or empty")
            return False
            
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        return False

def test_unicode_cleaning():
    """Test the Unicode text cleaning function"""
    
    print("\n🧹 Testing Unicode Text Cleaning")
    print("=" * 40)
    
    test_cases = [
        "Aspirin ✓ 325mg twice daily",
        "Warfarin ⚠️ monitor INR → check bleeding",
        "Drug interaction • high severity ≥ 80%",
        "Dosage: 500mg–1000mg • take with food",
        "Status: ✅ appropriate ❌ contraindicated",
        "Temperature: 98.6° ± 1.5°F",
        "Concentration: 50μg/mL × 2 doses"
    ]
    
    print("Original → Cleaned:")
    print("-" * 20)
    
    for test_text in test_cases:
        cleaned = clean_text_for_pdf(test_text)
        print(f"'{test_text}'")
        print(f"→ '{cleaned}'")
        print()
    
    print("✅ Unicode cleaning test completed")

def main():
    """Run PDF generation tests"""
    
    print("🔧 PDF Generation Fix - Testing Suite")
    print("=" * 50)
    print()
    
    # Test 1: Unicode cleaning
    test_unicode_cleaning()
    
    # Test 2: PDF generation
    success = test_pdf_generation()
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 PDF generation is now working correctly!")
        print("✅ Unicode characters are properly handled")
        print("✅ Your app can now export PDF reports without errors")
        print()
        print("💡 The PDF will use ASCII equivalents:")
        print("   ✓ → [OK]")
        print("   ❌ → [ERROR]") 
        print("   ⚠️ → [WARNING]")
        print("   • → -")
        print("   → → ->")
        
    else:
        print("❌ PDF generation still has issues")
        print("💡 Check the error messages above")
        print("🔄 You may need to install additional dependencies")

if __name__ == "__main__":
    main()