#!/usr/bin/env python3
"""
Quick PDF Test - Simple test for PDF generation with bytearray handling
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.utils import generate_pdf_report
from datetime import datetime

def test_pdf_types():
    """Test different PDF output types"""
    
    print("🔧 PDF Type Handling Test")
    print("=" * 30)
    
    # Test what fpdf2 returns
    try:
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, 'Test PDF', 0, 1)
        
        output = pdf.output(dest='S')
        output_type = type(output).__name__
        
        print(f"📊 fpdf2 returns: {output_type}")
        print(f"📏 Output length: {len(output)}")
        
        # Test conversion
        if isinstance(output, bytearray):
            converted = bytes(output)
            print(f"✅ bytearray → bytes conversion: {type(converted).__name__}")
        elif isinstance(output, str):
            converted = output.encode('latin-1')
            print(f"✅ str → bytes conversion: {type(converted).__name__}")
        else:
            converted = output
            print(f"✅ Already proper type: {type(converted).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing PDF types: {e}")
        return False

def quick_test():
    """Quick test of PDF generation"""
    
    print("\n📄 PDF Generation Test")
    print("=" * 30)
    
    # Simple test data
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'patient_age': 45,
        'entities': [
            {'drug': 'Aspirin', 'dose': '325mg', 'frequency': 'twice daily'}
        ],
        'interactions': [
            {
                'drug_a': 'Aspirin',
                'drug_b': 'Warfarin', 
                'severity': 'high',
                'description': 'Increased bleeding risk'
            }
        ],
        'dosage_results': [
            {
                'drug': 'Aspirin',
                'mentioned_dose': '325mg',
                'dose_status': 'appropriate'
            }
        ]
    }
    
    try:
        print("📄 Generating PDF...")
        pdf_bytes = generate_pdf_report(test_data)
        
        print(f"📊 Result type: {type(pdf_bytes).__name__}")
        print(f"📏 Size: {len(pdf_bytes)} bytes")
        
        if isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 100:
            print("✅ PDF generated successfully!")
            
            # Save test file
            with open('quick_test.pdf', 'wb') as f:
                f.write(pdf_bytes)
            
            print("💾 Saved as: quick_test.pdf")
            
            # Verify file is valid PDF
            with open('quick_test.pdf', 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    print("✅ Valid PDF file created")
                    return True
                else:
                    print("❌ Invalid PDF file format")
                    return False
        else:
            print("❌ PDF generation failed - wrong type or too small")
            print(f"   Type: {type(pdf_bytes)}")
            print(f"   Size: {len(pdf_bytes) if hasattr(pdf_bytes, '__len__') else 'Unknown'}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    
    print("🔧 Complete PDF Fix Verification")
    print("=" * 40)
    
    # Test 1: PDF output types
    type_test = test_pdf_types()
    
    # Test 2: Full PDF generation
    gen_test = quick_test()
    
    print("\n" + "=" * 40)
    
    if type_test and gen_test:
        print("🎉 All PDF tests passed!")
        print("✅ bytearray handling works correctly")
        print("✅ PDF generation creates valid files")
        print("✅ Your app can now export reports successfully")
        print("\n🚀 Ready for demo!")
    else:
        print("❌ Some PDF tests failed")
        if not type_test:
            print("   • PDF type detection failed")
        if not gen_test:
            print("   • PDF generation failed")
        print("\n💡 Try: pip install --upgrade fpdf2")

if __name__ == "__main__":
    main()