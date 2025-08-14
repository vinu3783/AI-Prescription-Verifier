#!/usr/bin/env python3
"""
Dataset Inspector for AI Prescription Verifier
Analyzes the uploaded medicine dataset to understand its structure and content
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_medicine_dataset(file_path: str):
    """
    Inspect the uploaded medicine dataset
    """
    try:
        # Load the dataset
        df = pd.read_csv(file_path)
        print(f"📊 Dataset Overview")
        print(f"==================")
        print(f"File: {file_path}")
        print(f"Rows: {len(df):,}")
        print(f"Columns: {len(df.columns)}")
        print()
        
        # Show column information
        print(f"📋 Column Information")
        print(f"====================")
        for i, col in enumerate(df.columns, 1):
            dtype = df[col].dtype
            non_null = df[col].count()
            null_count = len(df) - non_null
            print(f"{i:2d}. {col:<20} ({dtype}) - {non_null:,} non-null, {null_count:,} null")
        print()
        
        # Show sample data
        print(f"📄 Sample Data (First 3 Rows)")
        print(f"=============================")
        print(df.head(3).to_string())
        print()
        
        # Analyze Medicine Names
        print(f"💊 Medicine Name Analysis")
        print(f"========================")
        medicine_names = df['Medicine Name'].dropna()
        print(f"Unique medicines: {medicine_names.nunique():,}")
        print(f"Sample medicine names:")
        for name in medicine_names.head(10):
            print(f"  • {name}")
        print()
        
        # Analyze Compositions
        print(f"🧪 Composition Analysis")
        print(f"=====================")
        compositions = df['Composition'].dropna()
        print(f"Unique compositions: {compositions.nunique():,}")
        print(f"Sample compositions:")
        for comp in compositions.head(5):
            comp_short = comp[:80] + "..." if len(comp) > 80 else comp
            print(f"  • {comp_short}")
        print()
        
        # Extract common ingredients
        print(f"🔬 Common Active Ingredients")
        print(f"===========================")
        ingredients = []
        for comp in compositions.head(1000):  # Sample to avoid memory issues
            if pd.notna(comp):
                # Extract potential active ingredients
                comp_clean = str(comp).lower()
                # Common drug name patterns
                words = re.findall(r'\b[a-z]{4,20}\b', comp_clean)
                ingredients.extend(words)
        
        ingredient_counts = pd.Series(ingredients).value_counts()
        print(f"Top 15 ingredients/components:")
        for ingredient, count in ingredient_counts.head(15).items():
            print(f"  • {ingredient:<15} ({count:,} times)")
        print()
        
        # Analyze Side Effects
        print(f"⚠️  Side Effects Analysis")
        print(f"========================")
        side_effects = df['Side_effects'].dropna()
        print(f"Records with side effects: {len(side_effects):,}")
        print(f"Sample side effects:")
        for effect in side_effects.head(5):
            effect_short = effect[:100] + "..." if len(effect) > 100 else effect
            print(f"  • {effect_short}")
        print()
        
        # Analyze Uses
        print(f"🎯 Uses Analysis")
        print(f"================")
        uses = df['Uses'].dropna()
        print(f"Records with uses: {len(uses):,}")
        print(f"Sample uses:")
        for use in uses.head(5):
            use_short = use[:100] + "..." if len(use) > 100 else use
            print(f"  • {use_short}")
        print()
        
        # Review Analysis
        print(f"⭐ Review Analysis")
        print(f"==================")
        if 'Excellent Review %' in df.columns:
            excellent_avg = df['Excellent Review %'].mean()
            average_avg = df['Average Review %'].mean()
            poor_avg = df['Poor Review %'].mean()
            
            print(f"Average Excellent Reviews: {excellent_avg:.1f}%")
            print(f"Average Average Reviews:   {average_avg:.1f}%")
            print(f"Average Poor Reviews:      {poor_avg:.1f}%")
        print()
        
        # Identify potential drug interaction candidates
        print(f"🔄 Potential DDI Generation Strategy")
        print(f"===================================")
        
        # Look for common drug classes
        drug_classes = {
            'blood_thinners': ['warfarin', 'aspirin', 'clopidogrel', 'heparin'],
            'pain_relievers': ['ibuprofen', 'diclofenac', 'naproxen', 'celecoxib'],
            'heart_meds': ['metoprolol', 'amlodipine', 'lisinopril', 'atorvastatin'],
            'diabetes_meds': ['metformin', 'glipizide', 'insulin'],
            'antibiotics': ['amoxicillin', 'azithromycin', 'ciprofloxacin']
        }
        
        found_classes = {}
        for class_name, drugs in drug_classes.items():
            found_drugs = []
            for drug in drugs:
                matching = medicine_names[medicine_names.str.contains(drug, case=False, na=False)]
                if len(matching) > 0:
                    found_drugs.extend(matching.tolist()[:3])  # First 3 matches
            if found_drugs:
                found_classes[class_name] = found_drugs
        
        print(f"Found drug classes for DDI generation:")
        for class_name, drugs in found_classes.items():
            print(f"  • {class_name}: {len(drugs)} medicines")
            for drug in drugs[:2]:  # Show first 2
                print(f"    - {drug}")
        print()
        
        # Estimate DDI generation potential
        total_potential_pairs = 0
        for class_drugs in found_classes.values():
            if len(class_drugs) >= 2:
                pairs = len(class_drugs) * (len(class_drugs) - 1) // 2
                total_potential_pairs += pairs
        
        print(f"📈 DDI Generation Estimate")
        print(f"=========================")
        print(f"Potential intra-class interactions: ~{total_potential_pairs}")
        print(f"Potential inter-class interactions: ~{len(medicine_names) * 2}")
        print(f"Total estimated DDI records: ~{total_potential_pairs + len(medicine_names) * 2}")
        print()
        
        return df
        
    except Exception as e:
        logger.error(f"Error inspecting dataset: {e}")
        return None

def main():
    """
    Main function to inspect the uploaded dataset
    """
    dataset_path = Path("data/datasets/raw_kaggle_ddi/ddi_dataset.csv")
    
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        print(f"Please ensure the file is uploaded to the correct location.")
        return
    
    print(f"🔍 AI Prescription Verifier - Dataset Inspector")
    print(f"===============================================")
    print()
    
    df = inspect_medicine_dataset(dataset_path)
    
    if df is not None:
        print(f"✅ Dataset inspection completed successfully!")
        print(f"💡 Run 'python scripts/build_dataset.py' to convert this to DDI format")
    else:
        print(f"❌ Dataset inspection failed!")

if __name__ == "__main__":
    main()