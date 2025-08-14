"""
AI Prescription Verifier - Core Processing Modules

This package contains the core functionality for prescription analysis:
- OCR text extraction
- Medical named entity recognition
- Drug-drug interaction checking
- RxNorm API integration
- Severity classification
- Text summarization
- Dosage verification
- Utility functions
"""

__version__ = "1.0.0"
__author__ = "AI Prescription Verifier Team"

# Import main functions for easy access
from .ocr import extract_text
from .ner import extract_entities
from .rxcui import get_rxcui, get_brands, get_ingredient
from .interactions import find_interactions
from .severity import classify_severity
from .summarize import summarize_advice
from .dosage import check_dosage
from .utils import save_results_csv, generate_pdf_report

__all__ = [
    "extract_text",
    "extract_entities", 
    "get_rxcui",
    "get_brands",
    "get_ingredient",
    "find_interactions",
    "classify_severity",
    "summarize_advice",
    "check_dosage",
    "save_results_csv",
    "generate_pdf_report"
]