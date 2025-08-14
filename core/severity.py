import logging
from typing import Literal, Dict
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeverityClassifier:
    """
    Classify severity of drug interactions using transformer models and rules
    """
    
    def __init__(self):
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        self.classifier = None
        self.load_model()
        
        # Severity keywords
        self.high_severity_keywords = [
            'contraindicated', 'dangerous', 'fatal', 'death', 'life-threatening',
            'severe', 'serious', 'emergency', 'hospitalization', 'toxic',
            'poisoning', 'overdose', 'respiratory depression', 'cardiac arrest',
            'serotonin syndrome', 'bleeding', 'hemorrhage', 'stroke', 'seizure'
        ]
        
        self.medium_severity_keywords = [
            'monitor', 'caution', 'adjust', 'reduce', 'increase', 'modify',
            'careful', 'watch', 'observe', 'check', 'avoid', 'consider',
            'may increase', 'may decrease', 'potential', 'risk', 'interaction'
        ]
        
        self.low_severity_keywords = [
            'minor', 'minimal', 'slight', 'theoretical', 'unlikely',
            'possible', 'rare', 'uncommon', 'mild', 'moderate interaction'
        ]

    def load_model(self):
        """Load the sentiment classification model"""
        try:
            logger.info("Loading sentiment classification model for severity...")
            self.classifier = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("✅ Severity classification model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load transformer model: {e}")
            logger.info("Falling back to rule-based severity classification")
            self.classifier = None

    def classify_with_transformer(self, text: str) -> Dict:
        """
        Use transformer model to get sentiment as proxy for severity
        """
        if not self.classifier or not text:
            return {"label": "NEUTRAL", "score": 0.5}
        
        try:
            # Clean text for better classification
            clean_text = self.clean_text_for_classification(text)
            
            result = self.classifier(clean_text)
            return result[0] if isinstance(result, list) else result
            
        except Exception as e:
            logger.error(f"Transformer severity classification failed: {e}")
            return {"label": "NEUTRAL", "score": 0.5}

    def clean_text_for_classification(self, text: str) -> str:
        """
        Clean and prepare text for classification
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Limit length for transformer
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text

    def classify_with_rules(self, text: str) -> Literal["low", "medium", "high"]:
        """
        Rule-based severity classification using keywords
        """
        if not text:
            return "medium"
        
        text_lower = text.lower()
        
        # Count keyword matches
        high_count = sum(1 for keyword in self.high_severity_keywords if keyword in text_lower)
        medium_count = sum(1 for keyword in self.medium_severity_keywords if keyword in text_lower)
        low_count = sum(1 for keyword in self.low_severity_keywords if keyword in text_lower)
        
        # Additional pattern matching
        critical_patterns = [
            r'\b(?:do not|never|avoid)\b.*\b(?:combine|use together|concurrent)\b',
            r'\bcontraindicated\b',
            r'\b(?:severe|serious|life-threatening)\b.*\b(?:reaction|effect|outcome)\b',
            r'\b(?:death|fatal|mortality)\b',
            r'\bemergency\b.*\brequired\b'
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, text_lower):
                high_count += 2
        
        # Warning patterns
        warning_patterns = [
            r'\bmonitor\b.*\b(?:closely|carefully|frequently)\b',
            r'\b(?:adjust|reduce|modify)\b.*\bdose\b',
            r'\bmay (?:increase|decrease|affect)\b',
            r'\bcaution\b.*\brequired\b'
        ]
        
        for pattern in warning_patterns:
            if re.search(pattern, text_lower):
                medium_count += 1
        
        # Determine severity based on counts
        if high_count >= 2:
            return "high"
        elif high_count == 1 and medium_count >= 1:
            return "high"
        elif low_count >= 2 and high_count == 0:
            return "low"
        elif medium_count >= 2:
            return "medium"
        elif high_count >= 1:
            return "high"
        else:
            return "medium"  # Default to medium when unclear

    def classify_severity(self, text: str) -> Literal["low", "medium", "high"]:
        """
        Main severity classification function combining transformer and rules
        """
        if not text or not text.strip():
            return "medium"
        
        try:
            # Get rule-based classification
            rule_severity = self.classify_with_rules(text)
            
            # Get transformer-based sentiment
            transformer_result = self.classify_with_transformer(text)
            
            # Combine results
            if self.classifier:
                sentiment = transformer_result.get("label", "NEUTRAL")
                confidence = transformer_result.get("score", 0.5)
                
                # Adjust rule-based severity using sentiment
                if sentiment == "NEGATIVE" and confidence > 0.8:
                    # High confidence negative sentiment suggests higher severity
                    if rule_severity == "low":
                        rule_severity = "medium"
                    elif rule_severity == "medium":
                        rule_severity = "high"
                elif sentiment == "POSITIVE" and confidence > 0.8:
                    # High confidence positive sentiment suggests lower severity
                    if rule_severity == "high":
                        rule_severity = "medium"
                    elif rule_severity == "medium":
                        rule_severity = "low"
            
            logger.info(f"Classified severity as '{rule_severity}' for text snippet")
            return rule_severity
            
        except Exception as e:
            logger.error(f"Severity classification failed: {e}")
            return "medium"  # Safe default

def classify_severity(text: str) -> Literal["low", "medium", "high"]:
    """
    Convenience function for severity classification
    
    Args:
        text: Interaction description text
        
    Returns:
        Severity level: "low", "medium", or "high"
    """
    classifier = SeverityClassifier()
    return classifier.classify_severity(text)

def classify_multiple_interactions(interactions: list) -> list:
    """
    Classify severity for multiple interactions efficiently
    """
    classifier = SeverityClassifier()
    
    for interaction in interactions:
        if 'description' in interaction or 'interaction_text' in interaction:
            text = interaction.get('description') or interaction.get('interaction_text', '')
            interaction['severity'] = classifier.classify_severity(text)
        else:
            interaction['severity'] = 'medium'
    
    return interactions

def get_severity_color(severity: str) -> str:
    """
    Get color code for severity level
    """
    color_map = {
        'low': '#28a745',      # Green
        'medium': '#ffc107',   # Yellow/Orange
        'high': '#dc3545'      # Red
    }
    return color_map.get(severity.lower(), '#6c757d')  # Gray as default

def get_severity_icon(severity: str) -> str:
    """
    Get icon for severity level
    """
    icon_map = {
        'low': '🟢',
        'medium': '🟡', 
        'high': '🔴'
    }
    return icon_map.get(severity.lower(), '⚪')

def test_severity_classification():
    """
    Test severity classification functionality
    """
    test_cases = [
        {
            'text': 'Contraindicated. May cause life-threatening bleeding.',
            'expected': 'high'
        },
        {
            'text': 'Monitor patient closely and adjust dose as needed.',
            'expected': 'medium'
        },
        {
            'text': 'Minor interaction with minimal clinical significance.',
            'expected': 'low'
        },
        {
            'text': 'Serotonin syndrome may occur. Avoid concurrent use.',
            'expected': 'high'
        },
        {
            'text': 'May increase drug levels. Consider dose reduction.',
            'expected': 'medium'
        }
    ]
    
    try:
        classifier = SeverityClassifier()
        correct = 0
        total = len(test_cases)
        
        for case in test_cases:
            predicted = classifier.classify_severity(case['text'])
            expected = case['expected']
            
            print(f"Text: {case['text'][:50]}...")
            print(f"Expected: {expected}, Predicted: {predicted}")
            
            if predicted == expected:
                correct += 1
                print("✅ Correct")
            else:
                print("❌ Incorrect")
            print("-" * 50)
        
        accuracy = correct / total
        print(f"Accuracy: {accuracy:.2%} ({correct}/{total})")
        
        return accuracy >= 0.6  # Accept 60% accuracy for test
        
    except Exception as e:
        print(f"❌ Severity classification test failed: {e}")
        return False

if __name__ == "__main__":
    if test_severity_classification():
        print("✅ Severity classification module is working")
    else:
        print("❌ Severity classification module has issues")