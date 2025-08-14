import requests
import time
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RxNormAPI:
    """
    RxNorm API client for drug information lookup
    """
    
    def __init__(self):
        self.base_url = "https://rxnav.nlm.nih.gov/REST"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Prescription-Verifier/1.0',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """
        Make a rate-limited request to RxNorm API
        """
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            self.last_request_time = time.time()
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"RxNorm API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse RxNorm API response: {e}")
            return None

    @lru_cache(maxsize=1000)
    def get_rxcui(self, name: str) -> Optional[str]:
        """
        Get RxCUI for a drug name
        """
        if not name or not name.strip():
            return None
        
        # Clean the drug name
        clean_name = name.strip().lower()
        
        try:
            # Try exact match first
            data = self._make_request(f"rxcui.json", {"name": clean_name})
            
            if data and 'idGroup' in data and 'rxnormId' in data['idGroup']:
                rxcuis = data['idGroup']['rxnormId']
                if rxcuis:
                    logger.info(f"Found RxCUI for '{name}': {rxcuis[0]}")
                    return rxcuis[0]
            
            # Try approximate match
            data = self._make_request(f"approximateTerm.json", {"term": clean_name})
            
            if data and 'approximateGroup' in data and 'candidate' in data['approximateGroup']:
                candidates = data['approximateGroup']['candidate']
                if candidates:
                    # Return the first candidate's RxCUI
                    first_candidate = candidates[0] if isinstance(candidates, list) else candidates
                    rxcui = first_candidate.get('rxcui')
                    if rxcui:
                        logger.info(f"Found approximate RxCUI for '{name}': {rxcui}")
                        return rxcui
            
            logger.warning(f"No RxCUI found for drug: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting RxCUI for '{name}': {e}")
            return None

    @lru_cache(maxsize=500)
    def get_scds(self, rxcui: str) -> List[Dict[str, str]]:
        """
        Get Semantic Clinical Drugs (SCDs) for an RxCUI
        """
        if not rxcui:
            return []
        
        try:
            data = self._make_request(f"rxcui/{rxcui}/related.json", {"tty": "SCD"})
            
            if data and 'relatedGroup' in data and 'conceptGroup' in data['relatedGroup']:
                concept_groups = data['relatedGroup']['conceptGroup']
                
                scds = []
                for group in concept_groups:
                    if 'conceptProperties' in group:
                        for concept in group['conceptProperties']:
                            scds.append({
                                'rxcui': concept.get('rxcui', ''),
                                'name': concept.get('name', ''),
                                'tty': concept.get('tty', '')
                            })
                
                logger.info(f"Found {len(scds)} SCDs for RxCUI {rxcui}")
                return scds
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting SCDs for RxCUI {rxcui}: {e}")
            return []

    @lru_cache(maxsize=500)
    def get_ingredient(self, rxcui: str) -> Optional[str]:
        """
        Get ingredient RxCUI for a drug
        """
        if not rxcui:
            return None
        
        try:
            data = self._make_request(f"rxcui/{rxcui}/related.json", {"tty": "IN"})
            
            if data and 'relatedGroup' in data and 'conceptGroup' in data['relatedGroup']:
                concept_groups = data['relatedGroup']['conceptGroup']
                
                for group in concept_groups:
                    if 'conceptProperties' in group:
                        for concept in group['conceptProperties']:
                            if concept.get('tty') == 'IN':
                                ingredient_rxcui = concept.get('rxcui')
                                logger.info(f"Found ingredient RxCUI for {rxcui}: {ingredient_rxcui}")
                                return ingredient_rxcui
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting ingredient for RxCUI {rxcui}: {e}")
            return None

    @lru_cache(maxsize=500)
    def get_brands(self, ingredient_rxcui: str) -> List[str]:
        """
        Get brand alternatives for an ingredient
        """
        if not ingredient_rxcui:
            return []
        
        try:
            data = self._make_request(f"rxcui/{ingredient_rxcui}/related.json", {"tty": "SBD"})
            
            if data and 'relatedGroup' in data and 'conceptGroup' in data['relatedGroup']:
                concept_groups = data['relatedGroup']['conceptGroup']
                
                brands = []
                for group in concept_groups:
                    if 'conceptProperties' in group:
                        for concept in group['conceptProperties']:
                            if concept.get('tty') == 'SBD':
                                brand_name = concept.get('name', '')
                                if brand_name and brand_name not in brands:
                                    brands.append(brand_name)
                
                logger.info(f"Found {len(brands)} brand alternatives for ingredient {ingredient_rxcui}")
                return brands[:10]  # Limit to top 10 brands
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting brands for ingredient {ingredient_rxcui}: {e}")
            return []

    def get_drug_strengths(self, rxcui: str) -> List[str]:
        """
        Get available strengths for a drug
        """
        if not rxcui:
            return []
        
        try:
            # Get related concepts including different strengths
            data = self._make_request(f"rxcui/{rxcui}/related.json")
            
            strengths = []
            if data and 'relatedGroup' in data and 'conceptGroup' in data['relatedGroup']:
                concept_groups = data['relatedGroup']['conceptGroup']
                
                for group in concept_groups:
                    if 'conceptProperties' in group:
                        for concept in group['conceptProperties']:
                            name = concept.get('name', '')
                            # Extract strength information from name
                            import re
                            strength_match = re.search(r'\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b', name, re.IGNORECASE)
                            if strength_match:
                                strength = strength_match.group()
                                if strength not in strengths:
                                    strengths.append(strength)
            
            return strengths
            
        except Exception as e:
            logger.error(f"Error getting strengths for RxCUI {rxcui}: {e}")
            return []

# Convenience functions for easy use
@lru_cache(maxsize=1000)
def get_rxcui(name: str) -> Optional[str]:
    """Get RxCUI for a drug name"""
    api = RxNormAPI()
    return api.get_rxcui(name)

@lru_cache(maxsize=500)
def get_scds(rxcui: str) -> List[Dict[str, str]]:
    """Get SCDs for an RxCUI"""
    api = RxNormAPI()
    return api.get_scds(rxcui)

@lru_cache(maxsize=500)
def get_ingredient(rxcui: str) -> Optional[str]:
    """Get ingredient RxCUI"""
    api = RxNormAPI()
    return api.get_ingredient(rxcui)

@lru_cache(maxsize=500)
def get_brands(ingredient_rxcui: str) -> List[str]:
    """Get brand alternatives"""
    api = RxNormAPI()
    return api.get_brands(ingredient_rxcui)

def get_drug_info(drug_name: str) -> Dict[str, Any]:
    """
    Get comprehensive drug information
    """
    result = {
        'name': drug_name,
        'rxcui': None,
        'ingredient_rxcui': None,
        'scds': [],
        'brands': [],
        'strengths': []
    }
    
    try:
        api = RxNormAPI()
        
        # Get RxCUI
        rxcui = api.get_rxcui(drug_name)
        if not rxcui:
            return result
        
        result['rxcui'] = rxcui
        
        # Get SCDs
        result['scds'] = api.get_scds(rxcui)
        
        # Get ingredient
        ingredient_rxcui = api.get_ingredient(rxcui)
        if ingredient_rxcui:
            result['ingredient_rxcui'] = ingredient_rxcui
            
            # Get brand alternatives
            result['brands'] = api.get_brands(ingredient_rxcui)
        
        # Get available strengths
        result['strengths'] = api.get_drug_strengths(rxcui)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting drug info for '{drug_name}': {e}")
        return result

def test_rxnorm_api():
    """Test RxNorm API functionality"""
    try:
        # Test with a common drug
        test_drug = "aspirin"
        
        print(f"Testing with drug: {test_drug}")
        
        # Test RxCUI lookup
        rxcui = get_rxcui(test_drug)
        print(f"RxCUI: {rxcui}")
        
        if rxcui:
            # Test SCDs
            scds = get_scds(rxcui)
            print(f"SCDs found: {len(scds)}")
            
            # Test ingredient
            ingredient = get_ingredient(rxcui)
            print(f"Ingredient RxCUI: {ingredient}")
            
            if ingredient:
                # Test brands
                brands = get_brands(ingredient)
                print(f"Brand alternatives: {brands[:3]}")  # Show first 3
        
        print("✅ RxNorm API test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ RxNorm API test failed: {e}")
        return False

if __name__ == "__main__":
    test_rxnorm_api()