#!/usr/bin/env python3
"""
Dataset Builder for AI Prescription Verifier
Processes raw Kaggle DDI and RxNorm data to create mapped interaction dataset
"""

import os
import sys
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
import requests
import time
from tqdm import tqdm
import re

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.rxcui import RxNormAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatasetBuilder:
    """
    Build and preprocess drug interaction dataset with RxCUI mapping
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "datasets"
        self.processed_dir = self.data_dir / "processed"
        self.rxnorm_api = RxNormAPI()
        self.max_interactions = 1000  # Default limit
        
        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats tracking
        self.stats = {
            'total_interactions': 0,
            'mapped_interactions': 0,
            'unmapped_drugs': set(),
            'mapping_coverage': 0.0,
            'source_medicines': 0
        }

    def load_kaggle_ddi_data(self) -> pd.DataFrame:
        """
        Load Kaggle DDI dataset or medicine database
        """
        kaggle_dir = self.raw_dir / "raw_kaggle_ddi"
        
        # Look for common dataset files
        possible_files = [
            "ddi_dataset.csv",
            "drug_interactions.csv",
            "drug_drug_interactions.csv", 
            "interactions.csv",
            "medicines.csv",
            "drugs.csv"
        ]
        
        ddi_file = None
        for filename in possible_files:
            file_path = kaggle_dir / filename
            if file_path.exists():
                ddi_file = file_path
                break
        
        if not ddi_file:
            logger.warning("No dataset found. Creating sample dataset...")
            return self.create_sample_ddi_dataset()
        
        try:
            logger.info(f"Loading data from {ddi_file}")
            df = pd.read_csv(ddi_file)
            logger.info(f"Loaded {len(df)} records from dataset")
            
            # Check if this is a medicine database (has Medicine Name, Composition columns)
            if 'Medicine Name' in df.columns and 'Composition' in df.columns:
                logger.info("Detected medicine database format. Converting to DDI dataset...")
                return self.convert_medicine_db_to_ddi(df)
            
            # Check if this is already a DDI dataset
            elif 'drug_a' in df.columns or ('Medicine Name' in df.columns and 'Interacting Drug' in df.columns):
                logger.info("Detected DDI dataset format.")
                return df
            
            else:
                logger.warning("Unknown dataset format. Creating sample dataset...")
                return self.create_sample_ddi_dataset()
            
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            return self.create_sample_ddi_dataset()

    def convert_medicine_db_to_ddi(self, medicine_df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert medicine database to DDI dataset by creating interactions based on:
        1. Common drug combinations
        2. Side effects analysis
        3. Composition conflicts
        """
        logger.info("Converting medicine database to DDI dataset...")
        
        # Clean and prepare medicine data
        medicine_df = medicine_df.copy()
        medicine_df['Medicine Name'] = medicine_df['Medicine Name'].str.strip()
        medicine_df['Composition'] = medicine_df['Composition'].fillna('')
        medicine_df['Side_effects'] = medicine_df['Side_effects'].fillna('')
        
        # Extract main active ingredients
        medicine_df['Main_Ingredient'] = medicine_df['Composition'].apply(self.extract_main_ingredient)
        
        # Create DDI interactions
        interactions = []
        
        # 1. Known dangerous combinations
        dangerous_combinations = [
            ('warfarin', 'aspirin', 'Increased bleeding risk due to additive anticoagulant effects', 'high'),
            ('digoxin', 'furosemide', 'Risk of digoxin toxicity due to electrolyte imbalance', 'high'),
            ('metformin', 'ibuprofen', 'Reduced kidney function may affect drug elimination', 'medium'),
            ('lisinopril', 'ibuprofen', 'NSAIDs may reduce ACE inhibitor effectiveness', 'medium'),
            ('simvastatin', 'clarithromycin', 'Increased statin levels and muscle toxicity risk', 'high'),
            ('tramadol', 'sertraline', 'Risk of serotonin syndrome', 'high'),
            ('atorvastatin', 'amlodipine', 'Increased statin exposure, monitor for muscle problems', 'medium'),
            ('warfarin', 'amoxicillin', 'Antibiotics may affect anticoagulation', 'medium'),
        ]
        
        # Find medicines matching dangerous combinations
        for drug_a_pattern, drug_b_pattern, description, severity in dangerous_combinations:
            drugs_a = medicine_df[
                medicine_df['Medicine Name'].str.contains(drug_a_pattern, case=False, na=False) |
                medicine_df['Main_Ingredient'].str.contains(drug_a_pattern, case=False, na=False)
            ]
            drugs_b = medicine_df[
                medicine_df['Medicine Name'].str.contains(drug_b_pattern, case=False, na=False) |
                medicine_df['Main_Ingredient'].str.contains(drug_b_pattern, case=False, na=False)
            ]
            
            for _, drug_a in drugs_a.iterrows():
                for _, drug_b in drugs_b.iterrows():
                    if drug_a['Medicine Name'] != drug_b['Medicine Name']:
                        interactions.append({
                            'drug_a': drug_a['Medicine Name'],
                            'drug_b': drug_b['Medicine Name'],
                            'description': description,
                            'severity': severity,
                            'mechanism': 'clinical_evidence',
                            'sources': 'DrugBank;Clinical Studies'
                        })
        
        # 2. Generate interactions based on side effects overlap
        interactions.extend(self.generate_side_effect_interactions(medicine_df))
        
        # 3. Generate interactions based on composition conflicts
        interactions.extend(self.generate_composition_interactions(medicine_df))
        
        # 4. Add some beneficial combinations (low severity)
        beneficial_combinations = [
            ('amlodipine', 'metoprolol', 'Complementary blood pressure control', 'low'),
            ('losartan', 'hydrochlorothiazide', 'Synergistic antihypertensive effect', 'low'),
            ('metformin', 'glipizide', 'Complementary diabetes management', 'low'),
        ]
        
        for drug_a_pattern, drug_b_pattern, description, severity in beneficial_combinations:
            drugs_a = medicine_df[
                medicine_df['Medicine Name'].str.contains(drug_a_pattern, case=False, na=False) |
                medicine_df['Main_Ingredient'].str.contains(drug_a_pattern, case=False, na=False)
            ]
            drugs_b = medicine_df[
                medicine_df['Medicine Name'].str.contains(drug_b_pattern, case=False, na=False) |
                medicine_df['Main_Ingredient'].str.contains(drug_b_pattern, case=False, na=False)
            ]
            
            for _, drug_a in drugs_a.iterrows():
                for _, drug_b in drugs_b.iterrows():
                    if drug_a['Medicine Name'] != drug_b['Medicine Name']:
                        interactions.append({
                            'drug_a': drug_a['Medicine Name'],
                            'drug_b': drug_b['Medicine Name'],
                            'description': description,
                            'severity': severity,
                            'mechanism': 'synergistic_effect',
                            'sources': 'Clinical Guidelines'
                        })
        
        # Convert to DataFrame
        if not interactions:
            logger.warning("No interactions generated from medicine database. Using sample data.")
            return self.create_sample_ddi_dataset()
        
        # Limit interactions to prevent memory issues
        if len(interactions) > self.max_interactions:
            logger.info(f"Limiting interactions to {self.max_interactions} (from {len(interactions)})")
            # Prioritize high and medium severity interactions
            high_interactions = [i for i in interactions if i['severity'] == 'high']
            medium_interactions = [i for i in interactions if i['severity'] == 'medium']
            low_interactions = [i for i in interactions if i['severity'] == 'low']
            
            # Take proportionally
            high_count = min(len(high_interactions), self.max_interactions // 3)
            medium_count = min(len(medium_interactions), self.max_interactions // 2)
            low_count = min(len(low_interactions), self.max_interactions - high_count - medium_count)
            
            interactions = (high_interactions[:high_count] + 
                          medium_interactions[:medium_count] + 
                          low_interactions[:low_count])
        
        ddi_df = pd.DataFrame(interactions)
        
        # Remove duplicates
        ddi_df = ddi_df.drop_duplicates(subset=['drug_a', 'drug_b'])
        
        # Store source medicine count
        self.stats['source_medicines'] = len(medicine_df)
        
        logger.info(f"Generated {len(ddi_df)} drug interactions from {len(medicine_df):,} medicines")
        return ddi_df

    def extract_main_ingredient(self, composition: str) -> str:
        """
        Extract main active ingredient from composition string
        """
        if not composition or pd.isna(composition):
            return ""
        
        # Common patterns for extracting active ingredients
        composition = str(composition).lower()
        
        # Remove dosage information
        composition = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)', '', composition)
        
        # Split by common separators and take first ingredient
        separators = ['+', ',', '/', '&', 'and', 'with']
        for sep in separators:
            if sep in composition:
                composition = composition.split(sep)[0]
                break
        
        # Clean up
        composition = composition.strip()
        
        # Remove common suffixes
        suffixes = ['tablet', 'capsule', 'injection', 'syrup', 'suspension']
        for suffix in suffixes:
            composition = composition.replace(suffix, '')
        
        return composition.strip()

    def generate_side_effect_interactions(self, medicine_df: pd.DataFrame) -> List[Dict]:
        """
        Generate interactions based on overlapping serious side effects
        """
        interactions = []
        max_per_effect = 20  # Limit interactions per side effect
        
        # Keywords that indicate serious side effects
        serious_side_effects = [
            'bleeding', 'liver damage', 'kidney damage', 'heart problems',
            'respiratory depression', 'seizure', 'coma', 'hypotension',
            'arrhythmia', 'hepatotoxicity', 'nephrotoxicity', 'dizziness',
            'nausea', 'vomiting', 'drowsiness', 'confusion'
        ]
        
        for side_effect in serious_side_effects:
            # Find medicines with this side effect
            medicines_with_effect = medicine_df[
                medicine_df['Side_effects'].str.contains(side_effect, case=False, na=False)
            ]
            
            if len(medicines_with_effect) >= 2:
                # Create interactions between medicines with same serious side effect
                medicines_list = medicines_with_effect['Medicine Name'].tolist()
                
                interaction_count = 0
                for i, drug_a in enumerate(medicines_list[:20]):  # Limit to prevent explosion
                    if interaction_count >= max_per_effect:
                        break
                    for drug_b in medicines_list[i+1:20]:
                        if interaction_count >= max_per_effect:
                            break
                        
                        severity = 'medium' if side_effect in ['bleeding', 'liver damage', 'kidney damage'] else 'low'
                        interactions.append({
                            'drug_a': drug_a,
                            'drug_b': drug_b,
                            'description': f'Both drugs may cause {side_effect}, increasing risk when used together',
                            'severity': severity,
                            'mechanism': 'additive_side_effects',
                            'sources': 'Side Effect Analysis'
                        })
                        interaction_count += 1
        
        return interactions[:100]  # Limit total side effect interactions

    def generate_composition_interactions(self, medicine_df: pd.DataFrame) -> List[Dict]:
        """
        Generate interactions based on similar active ingredients
        """
        interactions = []
        max_per_ingredient = 10  # Limit interactions per ingredient
        
        # Group medicines by main ingredient
        ingredient_groups = medicine_df.groupby('Main_Ingredient')
        
        ingredient_count = 0
        for ingredient, group in ingredient_groups:
            if len(group) >= 2 and ingredient and len(ingredient) > 3:
                ingredient_count += 1
                if ingredient_count > 20:  # Limit number of ingredients to process
                    break
                    
                # Multiple medicines with same ingredient - potential duplication risk
                medicines_list = group['Medicine Name'].tolist()
                
                interaction_count = 0
                for i, drug_a in enumerate(medicines_list[:max_per_ingredient]):
                    if interaction_count >= max_per_ingredient:
                        break
                    for drug_b in medicines_list[i+1:max_per_ingredient]:
                        if interaction_count >= max_per_ingredient:
                            break
                            
                        interactions.append({
                            'drug_a': drug_a,
                            'drug_b': drug_b,
                            'description': f'Both contain {ingredient}. Avoid duplication to prevent overdose',
                            'severity': 'medium',
                            'mechanism': 'duplicate_active_ingredient',
                            'sources': 'Composition Analysis'
                        })
                        interaction_count += 1
        
        return interactions[:50]  # Limit total composition interactions
        """
        Create a comprehensive sample DDI dataset for testing
        """
        logger.info("Creating sample DDI dataset...")
        
        sample_interactions = [
            # High severity interactions
            {
                'drug_a': 'warfarin',
                'drug_b': 'aspirin',
                'description': 'Concurrent use increases risk of bleeding due to additive anticoagulant effects. Monitor INR closely and watch for signs of bleeding.',
                'severity': 'high',
                'mechanism': 'additive anticoagulant effects',
                'sources': 'DrugBank;Lexicomp;Clinical Studies'
            },
            {
                'drug_a': 'tramadol',
                'drug_b': 'sertraline',
                'description': 'Increased risk of serotonin syndrome. Both drugs increase serotonin levels which can lead to potentially life-threatening condition.',
                'severity': 'high',
                'mechanism': 'serotonin syndrome',
                'sources': 'FDA;DrugBank'
            },
            {
                'drug_a': 'atorvastatin',
                'drug_b': 'clarithromycin',
                'description': 'Clarithromycin inhibits CYP3A4 enzyme, significantly increasing statin levels and risk of myopathy and rhabdomyolysis.',
                'severity': 'high',
                'mechanism': 'CYP3A4 inhibition',
                'sources': 'FDA;Lexicomp'
            },
            {
                'drug_a': 'digoxin',
                'drug_b': 'amiodarone',
                'description': 'Amiodarone increases digoxin levels by inhibiting P-glycoprotein. Risk of digoxin toxicity. Reduce digoxin dose by 50%.',
                'severity': 'high',
                'mechanism': 'P-glycoprotein inhibition',
                'sources': 'Clinical Studies;Lexicomp'
            },
            
            # Medium severity interactions
            {
                'drug_a': 'metformin',
                'drug_b': 'ibuprofen',
                'description': 'NSAIDs may reduce kidney function affecting metformin elimination. Monitor renal function and blood glucose.',
                'severity': 'medium',
                'mechanism': 'reduced renal clearance',
                'sources': 'DrugBank;Clinical Studies'
            },
            {
                'drug_a': 'lisinopril',
                'drug_b': 'ibuprofen',
                'description': 'NSAIDs may reduce antihypertensive effect of ACE inhibitors and increase risk of kidney problems.',
                'severity': 'medium',
                'mechanism': 'prostaglandin inhibition',
                'sources': 'DrugBank;Clinical Guidelines'
            },
            {
                'drug_a': 'simvastatin',
                'drug_b': 'amlodipine',
                'description': 'Amlodipine may increase simvastatin exposure. Consider simvastatin dose reduction to maximum 20mg daily.',
                'severity': 'medium',
                'mechanism': 'CYP3A4 inhibition',
                'sources': 'FDA;DrugBank'
            },
            {
                'drug_a': 'warfarin',
                'drug_b': 'amoxicillin',
                'description': 'Antibiotics may alter gut flora affecting vitamin K production, potentially increasing anticoagulant effect.',
                'severity': 'medium',
                'mechanism': 'altered vitamin K metabolism',
                'sources': 'Clinical Studies'
            },
            {
                'drug_a': 'metoprolol',
                'drug_b': 'verapamil',
                'description': 'Both drugs have negative inotropic effects. Combination may cause excessive bradycardia or heart block.',
                'severity': 'medium',
                'mechanism': 'additive cardiac effects',
                'sources': 'Lexicomp;Clinical Guidelines'
            },
            {
                'drug_a': 'phenytoin',
                'drug_b': 'fluconazole',
                'description': 'Fluconazole inhibits phenytoin metabolism, increasing risk of phenytoin toxicity. Monitor phenytoin levels.',
                'severity': 'medium',
                'mechanism': 'CYP2C9 inhibition',
                'sources': 'DrugBank;Clinical Studies'
            },
            
            # Low severity interactions
            {
                'drug_a': 'atorvastatin',
                'drug_b': 'omeprazole',
                'description': 'Minor interaction with minimal clinical significance. No dose adjustment typically required.',
                'severity': 'low',
                'mechanism': 'minimal enzyme inhibition',
                'sources': 'DrugBank'
            },
            {
                'drug_a': 'metformin',
                'drug_b': 'paracetamol',
                'description': 'No significant pharmacokinetic or pharmacodynamic interaction expected.',
                'severity': 'low',
                'mechanism': 'no significant interaction',
                'sources': 'Clinical Studies'
            },
            {
                'drug_a': 'lisinopril',
                'drug_b': 'paracetamol',
                'description': 'Minimal interaction. Paracetamol does not significantly affect ACE inhibitor effectiveness.',
                'severity': 'low',
                'mechanism': 'no significant interaction',
                'sources': 'Clinical Studies'
            },
            
            # Additional common drug combinations
            {
                'drug_a': 'losartan',
                'drug_b': 'hydrochlorothiazide',
                'description': 'Beneficial combination for hypertension treatment. Monitor potassium and kidney function.',
                'severity': 'low',
                'mechanism': 'synergistic antihypertensive effect',
                'sources': 'Clinical Guidelines'
            },
            {
                'drug_a': 'amlodipine',
                'drug_b': 'metoprolol',
                'description': 'Effective combination for blood pressure control. May cause additive hypotensive effects.',
                'severity': 'low',
                'mechanism': 'additive antihypertensive effect',
                'sources': 'Clinical Guidelines'
            }
        ]
        
        df = pd.DataFrame(sample_interactions)
        self.stats['total_interactions'] = len(df)
        
        # Save sample dataset
        sample_file = self.raw_dir / "raw_kaggle_ddi" / "sample_drug_interactions.csv"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(sample_file, index=False)
        
        logger.info(f"Created sample dataset with {len(df)} interactions")
        return df

    def load_rxnorm_data(self) -> Optional[pd.DataFrame]:
        """
        Load RxNorm RXCONSO.RRF data if available
        """
        rxnorm_dir = self.raw_dir / "raw_rxnorm_2025"
        rxconso_file = rxnorm_dir / "RXCONSO.RRF"
        
        if not rxconso_file.exists():
            logger.warning("RxNorm RXCONSO.RRF file not found. Using API for mapping.")
            return None
        
        try:
            logger.info("Loading RxNorm RXCONSO data...")
            # RxNorm files are pipe-delimited
            df = pd.read_csv(
                rxconso_file,
                sep='|',
                header=None,
                low_memory=False,
                names=[
                    'RXCUI', 'LAT', 'TS', 'LUI', 'STT', 'SUI', 'ISPREF', 'RXAUI',
                    'SAUI', 'SCUI', 'SDUI', 'SAB', 'TTY', 'CODE', 'STR', 'SRL',
                    'SUPPRESS', 'CVF', 'FILLER'
                ]
            )
            
            # Filter for English terms and relevant term types
            df = df[
                (df['LAT'] == 'ENG') & 
                (df['TTY'].isin(['SCD', 'SBD', 'IN', 'PIN', 'BN']))
            ]
            
            logger.info(f"Loaded {len(df)} RxNorm concepts")
            return df
            
        except Exception as e:
            logger.error(f"Error loading RxNorm data: {e}")
            return None

    def normalize_drug_name(self, drug_name: str) -> str:
        """
        Normalize drug names for better matching
        """
        if not drug_name or pd.isna(drug_name):
            return ""
        
        # Convert to lowercase and strip
        normalized = str(drug_name).lower().strip()
        
        # Remove common suffixes and prefixes
        suffixes = [
            'tablet', 'tablets', 'cap', 'capsule', 'capsules',
            'injection', 'syrup', 'suspension', 'cream', 'ointment',
            'mg', 'mcg', 'g', 'ml', 'solution'
        ]
        
        for suffix in suffixes:
            normalized = re.sub(rf'\b{suffix}s?\b', '', normalized)
        
        # Remove dosage information
        normalized = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized

    def map_drug_to_rxcui(self, drug_name: str, cache: Dict[str, str] = None) -> Optional[str]:
        """
        Map a drug name to RxCUI with caching
        """
        if cache is None:
            cache = {}
        
        normalized_name = self.normalize_drug_name(drug_name)
        
        if not normalized_name:
            return None
        
        # Check cache first
        if normalized_name in cache:
            return cache[normalized_name]
        
        try:
            # Try API lookup
            rxcui = self.rxnorm_api.get_rxcui(normalized_name)
            
            if rxcui:
                cache[normalized_name] = rxcui
                logger.debug(f"Mapped '{drug_name}' -> RxCUI: {rxcui}")
                return rxcui
            else:
                # Try without normalization
                rxcui = self.rxnorm_api.get_rxcui(drug_name)
                if rxcui:
                    cache[normalized_name] = rxcui
                    return rxcui
                
                self.stats['unmapped_drugs'].add(drug_name)
                logger.debug(f"Could not map '{drug_name}' to RxCUI")
                return None
                
        except Exception as e:
            logger.warning(f"Error mapping '{drug_name}': {e}")
            return None

    def process_ddi_dataset(self, ddi_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process DDI dataset and add RxCUI mappings
        """
        logger.info("Processing DDI dataset and mapping to RxCUIs...")
        
        # Ensure required columns exist
        required_columns = ['drug_a', 'drug_b', 'description']
        missing_columns = [col for col in required_columns if col not in ddi_df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Initialize result dataframe
        result_df = ddi_df.copy()
        
        # Add RxCUI columns
        result_df['drug_a_rxcui'] = None
        result_df['drug_b_rxcui'] = None
        result_df['drug_a_name'] = result_df['drug_a']
        result_df['drug_b_name'] = result_df['drug_b']
        
        # Ensure severity column exists
        if 'severity' not in result_df.columns:
            result_df['severity'] = 'medium'  # Default severity
        
        # Ensure sources column exists
        if 'sources' not in result_df.columns:
            result_df['sources'] = 'Manual'
        
        # Cache for RxCUI mappings
        rxcui_cache = {}
        
        # Map drug names to RxCUIs with progress bar
        logger.info("Mapping drug names to RxCUIs...")
        
        total_drugs = len(result_df) * 2  # Two drugs per interaction
        mapped_count = 0
        
        with tqdm(total=len(result_df), desc="Processing interactions") as pbar:
            for idx, row in result_df.iterrows():
                # Map drug A
                drug_a_rxcui = self.map_drug_to_rxcui(row['drug_a'], rxcui_cache)
                result_df.at[idx, 'drug_a_rxcui'] = drug_a_rxcui
                if drug_a_rxcui:
                    mapped_count += 1
                
                # Map drug B
                drug_b_rxcui = self.map_drug_to_rxcui(row['drug_b'], rxcui_cache)
                result_df.at[idx, 'drug_b_rxcui'] = drug_b_rxcui
                if drug_b_rxcui:
                    mapped_count += 1
                
                pbar.update(1)
                
                # Rate limiting for API calls
                time.sleep(0.1)
        
        # Update stats
        self.stats['total_interactions'] = len(result_df)
        self.stats['mapped_interactions'] = len(result_df[
            result_df['drug_a_rxcui'].notna() & result_df['drug_b_rxcui'].notna()
        ])
        self.stats['mapping_coverage'] = mapped_count / total_drugs if total_drugs > 0 else 0
        
        # Rename description column to interaction_text for consistency
        if 'description' in result_df.columns:
            result_df['interaction_text'] = result_df['description']
        
        # Reorder columns
        column_order = [
            'drug_a_name', 'drug_a_rxcui', 'drug_b_name', 'drug_b_rxcui',
            'interaction_text', 'severity', 'sources'
        ]
        
        # Add any additional columns that exist
        for col in result_df.columns:
            if col not in column_order:
                column_order.append(col)
        
        result_df = result_df[column_order]
        
        logger.info(f"Processed {len(result_df)} interactions")
        logger.info(f"Successfully mapped {self.stats['mapped_interactions']} complete interactions")
        logger.info(f"Overall mapping coverage: {self.stats['mapping_coverage']:.1%}")
        
        return result_df

    def save_processed_dataset(self, df: pd.DataFrame):
        """
        Save the processed dataset
        """
        output_file = self.processed_dir / "ddi_mapped_with_rxcui.csv"
        
        try:
            df.to_csv(output_file, index=False)
            logger.info(f"Saved processed dataset to {output_file}")
            
            # Save statistics
            stats_file = self.processed_dir / "mapping_stats.json"
            import json
            
            # Convert set to list for JSON serialization
            stats_to_save = self.stats.copy()
            stats_to_save['unmapped_drugs'] = list(stats_to_save['unmapped_drugs'])
            
            with open(stats_file, 'w') as f:
                json.dump(stats_to_save, f, indent=2)
            
            logger.info(f"Saved mapping statistics to {stats_file}")
            
        except Exception as e:
            logger.error(f"Error saving processed dataset: {e}")

    def create_readme_files(self):
        """
        Create README files for data directories
        """
        # Kaggle DDI README
        kaggle_readme = self.raw_dir / "raw_kaggle_ddi" / "README.md"
        kaggle_readme.parent.mkdir(parents=True, exist_ok=True)
        
        kaggle_content = """# Kaggle Drug-Drug Interactions Dataset

Place your Kaggle DDI dataset files here.

## Expected Files:
- `drug_interactions.csv` or similar
- Should contain columns: drug_a, drug_b, description
- Optional columns: severity, mechanism, sources

## Download Sources:
- Kaggle: Search for "drug drug interactions" datasets
- DrugBank: https://drugbank.ca/ (requires registration)
- SIDER: http://sideeffects.embl.de/

If no files are found, the system will create a sample dataset for testing.
"""
        
        with open(kaggle_readme, 'w') as f:
            f.write(kaggle_content)
        
        # RxNorm README
        rxnorm_readme = self.raw_dir / "raw_rxnorm_2025" / "README.md"
        rxnorm_readme.parent.mkdir(parents=True, exist_ok=True)
        
        rxnorm_content = """# RxNorm 2025 Dataset

Place RxNorm dataset files here for offline processing.

## Expected Files:
- `RXCONSO.RRF` - Main concepts file

## Download:
1. Visit: https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html
2. Download the latest RxNorm Full Monthly Release
3. Extract RXCONSO.RRF to this directory

If files are not present, the system will use the RxNorm API for lookups.
"""
        
        with open(rxnorm_readme, 'w') as f:
            f.write(rxnorm_content)

    def build_dataset(self):
        """
        Main function to build the complete dataset
        """
        logger.info("Starting dataset build process...")
        
        # Create README files
        self.create_readme_files()
        
        # Load raw DDI data
        ddi_df = self.load_kaggle_ddi_data()
        
        if ddi_df.empty:
            logger.error("No DDI data available. Cannot build dataset.")
            return False
        
        # Process and map to RxCUIs
        processed_df = self.process_ddi_dataset(ddi_df)
        
        if processed_df.empty:
            logger.error("Dataset processing failed.")
            return False
        
        # Save processed dataset
        self.save_processed_dataset(processed_df)
        
        # Print summary
        logger.info("Dataset build completed!")
        logger.info(f"Source medicines: {self.stats.get('source_medicines', 'Unknown')}")
        logger.info(f"Total interactions: {self.stats['total_interactions']}")
        logger.info(f"Mapped interactions: {self.stats['mapped_interactions']}")
        logger.info(f"Mapping coverage: {self.stats['mapping_coverage']:.1%}")
        logger.info(f"Unmapped drugs: {len(self.stats['unmapped_drugs'])}")
        
        if self.stats['unmapped_drugs']:
            logger.info("Sample unmapped drugs:")
            for drug in list(self.stats['unmapped_drugs'])[:10]:
                logger.info(f"  - {drug}")
        
        return True

def main():
    """
    Main execution function
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Build DDI dataset with RxCUI mapping")
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--inspect-only", action="store_true", help="Only inspect the dataset without processing")
    parser.add_argument("--max-interactions", type=int, default=1000, help="Maximum interactions to generate")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create dataset builder
    builder = DatasetBuilder(args.data_dir)
    
    if args.inspect_only:
        # Just inspect the dataset
        kaggle_dir = builder.raw_dir / "raw_kaggle_ddi"
        ddi_file = kaggle_dir / "ddi_dataset.csv"
        
        if ddi_file.exists():
            print(f"🔍 Inspecting dataset: {ddi_file}")
            df = pd.read_csv(ddi_file)
            print(f"📊 Dataset contains {len(df):,} medicine records")
            print(f"📋 Columns: {', '.join(df.columns)}")
            print(f"💊 Sample medicines: {', '.join(df['Medicine Name'].head(5).tolist())}")
            
            if 'Composition' in df.columns:
                compositions = df['Composition'].dropna()
                print(f"🧪 Compositions available: {len(compositions):,}")
                
            if 'Side_effects' in df.columns:
                side_effects = df['Side_effects'].dropna()
                print(f"⚠️  Side effects available: {len(side_effects):,}")
            
            # Estimate interaction potential
            unique_medicines = df['Medicine Name'].nunique()
            estimated_interactions = min(args.max_interactions, unique_medicines * 2)
            print(f"📈 Estimated DDI interactions to generate: ~{estimated_interactions}")
            
        else:
            print(f"❌ Dataset file not found: {ddi_file}")
        
        return 0
    
    # Set max interactions limit
    builder.max_interactions = args.max_interactions
    
    # Build dataset
    success = builder.build_dataset()
    
    if success:
        print("✅ Dataset build completed successfully!")
        print(f"📄 Output file: data/processed/ddi_mapped_with_rxcui.csv")
        return 0
    else:
        print("❌ Dataset build failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())