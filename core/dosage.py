import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from core.rxcui import get_drug_info, get_brands, get_ingredient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DosageVerifier:
    """
    Verify dosages and suggest corrections based on age and standard guidelines
    """
    
    def __init__(self):
        # Standard adult dosage ranges for common drugs (mg)
        self.standard_dosages = {
            'paracetamol': {'min': 325, 'max': 1000, 'frequency': 'q4-6h', 'max_daily': 4000},
            'acetaminophen': {'min': 325, 'max': 1000, 'frequency': 'q4-6h', 'max_daily': 4000},
            'ibuprofen': {'min': 200, 'max': 800, 'frequency': 'q6-8h', 'max_daily': 3200},
            'aspirin': {'min': 81, 'max': 650, 'frequency': 'q4-6h', 'max_daily': 4000},
            'metformin': {'min': 500, 'max': 1000, 'frequency': 'bid', 'max_daily': 2500},
            'lisinopril': {'min': 2.5, 'max': 40, 'frequency': 'daily', 'max_daily': 40},
            'amlodipine': {'min': 2.5, 'max': 10, 'frequency': 'daily', 'max_daily': 10},
            'simvastatin': {'min': 5, 'max': 80, 'frequency': 'daily', 'max_daily': 80},
            'warfarin': {'min': 1, 'max': 10, 'frequency': 'daily', 'max_daily': 15},
            'digoxin': {'min': 0.125, 'max': 0.5, 'frequency': 'daily', 'max_daily': 0.5},
            'furosemide': {'min': 20, 'max': 80, 'frequency': 'daily', 'max_daily': 600},
            'amoxicillin': {'min': 250, 'max': 1000, 'frequency': 'tid', 'max_daily': 3000}
        }
        
        # Age-based dosage adjustment factors
        self.age_factors = {
            'pediatric': {'min_age': 0, 'max_age': 12, 'factor': 0.5, 'special_rules': True},
            'adolescent': {'min_age': 13, 'max_age': 17, 'factor': 0.8, 'special_rules': True},
            'adult': {'min_age': 18, 'max_age': 64, 'factor': 1.0, 'special_rules': False},
            'elderly': {'min_age': 65, 'max_age': 120, 'factor': 0.75, 'special_rules': True}
        }

    def parse_dose(self, dose_string: str) -> Optional[Dict[str, Any]]:
        """
        Parse dose string to extract numeric value and unit
        """
        if not dose_string:
            return None
        
        # Common dose patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units?)',
            r'(\d+(?:\.\d+)?)\s*(milligrams?|micrograms?|grams?|milliliters?)',
            r'(\d+(?:\.\d+)?)\s*(tablet|cap|capsule)s?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, dose_string, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()
                
                # Normalize units
                unit_map = {
                    'milligram': 'mg', 'milligrams': 'mg',
                    'microgram': 'mcg', 'micrograms': 'mcg',
                    'gram': 'g', 'grams': 'g',
                    'milliliter': 'ml', 'milliliters': 'ml',
                    'tablet': 'tablet', 'cap': 'capsule', 'capsule': 'capsule'
                }
                
                normalized_unit = unit_map.get(unit, unit)
                
                return {
                    'value': value,
                    'unit': normalized_unit,
                    'original': dose_string
                }
        
        logger.warning(f"Could not parse dose: {dose_string}")
        return None

    def get_age_category(self, age: int) -> str:
        """
        Determine age category for dosage adjustments
        """
        for category, info in self.age_factors.items():
            if info['min_age'] <= age <= info['max_age']:
                return category
        return 'adult'  # default

    def get_drug_standard_range(self, drug_name: str) -> Optional[Dict]:
        """
        Get standard dosage range for a drug
        """
        drug_lower = drug_name.lower().strip()
        
        # Direct lookup
        if drug_lower in self.standard_dosages:
            return self.standard_dosages[drug_lower]
        
        # Partial matching for brand names
        for standard_drug in self.standard_dosages:
            if standard_drug in drug_lower or drug_lower in standard_drug:
                return self.standard_dosages[standard_drug]
        
        return None

    def check_dose_against_standard(self, parsed_dose: Dict, standard_range: Dict, age_factor: float) -> Dict:
        """
        Check if dose is within acceptable range
        """
        if parsed_dose['unit'] not in ['mg', 'mcg', 'g']:
            # Can't verify non-weight units reliably
            return {
                'status': 'unknown',
                'reason': f"Cannot verify {parsed_dose['unit']} doses automatically"
            }
        
        dose_value = parsed_dose['value']
        
        # Convert to mg for comparison
        if parsed_dose['unit'] == 'g':
            dose_value *= 1000
        elif parsed_dose['unit'] == 'mcg':
            dose_value /= 1000
        
        # Apply age adjustment
        adjusted_min = standard_range['min'] * age_factor
        adjusted_max = standard_range['max'] * age_factor
        
        if dose_value < adjusted_min * 0.5:  # Significantly below minimum
            return {
                'status': 'too_low',
                'reason': f"Dose may be too low (minimum recommended: {adjusted_min:.1f}mg)",
                'suggested_min': adjusted_min,
                'suggested_max': adjusted_max
            }
        elif dose_value > adjusted_max * 1.5:  # Significantly above maximum
            return {
                'status': 'too_high',
                'reason': f"Dose may be too high (maximum recommended: {adjusted_max:.1f}mg)",
                'suggested_min': adjusted_min,
                'suggested_max': adjusted_max
            }
        elif adjusted_min <= dose_value <= adjusted_max:
            return {
                'status': 'appropriate',
                'reason': "Dose is within recommended range"
            }
        else:
            return {
                'status': 'borderline',
                'reason': f"Dose is outside typical range ({adjusted_min:.1f}-{adjusted_max:.1f}mg)",
                'suggested_min': adjusted_min,
                'suggested_max': adjusted_max
            }

    def get_pediatric_considerations(self, drug_name: str, age: int) -> List[str]:
        """
        Get special considerations for pediatric patients
        """
        considerations = []
        drug_lower = drug_name.lower()
        
        # Age-specific warnings
        if age < 2:
            considerations.append("Consult pediatrician for infants under 2 years")
        
        # Drug-specific pediatric considerations
        pediatric_warnings = {
            'aspirin': "Avoid in children under 16 due to Reye's syndrome risk",
            'ibuprofen': "Not recommended for infants under 6 months",
            'paracetamol': "Dose based on weight: 10-15mg/kg every 4-6 hours",
            'acetaminophen': "Dose based on weight: 10-15mg/kg every 4-6 hours",
            'codeine': "Contraindicated in children under 12 years",
            'tramadol': "Not recommended for children under 12 years"
        }
        
        for drug, warning in pediatric_warnings.items():
            if drug in drug_lower:
                considerations.append(warning)
        
        return considerations

    def get_elderly_considerations(self, drug_name: str, age: int) -> List[str]:
        """
        Get special considerations for elderly patients
        """
        considerations = []
        drug_lower = drug_name.lower()
        
        # General elderly considerations
        if age >= 80:
            considerations.append("Consider 'start low, go slow' approach for patients over 80")
        
        # Drug-specific elderly considerations
        elderly_warnings = {
            'digoxin': "Increased risk of toxicity; monitor levels closely",
            'warfarin': "Higher bleeding risk; more frequent INR monitoring",
            'benzodiazepine': "Increased fall risk; consider shorter-acting alternatives",
            'anticholinergic': "May cause confusion; monitor cognitive function",
            'nsaid': "Increased GI and cardiovascular risks",
            'ibuprofen': "Monitor kidney function and blood pressure",
            'diuretic': "Monitor for dehydration and electrolyte imbalances"
        }
        
        for drug_class, warning in elderly_warnings.items():
            if drug_class in drug_lower:
                considerations.append(warning)
        
        return considerations

    def suggest_alternatives(self, drug_name: str, rxcui: str) -> List[str]:
        """
        Suggest alternative formulations or brands
        """
        alternatives = []
        
        try:
            # Get ingredient and brand alternatives
            ingredient_rxcui = get_ingredient(rxcui) if rxcui else None
            if ingredient_rxcui:
                brands = get_brands(ingredient_rxcui)
                alternatives.extend(brands[:5])  # Top 5 alternatives
            
            # Add generic alternatives based on drug class
            drug_lower = drug_name.lower()
            
            alternative_map = {
                'ibuprofen': ['naproxen', 'diclofenac', 'celecoxib'],
                'paracetamol': ['ibuprofen (if no contraindications)'],
                'acetaminophen': ['ibuprofen (if no contraindications)'],
                'simvastatin': ['atorvastatin', 'rosuvastatin'],
                'lisinopril': ['enalapril', 'ramipril', 'losartan'],
                'amlodipine': ['nifedipine', 'felodipine', 'verapamil']
            }
            
            for drug, alts in alternative_map.items():
                if drug in drug_lower:
                    alternatives.extend(alts)
            
        except Exception as e:
            logger.error(f"Error getting alternatives for {drug_name}: {e}")
        
        return list(set(alternatives))  # Remove duplicates

def check_dosage(entities: List[Dict], age: int) -> List[Dict[str, Any]]:
    """
    Main function to check dosages for extracted entities
    
    Args:
        entities: List of extracted drug entities
        age: Patient age
        
    Returns:
        List of dosage verification results
    """
    if not entities:
        return []
    
    verifier = DosageVerifier()
    results = []
    
    age_category = verifier.get_age_category(age)
    age_factor = verifier.age_factors[age_category]['factor']
    
    for entity in entities:
        drug_name = entity.get('drug', '')
        dose_string = entity.get('dose', '')
        frequency = entity.get('frequency', '')
        rxcui = entity.get('rxcui', '')
        
        if not drug_name:
            continue
        
        result = {
            'drug': drug_name,
            'mentioned_dose': dose_string,
            'frequency': frequency,
            'rxcui': rxcui,
            'age_category': age_category,
            'dose_status': 'unknown',
            'considerations': [],
            'alternatives': [],
            'suggested_dose': None
        }
        
        try:
            # Parse the mentioned dose
            parsed_dose = verifier.parse_dose(dose_string) if dose_string else None
            
            # Get standard dosage range
            standard_range = verifier.get_drug_standard_range(drug_name)
            
            if parsed_dose and standard_range:
                # Check dose against standards
                dose_check = verifier.check_dose_against_standard(parsed_dose, standard_range, age_factor)
                result['dose_status'] = dose_check['status']
                result['dose_check_reason'] = dose_check['reason']
                
                # Suggest corrected dose if needed
                if 'suggested_min' in dose_check and 'suggested_max' in dose_check:
                    min_dose = dose_check['suggested_min']
                    max_dose = dose_check['suggested_max']
                    result['suggested_dose'] = f"{min_dose:.1f}-{max_dose:.1f}mg {standard_range.get('frequency', '')}"
            
            elif not standard_range:
                result['dose_status'] = 'unknown'
                result['dose_check_reason'] = 'No standard dosage information available for this drug'
            
            # Add age-specific considerations
            if age_category == 'pediatric':
                result['considerations'].extend(verifier.get_pediatric_considerations(drug_name, age))
            elif age_category == 'elderly':
                result['considerations'].extend(verifier.get_elderly_considerations(drug_name, age))
            
            # Get alternatives
            alternatives = verifier.suggest_alternatives(drug_name, rxcui)
            result['alternatives'] = alternatives
            
            # Overall assessment
            if result['dose_status'] in ['appropriate', 'unknown']:
                result['overall_status'] = 'valid'
            else:
                result['overall_status'] = 'needs_review'
            
        except Exception as e:
            logger.error(f"Error checking dosage for {drug_name}: {e}")
            result['dose_status'] = 'error'
            result['dose_check_reason'] = f"Error during verification: {e}"
        
        results.append(result)
    
    logger.info(f"✅ Checked dosages for {len(results)} drugs")
    return results

def get_weight_based_dose(drug_name: str, weight_kg: float, age: int) -> Optional[str]:
    """
    Calculate weight-based dosing for pediatric patients
    """
    drug_lower = drug_name.lower()
    
    # Weight-based dosing guidelines (mg/kg)
    weight_based_doses = {
        'paracetamol': {'dose_per_kg': 15, 'frequency': 'q6h', 'max_per_kg': 60},
        'acetaminophen': {'dose_per_kg': 15, 'frequency': 'q6h', 'max_per_kg': 60},
        'ibuprofen': {'dose_per_kg': 10, 'frequency': 'q6-8h', 'max_per_kg': 40},
        'amoxicillin': {'dose_per_kg': 25, 'frequency': 'q8h', 'max_per_kg': 90}
    }
    
    for drug, dosing in weight_based_doses.items():
        if drug in drug_lower:
            dose = weight_kg * dosing['dose_per_kg']
            max_dose = weight_kg * dosing['max_per_kg']
            return f"{dose:.1f}mg {dosing['frequency']} (max daily: {max_dose:.1f}mg)"
    
    return None

def validate_frequency(frequency: str) -> Dict[str, Any]:
    """
    Validate and interpret dosing frequency
    """
    if not frequency:
        return {'valid': False, 'reason': 'No frequency specified'}
    
    freq_lower = frequency.lower().strip()
    
    # Common frequency patterns
    valid_frequencies = {
        'once daily': {'times_per_day': 1, 'interval_hours': 24},
        'twice daily': {'times_per_day': 2, 'interval_hours': 12},
        'three times daily': {'times_per_day': 3, 'interval_hours': 8},
        'four times daily': {'times_per_day': 4, 'interval_hours': 6},
        'bid': {'times_per_day': 2, 'interval_hours': 12},
        'tid': {'times_per_day': 3, 'interval_hours': 8},
        'qid': {'times_per_day': 4, 'interval_hours': 6},
        'qd': {'times_per_day': 1, 'interval_hours': 24},
        'q4h': {'times_per_day': 6, 'interval_hours': 4},
        'q6h': {'times_per_day': 4, 'interval_hours': 6},
        'q8h': {'times_per_day': 3, 'interval_hours': 8},
        'q12h': {'times_per_day': 2, 'interval_hours': 12}
    }
    
    for pattern, info in valid_frequencies.items():
        if pattern in freq_lower:
            return {
                'valid': True,
                'standardized': pattern,
                'times_per_day': info['times_per_day'],
                'interval_hours': info['interval_hours']
            }
    
    return {
        'valid': False,
        'reason': f'Unrecognized frequency pattern: {frequency}'
    }

def test_dosage_verification():
    """
    Test dosage verification functionality
    """
    test_entities = [
        {
            'drug': 'paracetamol',
            'dose': '500mg',
            'frequency': 'twice daily',
            'rxcui': '161'
        },
        {
            'drug': 'ibuprofen',
            'dose': '200mg',
            'frequency': 'three times daily',
            'rxcui': '5640'
        },
        {
            'drug': 'unknown_drug',
            'dose': '100mg',
            'frequency': 'once daily',
            'rxcui': None
        }
    ]
    
    test_ages = [5, 30, 75]  # pediatric, adult, elderly
    
    try:
        for age in test_ages:
            print(f"\n=== Testing for age {age} ===")
            results = check_dosage(test_entities, age)
            
            for result in results:
                print(f"Drug: {result['drug']}")
                print(f"Status: {result['dose_status']}")
                print(f"Age category: {result['age_category']}")
                if result.get('considerations'):
                    print(f"Considerations: {result['considerations']}")
                print("-" * 40)
        
        print("✅ Dosage verification test completed")
        return True
        
    except Exception as e:
        print(f"❌ Dosage verification test failed: {e}")
        return False

if __name__ == "__main__":
    if test_dosage_verification():
        print("✅ Dosage verification module is working")
    else:
        print("❌ Dosage verification module has issues")