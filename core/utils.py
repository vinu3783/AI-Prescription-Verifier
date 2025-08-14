import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from fpdf import FPDF
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path: str) -> Path:
    """
    Ensure a directory exists, create if it doesn't
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def clean_text(text: str) -> str:
    """
    Clean and normalize text input
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep medical symbols
    text = re.sub(r'[^\w\s\-\.\,\(\)\[\]\/\%\+\=\:]', '', text)
    
    return text.strip()

def normalize_drug_name(drug_name: str) -> str:
    """
    Normalize drug names for consistent processing
    """
    if not drug_name:
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = drug_name.lower().strip()
    
    # Remove common prefixes/suffixes
    prefixes_suffixes = ['tab', 'tablet', 'cap', 'capsule', 'inj', 'injection', 'syrup', 'suspension']
    
    for term in prefixes_suffixes:
        normalized = re.sub(rf'\b{term}\b', '', normalized).strip()
    
    # Remove brand name indicators in parentheses
    normalized = re.sub(r'\([^)]*\)', '', normalized).strip()
    
    # Remove multiple spaces
    normalized = ' '.join(normalized.split())
    
    return normalized

def parse_dosage_units(dosage_string: str) -> Dict[str, Any]:
    """
    Parse dosage string to extract components
    """
    if not dosage_string:
        return {}
    
    result = {
        'original': dosage_string,
        'value': None,
        'unit': None,
        'form': None
    }
    
    # Extract numeric value and unit
    dose_pattern = r'(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units?|iu)\b'
    dose_match = re.search(dose_pattern, dosage_string, re.IGNORECASE)
    
    if dose_match:
        result['value'] = float(dose_match.group(1))
        result['unit'] = dose_match.group(2).lower()
    
    # Extract form (tablet, capsule, etc.)
    form_pattern = r'\b(tablet|cap|capsule|injection|syrup|suspension|drops?)\b'
    form_match = re.search(form_pattern, dosage_string, re.IGNORECASE)
    
    if form_match:
        result['form'] = form_match.group(1).lower()
    
    return result

def standardize_frequency(frequency: str) -> str:
    """
    Standardize frequency notation
    """
    if not frequency:
        return ""
    
    freq_map = {
        'bid': 'twice daily',
        'tid': 'three times daily', 
        'qid': 'four times daily',
        'qd': 'once daily',
        'qhs': 'at bedtime',
        'q4h': 'every 4 hours',
        'q6h': 'every 6 hours',
        'q8h': 'every 8 hours',
        'q12h': 'every 12 hours',
        'prn': 'as needed'
    }
    
    freq_lower = frequency.lower().strip()
    
    for abbrev, full in freq_map.items():
        if abbrev in freq_lower:
            return full
    
    return frequency

def format_drug_interaction(interaction: Dict) -> str:
    """
    Format drug interaction for display
    """
    drug_a = interaction.get('drug_a', 'Drug A')
    drug_b = interaction.get('drug_b', 'Drug B')
    severity = interaction.get('severity', 'unknown')
    description = interaction.get('description', 'No description available')
    
    severity_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(severity, '⚪')
    
    return f"{severity_emoji} {drug_a} ↔ {drug_b} ({severity.title()}): {description}"

def save_results_csv(analysis_results: Dict[str, Any]) -> str:
    """
    Save analysis results to CSV format
    """
    try:
        # Prepare data for CSV
        csv_data = []
        
        # Add basic information
        csv_data.append(['Analysis Date', analysis_results.get('timestamp', datetime.now().isoformat())])
        csv_data.append(['Patient Age', analysis_results.get('patient_age', 'Unknown')])
        csv_data.append([''])  # Empty row
        
        # Add drug entities
        csv_data.append(['Drugs Identified'])
        csv_data.append(['Drug Name', 'Dose', 'Route', 'Frequency', 'RxCUI'])
        
        entities = analysis_results.get('entities', [])
        for entity in entities:
            csv_data.append([
                entity.get('drug', ''),
                entity.get('dose', ''),
                entity.get('route', ''),
                entity.get('frequency', ''),
                entity.get('rxcui', '')
            ])
        
        csv_data.append([''])  # Empty row
        
        # Add interactions
        interactions = analysis_results.get('interactions', [])
        if interactions:
            csv_data.append(['Drug Interactions'])
            csv_data.append(['Drug A', 'Drug B', 'Severity', 'Description'])
            
            for interaction in interactions:
                csv_data.append([
                    interaction.get('drug_a', ''),
                    interaction.get('drug_b', ''),
                    interaction.get('severity', ''),
                    interaction.get('description', '')
                ])
        else:
            csv_data.append(['Drug Interactions'])
            csv_data.append(['No significant interactions found'])
        
        csv_data.append([''])  # Empty row
        
        # Add dosage results
        dosage_results = analysis_results.get('dosage_results', [])
        if dosage_results:
            csv_data.append(['Dosage Verification'])
            csv_data.append(['Drug', 'Mentioned Dose', 'Status', 'Suggested Dose', 'Considerations'])
            
            for result in dosage_results:
                considerations = '; '.join(result.get('considerations', []))
                csv_data.append([
                    result.get('drug', ''),
                    result.get('mentioned_dose', ''),
                    result.get('dose_status', ''),
                    result.get('suggested_dose', ''),
                    considerations
                ])
        
        # Convert to CSV string
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error saving CSV: {e}")
        return "Error generating CSV data"

def generate_pdf_report(analysis_results: Dict[str, Any]) -> bytes:
    """
    Generate PDF report from analysis results with proper bytes handling
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Use Arial font (most compatible)
        pdf.set_font('Arial', 'B', 16)
        
        # Title
        pdf.cell(0, 10, 'AI Prescription Verification Report', 0, 1, 'C')
        pdf.ln(5)
        
        # Basic information
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f"Analysis Date: {analysis_results.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))}", 0, 1)
        pdf.cell(0, 8, f"Patient Age: {analysis_results.get('patient_age', 'Unknown')}", 0, 1)
        pdf.ln(5)
        
        # Drugs identified
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Drugs Identified:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        entities = analysis_results.get('entities', [])
        for i, entity in enumerate(entities, 1):
            drug_info = f"{i}. {entity.get('drug', 'Unknown')}"
            if entity.get('dose'):
                drug_info += f" - {entity.get('dose')}"
            if entity.get('frequency'):
                drug_info += f" {entity.get('frequency')}"
            
            # Clean drug info for PDF
            drug_info = clean_text_for_pdf(drug_info)
            pdf.cell(0, 6, drug_info, 0, 1)
        
        pdf.ln(5)
        
        # Drug interactions
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Drug Interactions:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        interactions = analysis_results.get('interactions', [])
        if interactions:
            for i, interaction in enumerate(interactions, 1):
                severity = interaction.get('severity', 'unknown').upper()
                drug_a = clean_text_for_pdf(interaction.get('drug_a', 'Drug A'))
                drug_b = clean_text_for_pdf(interaction.get('drug_b', 'Drug B'))
                
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, f"{i}. {drug_a} with {drug_b} ({severity})", 0, 1)
                pdf.set_font('Arial', '', 10)
                
                # Word wrap for description
                description = clean_text_for_pdf(interaction.get('description', 'No description'))
                if len(description) > 80:
                    words = description.split()
                    line = ""
                    for word in words:
                        if len(line + word) > 80:
                            pdf.cell(0, 5, f"   {line}", 0, 1)
                            line = word + " "
                        else:
                            line += word + " "
                    if line:
                        pdf.cell(0, 5, f"   {line}", 0, 1)
                else:
                    pdf.cell(0, 5, f"   {description}", 0, 1)
                pdf.ln(2)
        else:
            pdf.cell(0, 6, 'No significant drug interactions found.', 0, 1)
        
        pdf.ln(5)
        
        # Dosage verification
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Dosage Verification:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        dosage_results = analysis_results.get('dosage_results', [])
        if dosage_results:
            for i, result in enumerate(dosage_results, 1):
                status = result.get('dose_status', 'unknown')
                
                # Use ASCII characters instead of Unicode symbols
                status_symbol = get_ascii_status_symbol(status)
                
                drug_name = clean_text_for_pdf(result.get('drug', 'Unknown'))
                dose = clean_text_for_pdf(result.get('mentioned_dose', 'No dose'))
                
                pdf.cell(0, 6, f"{i}. {drug_name} - {dose} {status_symbol}", 0, 1)
                
                if result.get('suggested_dose'):
                    pdf.set_font('Arial', 'I', 10)
                    suggested = clean_text_for_pdf(result.get('suggested_dose'))
                    pdf.cell(0, 5, f"   Suggested: {suggested}", 0, 1)
                    pdf.set_font('Arial', '', 11)
                
                if result.get('considerations'):
                    pdf.set_font('Arial', '', 10)
                    for consideration in result.get('considerations', []):
                        clean_consideration = clean_text_for_pdf(consideration)
                        pdf.cell(0, 5, f"   - {clean_consideration}", 0, 1)
                    pdf.set_font('Arial', '', 11)
                pdf.ln(2)
        
        # Footer
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, 'DISCLAIMER: This report is for educational purposes only and should not replace professional medical advice.', 0, 1, 'C')
        pdf.cell(0, 6, 'Always consult with healthcare professionals before making medication changes.', 0, 1, 'C')
        
        # Get PDF output and ensure it's proper bytes
        pdf_output = pdf.output(dest='S')
        
        # Convert to bytes regardless of what fpdf2 returns
        if isinstance(pdf_output, bytearray):
            return bytes(pdf_output)
        elif isinstance(pdf_output, str):
            return pdf_output.encode('latin-1')
        elif isinstance(pdf_output, bytes):
            return pdf_output
        else:
            # Fallback - try to convert to bytes
            return bytes(pdf_output)
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        # Return simple fallback PDF
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', '', 12)
            error_msg = clean_text_for_pdf(f'Error generating report: {str(e)}')
            pdf.cell(0, 10, error_msg, 0, 1)
            
            pdf_output = pdf.output(dest='S')
            
            # Handle the output type
            if isinstance(pdf_output, bytearray):
                return bytes(pdf_output)
            elif isinstance(pdf_output, str):
                return pdf_output.encode('latin-1')
            else:
                return bytes(pdf_output)
                
        except Exception as fallback_error:
            logger.error(f"Fallback PDF generation also failed: {fallback_error}")
            # Return minimal valid PDF as bytes
            minimal_pdf = b'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(PDF Generation Error) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000201 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
295
%%EOF'''
            return minimal_pdf

def clean_text_for_pdf(text: str) -> str:
    """
    Clean text for PDF generation by removing/replacing Unicode characters
    """
    if not text:
        return ""
    
    # Dictionary of Unicode characters to ASCII replacements
    unicode_replacements = {
        '✓': '[OK]',
        '✅': '[OK]',
        '❌': '[ERROR]',
        '⚠': '[WARNING]',
        '⚠️': '[WARNING]',
        '💊': '[DRUG]',
        '🔴': '[HIGH]',
        '🟡': '[MEDIUM]',
        '🟢': '[LOW]',
        '→': '->',
        '←': '<-',
        '↔': '<->',
        '•': '-',
        '·': '-',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '–': '-',
        '—': '-',
        '…': '...',
        '°': ' degrees',
        '±': '+/-',
        '×': 'x',
        '÷': '/',
        '≤': '<=',
        '≥': '>=',
        '≠': '!=',
        '≈': '~=',
        '∞': 'infinity',
        'α': 'alpha',
        'β': 'beta',
        'γ': 'gamma',
        'δ': 'delta',
        'ε': 'epsilon',
        'μ': 'micro',
        'π': 'pi',
        'σ': 'sigma',
        'Ω': 'omega'
    }
    
    # Replace Unicode characters
    for unicode_char, ascii_replacement in unicode_replacements.items():
        text = text.replace(unicode_char, ascii_replacement)
    
    # Remove any remaining non-ASCII characters
    text = ''.join(char if ord(char) < 128 else '?' for char in text)
    
    # Clean up multiple spaces
    text = ' '.join(text.split())
    
    return text

def get_ascii_status_symbol(status: str) -> str:
    """
    Get ASCII status symbol for dosage verification
    """
    status_map = {
        'appropriate': '[OK]',
        'valid': '[OK]',
        'too_low': '[LOW]',
        'too_high': '[HIGH]',
        'borderline': '[REVIEW]',
        'unknown': '[?]',
        'error': '[ERROR]'
    }
    return status_map.get(status, '[?]')

def save_uploaded_file(uploaded_file, upload_dir: str = "data/uploads/prescriptions") -> str:
    """
    Save uploaded file to disk and return path
    """
    try:
        # Ensure upload directory exists
        upload_path = ensure_directory_exists(upload_dir)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'bin'
        filename = f"prescription_{timestamp}.{file_extension}"
        
        file_path = upload_path / filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.read())
        
        logger.info(f"Saved uploaded file: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise

def load_json_config(config_path: str) -> Dict[str, Any]:
    """
    Load JSON configuration file
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}

def save_json_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to JSON file
    """
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {e}")
        return False

def validate_age(age_input: Any) -> Optional[int]:
    """
    Validate and convert age input
    """
    try:
        age = int(age_input)
        if 0 <= age <= 120:
            return age
        else:
            logger.warning(f"Age {age} is outside valid range (0-120)")
            return None
    except (ValueError, TypeError):
        logger.warning(f"Invalid age input: {age_input}")
        return None

def format_timestamp(timestamp: str = None) -> str:
    """
    Format timestamp for display
    """
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0.0

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def extract_drug_names_from_text(text: str) -> List[str]:
    """
    Extract potential drug names from text using simple heuristics
    """
    if not text:
        return []
    
    # Common drug name patterns
    drug_patterns = [
        r'\b[A-Z][a-z]+(?:cillin|mycin|prazole|olol|pine|zole|statin|fenac)\b',
        r'\b(?:aspirin|ibuprofen|acetaminophen|paracetamol|morphine|codeine)\b',
        r'\b[A-Z][a-z]{3,12}\b(?=\s+\d+\s*mg)'
    ]
    
    found_drugs = []
    for pattern in drug_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found_drugs.extend(matches)
    
    # Remove duplicates and return
    return list(set([drug.lower() for drug in found_drugs]))

def create_summary_stats(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create summary statistics from analysis results
    """
    entities = analysis_results.get('entities', [])
    interactions = analysis_results.get('interactions', [])
    dosage_results = analysis_results.get('dosage_results', [])
    
    # Count severities
    severity_counts = {'high': 0, 'medium': 0, 'low': 0}
    for interaction in interactions:
        severity = interaction.get('severity', 'medium')
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Count dosage issues
    dosage_issues = sum(1 for result in dosage_results 
                       if result.get('dose_status') not in ['appropriate', 'unknown'])
    
    return {
        'total_drugs': len(entities),
        'total_interactions': len(interactions),
        'high_severity_interactions': severity_counts['high'],
        'medium_severity_interactions': severity_counts['medium'],
        'low_severity_interactions': severity_counts['low'],
        'dosage_issues': dosage_issues,
        'drugs_with_rxcui': sum(1 for entity in entities if entity.get('rxcui')),
        'analysis_timestamp': analysis_results.get('timestamp', datetime.now().isoformat())
    }

def test_utils():
    """
    Test utility functions
    """
    try:
        # Test text cleaning
        test_text = "  Test   drug  name  123  "
        cleaned = clean_text(test_text)
        assert cleaned == "Test drug name 123"
        
        # Test drug name normalization
        drug_name = "Paracetamol 500mg Tablet"
        normalized = normalize_drug_name(drug_name)
        assert "paracetamol" in normalized
        
        # Test dosage parsing
        dosage = "500mg tablet"
        parsed = parse_dosage_units(dosage)
        assert parsed['value'] == 500.0
        assert parsed['unit'] == 'mg'
        
        print("✅ Utility functions test passed")
        return True
        
    except Exception as e:
        print(f"❌ Utility functions test failed: {e}")
        return False

if __name__ == "__main__":
    if test_utils():
        print("✅ Utils module is working correctly")
    else:
        print("❌ Utils module has issues")