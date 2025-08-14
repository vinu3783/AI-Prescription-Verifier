"""
AI Prescription Verifier - UI Components

This package contains UI-related files:
- Custom CSS themes and styling
- Lottie animation files
- UI utility functions
"""

__version__ = "1.0.0"

# UI configuration
THEME_CONFIG = {
    "primary_color": "#667eea",
    "secondary_color": "#764ba2", 
    "success_color": "#10b981",
    "warning_color": "#f59e0b",
    "error_color": "#ef4444",
    "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
}

# Animation file paths
ANIMATIONS = {
    "upload": "ui/animations/upload.json",
    "success": "ui/animations/success.json", 
    "warning": "ui/animations/warning.json"
}

__all__ = [
    "THEME_CONFIG",
    "ANIMATIONS"
]