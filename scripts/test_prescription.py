#!/usr/bin/env python3
"""
Prescription Testing Tool
Test your prescription images and see what the OCR/NER extracts
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.ocr import extract_text
from core.ner import extract_entities
from core.interactions import find_interactions
from core.rxcui import get_rxcui
import argparse

def test_prescription_file(file_path: str, show_debug: bool = True):
    """
    Test a prescription file and show detailed results
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"🔍 Testing Prescription: {file_path.name}")
    print("=" * 60)
    
    try:
        # Read file
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # Determine file type
        file_ext = file_path.suffix.lower()
        if file_ext in ['.png', '.jpg', '.jpeg']:
            file_type = f'image/{file_ext[1:]}'
        elif file_ext == '.pdf':
            file_type = 'application/pdf'
        else:
            print(f"❌ Unsupported file type: {file_ext}")
            return False
        
        print(f"📄 File Type: {file_type}")
        print(f"📊 File Size: {len(file_bytes):,} bytes")
        print()
        
        # Step 1: OCR
        print("🔍 STEP 1: OCR Text Extraction")
        print("-" * 30)
        try:
            extracted_text = extract_text(file_bytes, file_type)
            print(f"✅ Extracted {len(extracted_text)} characters")
            
            if show_debug:
                print(f"\n📄 Extracted Text:")
                print("─" * 20)
                print(extracted_text)
                print("─" * 20)
            
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            return False
        
        # Step 2: NER
        print(f"\n💊 STEP 2: Entity Recognition")
        print("-" * 30)
        try:
            entities = extract_entities(extracted_text)
            print(f"✅ Found {len(entities)} drug entities")
            
            if entities:
                print("\n📋 Identified Entities:")
                for i, entity in enumerate(entities, 1):
                    drug = entity.get('drug', 'Unknown')
                    dose = entity.get('dose', 'No dose')
                    freq = entity.get('frequency', 'No frequency')
                    route = entity.get('route', 'No route')
                    print(f"  {i}. Drug: {drug}")
                    print(f"     Dose: {dose}")
                    print(f"     Frequency: {freq}")
                    print(f"     Route: {route}")
                    print()
            else:
                print("⚠️  No entities found")
                print("💡 Suggestions:")
                print("   • Check if prescription contains clear drug names")
                print("   • Ensure dosages are visible (e.g., 325mg, 500mg)")
                print("   • Try a different image format or quality")
        
        except Exception as e:
            print(f"❌ NER failed: {e}")
            return False
        
        # Step 3: RxNorm Mapping
        if entities:
            print(f"\n🔗 STEP 3: RxNorm Mapping")
            print("-" * 30)
            mapped_count = 0
            
            for entity in entities:
                drug_name = entity.get('drug')
                if drug_name:
                    try:
                        rxcui = get_rxcui(drug_name)
                        if rxcui:
                            print(f"✅ {drug_name} → RxCUI: {rxcui}")
                            entity['rxcui'] = rxcui
                            mapped_count += 1
                        else:
                            print(f"❌ {drug_name} → No RxCUI found")
                    except Exception as e:
                        print(f"❌ {drug_name} → Error: {e}")
            
            print(f"\n📊 Mapping Success: {mapped_count}/{len(entities)} drugs")
        
        # Step 4: Drug Interactions
        if entities:
            print(f"\n⚠️  STEP 4: Drug Interaction Check")
            print("-" * 30)
            
            rxcuis = [e.get('rxcui') for e in entities if e.get('rxcui')]
            if len(rxcuis) >= 2:
                try:
                    interactions = find_interactions(rxcuis)
                    if interactions:
                        print(f"⚠️  Found {len(interactions)} potential interactions:")
                        for interaction in interactions:
                            severity = interaction.get('severity', 'unknown')
                            drug_a = interaction.get('drug_a', 'Drug A')
                            drug_b = interaction.get('drug_b', 'Drug B')
                            desc = interaction.get('description', 'No description')
                            
                            severity_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(severity, '⚪')
                            print(f"  {severity_emoji} {drug_a} ↔ {drug_b} ({severity})")
                            print(f"     {desc}")
                            print()
                    else:
                        print("✅ No drug interactions found")
                except Exception as e:
                    print(f"❌ Interaction check failed: {e}")
            else:
                print("ℹ️  Need at least 2 mapped drugs to check interactions")
        
        print("\n" + "=" * 60)
        print("✅ Prescription test completed!")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"   OCR: {'✅ Success' if extracted_text else '❌ Failed'}")
        print(f"   NER: {'✅ Found entities' if entities else '❌ No entities'}")
        if entities:
            mapped = len([e for e in entities if e.get('rxcui')])
            print(f"   RxNorm: {mapped}/{len(entities)} mapped")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def show_good_prescription_examples():
    """Show examples of prescription formats that work well"""
    
    print("📋 PRESCRIPTION FORMATS THAT WORK BEST")
    print("=" * 50)
    
    examples = [
        {
            "title": "Standard Hospital Format",
            "text": """
PRESCRIPTION
Patient: John Doe, Age: 45
Date: 01/15/2024

Medications:
1. Aspirin 325mg - Take twice daily with food
2. Metformin 500mg - Take twice daily with meals
3. Lisinopril 10mg - Take once daily in morning

Dr. Sarah Smith, MD
License: MD123456
            """
        },
        {
            "title": "Simple List Format", 
            "text": """
Rx:
• Aspirin 325mg bid
• Metformin 500mg bid with meals
• Lisinopril 10mg qd

Dr. Johnson
            """
        },
        {
            "title": "Numbered Format",
            "text": """
MEDICATIONS:
1. Atorvastatin 20mg once daily at bedtime
2. Amlodipine 5mg once daily
3. Metformin 500mg twice daily with meals

Follow up in 4 weeks
            """
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print("-" * 25)
        print(example['text'].strip())
    
    print("\n" + "=" * 50)
    print("💡 TIPS FOR BETTER RECOGNITION:")
    print("✅ Use clear, high-contrast images")
    print("✅ Ensure text is straight (not tilted)")
    print("✅ Include drug names, dosages, and frequencies")
    print("✅ Use standard medical abbreviations")
    print("✅ Avoid handwritten prescriptions if possible")
    print("❌ Avoid blurry or low-resolution images")
    print("❌ Avoid complex layouts or decorative fonts")

def main():
    """Main testing function"""
    parser = argparse.ArgumentParser(description="Test prescription OCR and NER")
    parser.add_argument("file", nargs="?", help="Prescription file to test")
    parser.add_argument("--examples", action="store_true", help="Show good prescription examples")
    parser.add_argument("--no-debug", action="store_true", help="Hide debug output")
    
    args = parser.parse_args()
    
    if args.examples:
        show_good_prescription_examples()
        return
    
    if not args.file:
        print("🧪 Prescription Testing Tool")
        print("=" * 30)
        print()
        print("Usage:")
        print("  python scripts/test_prescription.py <file>")
        print("  python scripts/test_prescription.py --examples")
        print()
        print("Examples:")
        print("  python scripts/test_prescription.py prescription.jpg")
        print("  python scripts/test_prescription.py prescription.pdf")
        print()
        return
    
    # Test the file
    success = test_prescription_file(args.file, show_debug=not args.no_debug)
    
    if not success:
        print("\n💡 Try running with --examples to see good prescription formats")

if __name__ == "__main__":
    main()