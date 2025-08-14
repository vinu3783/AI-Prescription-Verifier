import logging
from typing import Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalSummarizer:
    """
    Generate patient-friendly summaries of medical advice using BART
    """
    
    def __init__(self):
        self.model_name = "facebook/bart-large-cnn"
        self.summarizer = None
        self.tokenizer = None
        self.load_model()
        
        # Templates for different types of advice
        self.templates = {
            'interaction': "Drug interaction: {summary}",
            'dosage': "Dosage advice: {summary}",
            'general': "Medical advice: {summary}"
        }

    def load_model(self):
        """Load the BART summarization model"""
        try:
            logger.info("Loading BART summarization model...")
            
            # Load with smaller model if BART-large fails
            try:
                self.summarizer = pipeline(
                    "summarization",
                    model=self.model_name,
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info("✅ BART-large model loaded successfully")
            except:
                # Fallback to smaller model
                logger.info("Falling back to distilbart-cnn model...")
                self.summarizer = pipeline(
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6",
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info("✅ DistilBART model loaded successfully")
                
        except Exception as e:
            logger.warning(f"Failed to load summarization model: {e}")
            logger.info("Falling back to rule-based summarization")
            self.summarizer = None

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for better summarization
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove medical jargon and replace with simpler terms
        replacements = {
            'contraindicated': 'should not be used together',
            'concurrent use': 'using at the same time',
            'monitor closely': 'watch carefully',
            'adjust dose': 'change the amount',
            'pharmacokinetic': 'how the body processes the drug',
            'pharmacodynamic': 'how the drug affects the body',
            'bioavailability': 'how much drug enters the bloodstream',
            'metabolism': 'breakdown of the drug',
            'hepatic': 'liver',
            'renal': 'kidney',
            'cardiovascular': 'heart and blood vessels',
            'gastrointestinal': 'stomach and intestines'
        }
        
        for medical_term, simple_term in replacements.items():
            text = re.sub(rf'\b{medical_term}\b', simple_term, text, flags=re.IGNORECASE)
        
        return text

    def postprocess_summary(self, summary: str) -> str:
        """
        Clean and format the summary for patient readability
        """
        if not summary:
            return ""
        
        # Remove redundant phrases
        summary = re.sub(r'\b(?:the patient should|patients should|it is recommended that)\b', '', summary, flags=re.IGNORECASE)
        
        # Ensure proper capitalization
        summary = summary.strip()
        if summary and not summary[0].isupper():
            summary = summary[0].upper() + summary[1:]
        
        # Ensure proper ending
        if summary and not summary.endswith(('.', '!', '?')):
            summary += '.'
        
        # Remove duplicate periods
        summary = re.sub(r'\.+', '.', summary)
        
        return summary

    def summarize_with_transformer(self, text: str, max_length: int = 80) -> str:
        """
        Generate summary using transformer model
        """
        if not self.summarizer or not text:
            return ""
        
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            # Skip summarization if text is already short
            if len(processed_text.split()) <= 15:
                return self.postprocess_summary(processed_text)
            
            # Generate summary
            result = self.summarizer(
                processed_text,
                max_length=max_length,
                min_length=20,
                do_sample=False,
                early_stopping=True
            )
            
            summary = result[0]['summary_text'] if result else ""
            return self.postprocess_summary(summary)
            
        except Exception as e:
            logger.error(f"Transformer summarization failed: {e}")
            return ""

    def summarize_with_rules(self, text: str, max_words: int = 25) -> str:
        """
        Rule-based summarization as fallback
        """
        if not text:
            return ""
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        sentences = processed_text.split('.')
        
        # Extract key information
        key_phrases = []
        
        # Priority phrases (most important)
        priority_patterns = [
            r'(?:contraindicated|should not be used together)',
            r'(?:monitor|watch).*(?:closely|carefully)',
            r'(?:adjust|change).*dose',
            r'(?:risk|danger) of.*',
            r'may (?:cause|increase|decrease).*',
            r'(?:avoid|do not).*'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            for pattern in priority_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    key_phrases.append(sentence)
                    break
        
        # If no priority phrases found, take first meaningful sentence
        if not key_phrases:
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence.split()) >= 5:  # Meaningful length
                    key_phrases.append(sentence)
                    break
        
        # Combine and limit length
        if key_phrases:
            summary = '. '.join(key_phrases[:2])  # Max 2 sentences
            words = summary.split()
            if len(words) > max_words:
                summary = ' '.join(words[:max_words]) + '...'
        else:
            summary = processed_text[:100] + '...' if len(processed_text) > 100 else processed_text
        
        return self.postprocess_summary(summary)

    def summarize_advice(self, text: str, advice_type: str = 'general') -> str:
        """
        Main summarization function
        
        Args:
            text: Original advice text
            advice_type: Type of advice ('interaction', 'dosage', 'general')
            
        Returns:
            Patient-friendly summary
        """
        if not text or not text.strip():
            return "No specific advice available."
        
        try:
            # Try transformer summarization first
            summary = ""
            if self.summarizer:
                summary = self.summarize_with_transformer(text)
            
            # Fall back to rule-based if transformer fails
            if not summary or len(summary.strip()) < 10:
                summary = self.summarize_with_rules(text)
            
            # Ensure we have a meaningful summary
            if not summary or len(summary.strip()) < 5:
                summary = "Consult your doctor or pharmacist for specific advice."
            
            # Apply template if specified
            if advice_type in self.templates:
                summary = self.templates[advice_type].format(summary=summary)
            
            logger.info(f"Generated {advice_type} summary: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Advice summarization failed: {e}")
            return "Please consult your healthcare provider for detailed information."

def summarize_advice(text: str, advice_type: str = 'general') -> str:
    """
    Convenience function for advice summarization
    
    Args:
        text: Original advice text
        advice_type: Type of advice ('interaction', 'dosage', 'general')
        
    Returns:
        Patient-friendly summary
    """
    summarizer = MedicalSummarizer()
    return summarizer.summarize_advice(text, advice_type)

def summarize_multiple_interactions(interactions: list) -> list:
    """
    Generate summaries for multiple interactions efficiently
    """
    summarizer = MedicalSummarizer()
    
    for interaction in interactions:
        if 'description' in interaction or 'advice' in interaction:
            text = interaction.get('description') or interaction.get('advice', '')
            interaction['summary'] = summarizer.summarize_advice(text, 'interaction')
        else:
            interaction['summary'] = 'No specific advice available.'
    
    return interactions

def create_patient_friendly_report(interactions: list, dosage_info: list) -> str:
    """
    Create a comprehensive patient-friendly report
    """
    summarizer = MedicalSummarizer()
    
    report_sections = []
    
    # Interactions summary
    if interactions:
        report_sections.append("## Drug Interactions Found")
        for i, interaction in enumerate(interactions, 1):
            drug_pair = f"{interaction.get('drug_a', 'Drug')} and {interaction.get('drug_b', 'Drug')}"
            severity = interaction.get('severity', 'unknown')
            description = interaction.get('description', '')
            
            summary = summarizer.summarize_advice(description, 'interaction')
            
            report_sections.append(f"{i}. **{drug_pair}** (Severity: {severity.title()})")
            report_sections.append(f"   {summary}")
    else:
        report_sections.append("## Drug Interactions")
        report_sections.append("No significant drug interactions found.")
    
    # Dosage summary
    if dosage_info:
        report_sections.append("\n## Dosage Information")
        for dose_item in dosage_info:
            drug = dose_item.get('drug', 'Unknown drug')
            status = dose_item.get('dose_status', 'unknown')
            
            if status == 'valid':
                report_sections.append(f"✅ **{drug}**: Dosage appears appropriate")
            elif status == 'invalid':
                report_sections.append(f"⚠️ **{drug}**: Dosage may need adjustment")
                if dose_item.get('suggested_dose'):
                    report_sections.append(f"   Suggested: {dose_item['suggested_dose']}")
    
    return '\n'.join(report_sections)

def test_summarization():
    """
    Test summarization functionality
    """
    test_cases = [
        {
            'text': 'Concurrent use of warfarin and aspirin is contraindicated due to increased risk of hemorrhage. Patients should be monitored closely for signs of bleeding and INR should be checked frequently. Dose adjustments may be necessary.',
            'type': 'interaction'
        },
        {
            'text': 'The recommended dose for adults is 500mg twice daily. For elderly patients or those with renal impairment, dose reduction to 250mg twice daily is recommended.',
            'type': 'dosage'
        },
        {
            'text': 'This is a minor interaction with minimal clinical significance. No specific monitoring is required.',
            'type': 'interaction'
        }
    ]
    
    try:
        summarizer = MedicalSummarizer()
        
        for i, case in enumerate(test_cases, 1):
            original = case['text']
            summary = summarizer.summarize_advice(original, case['type'])
            
            print(f"Test {i}:")
            print(f"Original ({len(original)} chars): {original}")
            print(f"Summary ({len(summary)} chars): {summary}")
            print("-" * 70)
        
        print("✅ Summarization test completed")
        return True
        
    except Exception as e:
        print(f"❌ Summarization test failed: {e}")
        return False

if __name__ == "__main__":
    if test_summarization():
        print("✅ Summarization module is working")
    else:
        print("❌ Summarization module has issues")