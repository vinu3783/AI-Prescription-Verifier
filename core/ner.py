import re
import logging
from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalNER:
    def __init__(self):
        self.model_name = "samrawal/bert-base-uncased-medical-ner"
        self.tokenizer = None
        self.model = None
        self.ner_pipeline = None
        self.load_model()
        
    def load_model(self):
        """Load the medical NER model"""
        try:
            logger.info("Loading medical NER model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            
            # Create pipeline
            self.ner_pipeline = pipeline(
                "ner", 
                model=self.model, 
                tokenizer=self.tokenizer,
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("✅ Medical NER model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load Hugging Face model: {e}")
            logger.info("Falling back to rule-based NER")
            self.ner_pipeline = None

    def extract_with_transformer(self, text: str) -> List[Dict]:
        """Extract entities using transformer model"""
        if not self.ner_pipeline:
            return []
            
        try:
            # Run NER pipeline
            entities = self.ner_pipeline(text)
            
            # Process and clean entities
            processed_entities = []
            for entity in entities:
                if entity['entity_group'] in ['DRUG', 'MEDICATION', 'CHEMICAL']:
                    processed_entities.append({
                        'text': entity['word'],
                        'label': 'DRUG',
                        'confidence': entity['score'],
                        'start': entity['start'],
                        'end': entity['end']
                    })
                    
            return processed_entities
            
        except Exception as e:
            logger.error(f"Transformer NER failed: {e}")
            return []

    def extract_with_rules(self, text: str) -> List[Dict]:
        """Fallback rule-based entity extraction"""
        
        # Common drug name patterns
        drug_patterns = [
            r'\b[A-Z][a-z]+(?:cillin|mycin|prazole|olol|pine|zole|statin|fenac|coxib)\b',
            r'\b(?:aspirin|ibuprofen|acetaminophen|paracetamol|morphine|codeine|tramadol)\b',
            r'\b(?:metformin|insulin|warfarin|heparin|digoxin|furosemide|lisinopril)\b',
            r'\b(?:amoxicillin|azithromycin|ciprofloxacin|doxycycline|penicillin)\b',
            r'\b[A-Z][a-z]{3,15}\b(?=\s+(?:\d+\s*mg|\d+\s*ml|\d+\s*tablets?))'
        ]
        
        # Dosage patterns
        dose_patterns = [
            r'\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|cc|units?|iu)\b',
            r'\d+(?:\.\d+)?\s*(?:milligram|microgram|gram|milliliter)s?\b'
        ]
        
        # Frequency patterns
        frequency_patterns = [
            r'\b(?:once|twice|thrice|\d+\s*times?)\s+(?:daily|a\s+day|per\s+day)\b',
            r'\b(?:bid|tid|qid|qd|qhs|prn|q\d+h)\b',
            r'\b(?:every|q)\s+\d+\s+(?:hours?|hrs?|h)\b',
            r'\b(?:morning|evening|night|bedtime)\b'
        ]
        
        # Route patterns
        route_patterns = [
            r'\b(?:oral|po|by\s+mouth)\b',
            r'\b(?:iv|intravenous|intravenously)\b',
            r'\b(?:im|intramuscular|intramuscularly)\b',
            r'\b(?:topical|topically|applied)\b',
            r'\b(?:sublingual|sl|under\s+tongue)\b'
        ]
        
        entities = []
        
        # Extract drugs
        for pattern in drug_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': 'DRUG',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8
                })
        
        # Extract doses
        for pattern in dose_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': 'DOSE',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9
                })
        
        # Extract frequencies
        for pattern in frequency_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': 'FREQUENCY',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8
                })
        
        # Extract routes
        for pattern in route_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': 'ROUTE',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.7
                })
        
        return entities

def group_entities(entities: List[Dict], text: str) -> List[Dict]:
    """Group related entities into drug prescriptions"""
    
    # Sort entities by position
    entities.sort(key=lambda x: x['start'])
    
    # Group entities by proximity (within 50 characters)
    groups = []
    current_group = []
    
    for entity in entities:
        if not current_group:
            current_group.append(entity)
        else:
            # Check if entity is close to the last entity in current group
            last_entity = current_group[-1]
            if entity['start'] - last_entity['end'] <= 50:
                current_group.append(entity)
            else:
                # Start new group
                if current_group:
                    groups.append(current_group)
                current_group = [entity]
    
    # Add the last group
    if current_group:
        groups.append(current_group)
    
    # Convert groups to prescription objects
    prescriptions = []
    
    for group in groups:
        prescription = {
            'drug': None,
            'dose': None,
            'route': 'oral',  # default
            'frequency': None
        }
        
        # Extract information from group
        for entity in group:
            label = entity['label']
            text_value = entity['text'].strip()
            
            if label == 'DRUG' and not prescription['drug']:
                prescription['drug'] = text_value
            elif label == 'DOSE' and not prescription['dose']:
                prescription['dose'] = text_value
            elif label == 'ROUTE':
                prescription['route'] = text_value
            elif label == 'FREQUENCY' and not prescription['frequency']:
                prescription['frequency'] = text_value
        
        # Only add if we have at least a drug name
        if prescription['drug']:
            prescriptions.append(prescription)
    
    return prescriptions

def clean_drug_name(drug_name: str) -> str:
    """Clean and normalize drug names"""
    if not drug_name:
        return ""
    
    # Remove common prefixes and suffixes
    drug_name = re.sub(r'^(?:tab|tablet|cap|capsule|inj|injection)\s+', '', drug_name, flags=re.IGNORECASE)
    drug_name = re.sub(r'\s+(?:tab|tablet|cap|capsule|inj|injection)$', '', drug_name, flags=re.IGNORECASE)
    
    # Remove brand name indicators
    drug_name = re.sub(r'\s*\([^)]*\)\s*', '', drug_name)
    
    # Capitalize first letter
    drug_name = drug_name.strip().title()
    
    return drug_name

def normalize_dose(dose: str) -> str:
    """Normalize dose format"""
    if not dose:
        return ""
    
    # Standardize units
    dose = re.sub(r'\bmcg\b', 'mcg', dose, flags=re.IGNORECASE)
    dose = re.sub(r'\bmg\b', 'mg', dose, flags=re.IGNORECASE)
    dose = re.sub(r'\bg\b', 'g', dose, flags=re.IGNORECASE)
    dose = re.sub(r'\bml\b', 'ml', dose, flags=re.IGNORECASE)
    
    return dose.strip()

def normalize_frequency(frequency: str) -> str:
    """Normalize frequency format"""
    if not frequency:
        return ""
    
    # Common frequency mappings
    freq_map = {
        'bid': 'twice daily',
        'tid': 'three times daily',
        'qid': 'four times daily',
        'qd': 'once daily',
        'qhs': 'at bedtime',
        'prn': 'as needed'
    }
    
    freq_lower = frequency.lower().strip()
    
    for abbrev, full in freq_map.items():
        if abbrev in freq_lower:
            return full
    
    return frequency.strip()

def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Main function to extract medical entities from text
    
    Args:
        text: Input text from prescription
        
    Returns:
        List of dictionaries with drug information
    """
    
    if not text or not text.strip():
        return []
    
    try:
        # Initialize NER model
        ner_model = MedicalNER()
        
        # Try transformer model first
        entities = ner_model.extract_with_transformer(text)
        
        # If transformer fails or returns few results, use rule-based
        if len(entities) < 2:
            logger.info("Using rule-based NER as fallback")
            entities = ner_model.extract_with_rules(text)
        
        # Group entities into prescriptions
        prescriptions = group_entities(entities, text)
        
        # Clean and normalize
        for prescription in prescriptions:
            if prescription.get('drug'):
                prescription['drug'] = clean_drug_name(prescription['drug'])
            if prescription.get('dose'):
                prescription['dose'] = normalize_dose(prescription['dose'])
            if prescription.get('frequency'):
                prescription['frequency'] = normalize_frequency(prescription['frequency'])
        
        logger.info(f"✅ Extracted {len(prescriptions)} drug prescriptions")
        return prescriptions
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        # Return empty list instead of raising exception
        return []

# Test function
def test_ner():
    """Test NER functionality"""
    test_text = "Take Paracetamol 500mg twice daily by mouth. Apply Ibuprofen 200mg three times daily."
    
    try:
        entities = extract_entities(test_text)
        print(f"Test results: {entities}")
        return len(entities) > 0
    except Exception as e:
        print(f"NER test failed: {e}")
        return False

if __name__ == "__main__":
    if test_ner():
        print("✅ NER module is working correctly")
    else:
        print("❌ NER module has issues")