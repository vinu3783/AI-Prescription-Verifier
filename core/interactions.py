import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import itertools

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DrugInteractionChecker:
    """
    Drug-drug interaction checker using preprocessed DDI dataset
    """
    
    def __init__(self, dataset_path: str = "data/processed/ddi_mapped_with_rxcui.csv"):
        self.dataset_path = Path(dataset_path)
        self.interactions_df = None
        self.load_dataset()
    
    def load_dataset(self):
        """Load the drug-drug interaction dataset"""
        try:
            if self.dataset_path.exists():
                self.interactions_df = pd.read_csv(self.dataset_path)
                logger.info(f"✅ Loaded {len(self.interactions_df)} drug interactions from dataset")
            else:
                logger.warning(f"DDI dataset not found at {self.dataset_path}")
                self.create_sample_dataset()
                
        except Exception as e:
            logger.error(f"Error loading DDI dataset: {e}")
            self.create_sample_dataset()
    
    def create_sample_dataset(self):
        """Create a sample dataset for testing"""
        logger.info("Creating sample DDI dataset...")
        
        sample_data = [
            {
                'drug_a_name': 'warfarin',
                'drug_a_rxcui': '11289',
                'drug_b_name': 'aspirin', 
                'drug_b_rxcui': '1191',
                'interaction_text': 'Increased risk of bleeding. Monitor INR closely and adjust warfarin dose as needed.',
                'severity': 'high',
                'sources': 'DrugBank;Lexicomp'
            },
            {
                'drug_a_name': 'metformin',
                'drug_a_rxcui': '6809',
                'drug_b_name': 'ibuprofen',
                'drug_b_rxcui': '5640',
                'interaction_text': 'NSAIDs may reduce kidney function and affect metformin elimination.',
                'severity': 'medium',
                'sources': 'DrugBank'
            },
            {
                'drug_a_name': 'lisinopril',
                'drug_a_rxcui': '29046',
                'drug_b_name': 'ibuprofen',
                'drug_b_rxcui': '5640',
                'interaction_text': 'NSAIDs may reduce the antihypertensive effect of ACE inhibitors.',
                'severity': 'medium',
                'sources': 'DrugBank;Clinical'
            },
            {
                'drug_a_name': 'digoxin',
                'drug_a_rxcui': '3407',
                'drug_b_name': 'furosemide',
                'drug_b_rxcui': '4603',
                'interaction_text': 'Furosemide may increase digoxin levels by causing hypokalemia.',
                'severity': 'high',
                'sources': 'Lexicomp'
            },
            {
                'drug_a_name': 'simvastatin',
                'drug_a_rxcui': '36567',
                'drug_b_name': 'amlodipine',
                'drug_b_rxcui': '17767',
                'interaction_text': 'Amlodipine may increase simvastatin levels. Consider dose reduction.',
                'severity': 'medium',
                'sources': 'FDA;DrugBank'
            },
            {
                'drug_a_name': 'warfarin',
                'drug_a_rxcui': '11289',
                'drug_b_name': 'amoxicillin',
                'drug_b_rxcui': '723',
                'interaction_text': 'Antibiotics may alter gut flora and affect warfarin metabolism.',
                'severity': 'medium',
                'sources': 'Clinical'
            },
            {
                'drug_a_name': 'tramadol',
                'drug_a_rxcui': '10689',
                'drug_b_name': 'sertraline',
                'drug_b_rxcui': '36437',
                'interaction_text': 'Increased risk of serotonin syndrome. Monitor for symptoms.',
                'severity': 'high',
                'sources': 'FDA;DrugBank'
            },
            {
                'drug_a_name': 'atorvastatin',
                'drug_a_rxcui': '83367',
                'drug_b_name': 'clarithromycin',
                'drug_b_rxcui': '21212',
                'interaction_text': 'Clarithromycin may significantly increase statin levels and risk of myopathy.',
                'severity': 'high',
                'sources': 'FDA;Lexicomp'
            }
        ]
        
        self.interactions_df = pd.DataFrame(sample_data)
        
        # Ensure directory exists
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save sample dataset
        self.interactions_df.to_csv(self.dataset_path, index=False)
        logger.info(f"✅ Created sample DDI dataset with {len(self.interactions_df)} interactions")

    def find_interaction_by_rxcui(self, rxcui_a: str, rxcui_b: str) -> Optional[Dict]:
        """
        Find interaction between two RxCUI codes
        """
        if self.interactions_df is None or self.interactions_df.empty:
            return None
        
        try:
            # Check both directions (A-B and B-A)
            interaction = self.interactions_df[
                ((self.interactions_df['drug_a_rxcui'] == rxcui_a) & 
                 (self.interactions_df['drug_b_rxcui'] == rxcui_b)) |
                ((self.interactions_df['drug_a_rxcui'] == rxcui_b) & 
                 (self.interactions_df['drug_b_rxcui'] == rxcui_a))
            ]
            
            if not interaction.empty:
                return interaction.iloc[0].to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding interaction for RxCUIs {rxcui_a}, {rxcui_b}: {e}")
            return None

    def find_interaction_by_name(self, drug_a: str, drug_b: str) -> Optional[Dict]:
        """
        Find interaction between two drug names
        """
        if self.interactions_df is None or self.interactions_df.empty:
            return None
        
        try:
            # Normalize drug names for comparison
            drug_a_lower = drug_a.lower().strip()
            drug_b_lower = drug_b.lower().strip()
            
            # Check both directions
            interaction = self.interactions_df[
                ((self.interactions_df['drug_a_name'].str.lower() == drug_a_lower) & 
                 (self.interactions_df['drug_b_name'].str.lower() == drug_b_lower)) |
                ((self.interactions_df['drug_a_name'].str.lower() == drug_b_lower) & 
                 (self.interactions_df['drug_b_name'].str.lower() == drug_a_lower))
            ]
            
            if not interaction.empty:
                return interaction.iloc[0].to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding interaction for drugs {drug_a}, {drug_b}: {e}")
            return None

def find_interactions(rxcuis: List[str]) -> List[Dict[str, Any]]:
    """
    Find all interactions between a list of RxCUI codes
    
    Args:
        rxcuis: List of RxCUI codes
        
    Returns:
        List of interaction dictionaries
    """
    if not rxcuis or len(rxcuis) < 2:
        return []
    
    try:
        checker = DrugInteractionChecker()
        interactions = []
        
        # Check all pairs of drugs
        for rxcui_a, rxcui_b in itertools.combinations(rxcuis, 2):
            if rxcui_a and rxcui_b:
                interaction = checker.find_interaction_by_rxcui(rxcui_a, rxcui_b)
                if interaction:
                    # Format interaction for UI
                    formatted_interaction = {
                        'drug_a': interaction.get('drug_a_name', ''),
                        'drug_b': interaction.get('drug_b_name', ''),
                        'drug_a_rxcui': interaction.get('drug_a_rxcui', ''),
                        'drug_b_rxcui': interaction.get('drug_b_rxcui', ''),
                        'description': interaction.get('interaction_text', ''),
                        'severity': interaction.get('severity', 'medium'),
                        'sources': interaction.get('sources', ''),
                        'advice': interaction.get('interaction_text', '')
                    }
                    interactions.append(formatted_interaction)
        
        logger.info(f"Found {len(interactions)} interactions among {len(rxcuis)} drugs")
        return interactions
        
    except Exception as e:
        logger.error(f"Error finding interactions: {e}")
        return []

def find_interactions_by_names(drug_names: List[str]) -> List[Dict[str, Any]]:
    """
    Find interactions between drug names
    
    Args:
        drug_names: List of drug names
        
    Returns:
        List of interaction dictionaries
    """
    if not drug_names or len(drug_names) < 2:
        return []
    
    try:
        checker = DrugInteractionChecker()
        interactions = []
        
        # Check all pairs of drugs
        for drug_a, drug_b in itertools.combinations(drug_names, 2):
            if drug_a and drug_b:
                interaction = checker.find_interaction_by_name(drug_a, drug_b)
                if interaction:
                    formatted_interaction = {
                        'drug_a': interaction.get('drug_a_name', ''),
                        'drug_b': interaction.get('drug_b_name', ''),
                        'drug_a_rxcui': interaction.get('drug_a_rxcui', ''),
                        'drug_b_rxcui': interaction.get('drug_b_rxcui', ''),
                        'description': interaction.get('interaction_text', ''),
                        'severity': interaction.get('severity', 'medium'),
                        'sources': interaction.get('sources', ''),
                        'advice': interaction.get('interaction_text', '')
                    }
                    interactions.append(formatted_interaction)
        
        logger.info(f"Found {len(interactions)} interactions among drugs: {drug_names}")
        return interactions
        
    except Exception as e:
        logger.error(f"Error finding interactions by names: {e}")
        return []

def get_interaction_summary(interactions: List[Dict]) -> Dict[str, Any]:
    """
    Get summary statistics of interactions
    """
    if not interactions:
        return {
            'total': 0,
            'high_severity': 0,
            'medium_severity': 0,
            'low_severity': 0,
            'max_severity': 'none'
        }
    
    severity_counts = {'high': 0, 'medium': 0, 'low': 0}
    
    for interaction in interactions:
        severity = interaction.get('severity', 'medium').lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Determine max severity
    max_severity = 'low'
    if severity_counts['high'] > 0:
        max_severity = 'high'
    elif severity_counts['medium'] > 0:
        max_severity = 'medium'
    
    return {
        'total': len(interactions),
        'high_severity': severity_counts['high'],
        'medium_severity': severity_counts['medium'],
        'low_severity': severity_counts['low'],
        'max_severity': max_severity
    }

def test_interactions():
    """Test drug interaction functionality"""
    try:
        # Test with known interacting drugs
        test_rxcuis = ['11289', '1191']  # warfarin, aspirin
        
        interactions = find_interactions(test_rxcuis)
        print(f"Found {len(interactions)} interactions")
        
        if interactions:
            for interaction in interactions:
                print(f"- {interaction['drug_a']} ↔ {interaction['drug_b']}: {interaction['severity']}")
        
        # Test with drug names
        test_drugs = ['warfarin', 'aspirin']
        interactions_by_name = find_interactions_by_names(test_drugs)
        print(f"Found {len(interactions_by_name)} interactions by name")
        
        print("✅ Drug interaction test completed")
        return True
        
    except Exception as e:
        print(f"❌ Drug interaction test failed: {e}")
        return False

if __name__ == "__main__":
    test_interactions()