import streamlit as st
import os
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components

# Import core modules
from core.ocr import extract_text
from core.ner import extract_entities
from core.rxcui import get_rxcui, get_brands, get_ingredient
from core.interactions import find_interactions
from core.severity import classify_severity
from core.summarize import summarize_advice
from core.dosage import check_dosage
from core.utils import save_results_csv, generate_pdf_report

# Import NEW modules with fallback handling
try:
    from core.mistral_api import TherapyDoctorBot, get_therapy_response
    NEW_FEATURES_AVAILABLE = True
except ImportError:
    NEW_FEATURES_AVAILABLE = False
    class TherapyDoctorBot:
        def __init__(self):
            self.model = None
    def get_therapy_response(message, context=None):
        return "Therapy Doctor not available. Please run: pip install google-generativeai"

try:
    from core.reminder_system import (
        SmartReminderSystem, 
        create_reminders_from_prescription,
        get_current_notifications,
        mark_dose_taken,
        mark_water_drunk
    )
    REMINDERS_AVAILABLE = True
except ImportError:
    REMINDERS_AVAILABLE = False
    class SmartReminderSystem:
        def __init__(self):
            self.medication_reminders = {}
    def create_reminders_from_prescription(entities):
        return []
    def get_current_notifications():
        return []
    def mark_dose_taken(reminder_id):
        return True
    def mark_water_drunk(reminder_id, glasses=1):
        return True

# Page configuration
st.set_page_config(
    page_title="AI Prescription Verifier",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
@st.cache_data
def load_css():
    css_paths = ["ui/theme.css", "ui/enhanced_theme.css"]
    combined_css = ""
    
    for css_path in css_paths:
        if Path(css_path).exists():
            with open(css_path) as f:
                combined_css += f.read() + "\n"
    
    # Fallback CSS if files don't exist
    if not combined_css:
        combined_css = """
        .main { font-family: 'Arial', sans-serif; }
        .hero-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem; border-radius: 10px; color: white; text-align: center;
        }
        .feature-card {
            background: white; padding: 1.5rem; border-radius: 10px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 1rem 0;
        }
        """
    
    return combined_css

# Load Lottie animations
@st.cache_data
def load_lottie(file_path):
    try:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = 0

# Initialize new features if available
if REMINDERS_AVAILABLE and 'reminder_system' not in st.session_state:
    st.session_state.reminder_system = SmartReminderSystem()
if NEW_FEATURES_AVAILABLE and 'therapy_bot' not in st.session_state:
    st.session_state.therapy_bot = TherapyDoctorBot()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def main():
    # Apply custom CSS
    st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)
    
    # Add floating particles background
    st.markdown("""
    <div class="particles-container">
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <div class="pulse-icon">💊</div>
            <h1 class="sidebar-title">AI Prescription Verifier</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Dynamic navigation based on available features
        nav_options = ["🏠 Home", "🔍 Analyze", "⚠️ Interactions", "💊 Dosage & Alternatives"]
        
        if REMINDERS_AVAILABLE:
            nav_options.append("⏰ Smart Reminders")
        
        if NEW_FEATURES_AVAILABLE:
            nav_options.append("🧠 Therapy Doctor")
        
        nav_options.append("📄 Exports")
        
        page = st.selectbox("Navigate", nav_options)
        
        # Show notifications if reminders available
        if REMINDERS_AVAILABLE:
            show_sidebar_notifications()
        
        st.markdown("---")
        st.markdown("### ⚠️ Medical Disclaimer")
        st.caption("This tool is for educational purposes only and is not a medical device. Always consult healthcare professionals.")

    # Page routing
    if page == "🏠 Home":
        show_home_page()
    elif page == "🔍 Analyze":
        show_analyze_page()
    elif page == "⚠️ Interactions":
        show_interactions_page()
    elif page == "💊 Dosage & Alternatives":
        show_dosage_page()
    elif page == "⏰ Smart Reminders" and REMINDERS_AVAILABLE:
        show_reminders_page()
    elif page == "🧠 Therapy Doctor" and NEW_FEATURES_AVAILABLE:
        show_therapy_page()
    elif page == "📄 Exports":
        show_exports_page()

def show_sidebar_notifications():
    """Show reminder notifications in sidebar"""
    try:
        notifications = get_current_notifications()
        
        if notifications:
            st.markdown("### 🔔 Current Reminders")
            
            for notification in notifications[:3]:  # Show top 3
                icon = notification.get('icon', '⚠️')
                title = notification.get('title', '')
                
                if notification['type'] == 'medication':
                    if st.button(f"{icon} {title}", key=f"sidebar_{notification['id']}"):
                        mark_dose_taken(notification['id'])
                        st.rerun()
                elif notification['type'] == 'water':
                    if st.button(f"{icon} Drink Water", key=f"sidebar_{notification['id']}"):
                        mark_water_drunk(notification['id'])
                        st.rerun()
            
            if len(notifications) > 3:
                st.caption(f"+ {len(notifications) - 3} more reminders")
    except Exception as e:
        st.caption(f"Reminders: {str(e)}")

def show_home_page():
    # Enhanced Hero section with gradient animation
    st.markdown("""
    <div class="hero-section-enhanced">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <h1 class="hero-title glitch" data-text="AI Prescription Verifier">
                <span class="magic-text">AI</span> Prescription Verifier
            </h1>
            <p class="hero-subtitle typewriter">Intelligent prescription analysis powered by cutting-edge AI</p>
            <div class="hero-badges">
                <span class="badge badge-success">✨ Advanced OCR</span>
                <span class="badge badge-warning">🔬 Drug Analysis</span>
                <span class="badge badge-info">🛡️ Safety First</span>
            </div>
        </div>
        <div class="floating-pills">
            <span class="pill pill-1">💊</span>
            <span class="pill pill-2">💉</span>
            <span class="pill pill-3">🩺</span>
            <span class="pill pill-4">⚕️</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        upload_animation = load_lottie("ui/animations/upload.json")
        if upload_animation:
            st_lottie(upload_animation, height=300, key="hero_animation")
    
    # Features overview with enhanced cards
    st.markdown("<h2 class='section-title gradient-text'>✨ Powerful Features</h2>", unsafe_allow_html=True)
    
    # Determine number of columns based on available features
    num_features = 3
    if REMINDERS_AVAILABLE:
        num_features += 1
    if NEW_FEATURES_AVAILABLE:
        num_features += 1
    
    if num_features <= 3:
        cols = st.columns(3)
    else:
        cols = st.columns(min(num_features, 5))
    
    feature_idx = 0
    
    with cols[feature_idx]:
        st.markdown("""
        <div class="feature-card-enhanced card-hover-1">
            <div class="card-glow"></div>
            <div class="card-icon">🔍</div>
            <h3>Smart OCR</h3>
            <p>Extract text from prescription images and PDFs with military-grade accuracy</p>
            <div class="card-shimmer"></div>
        </div>
        """, unsafe_allow_html=True)
    feature_idx += 1
    
    with cols[feature_idx % len(cols)]:
        st.markdown("""
        <div class="feature-card-enhanced card-hover-2">
            <div class="card-glow"></div>
            <div class="card-icon">⚠️</div>
            <h3>Drug Interaction</h3>
            <p>Real-time detection of dangerous drug-drug interactions with instant alerts</p>
            <div class="card-shimmer"></div>
        </div>
        """, unsafe_allow_html=True)
    feature_idx += 1
    
    with cols[feature_idx % len(cols)]:
        st.markdown("""
        <div class="feature-card-enhanced card-hover-3">
            <div class="card-glow"></div>
            <div class="card-icon">💊</div>
            <h3>Dosage Verification</h3>
            <p>AI-powered age-appropriate dosage verification and safer alternatives</p>
            <div class="card-shimmer"></div>
        </div>
        """, unsafe_allow_html=True)
    feature_idx += 1
    
    if REMINDERS_AVAILABLE:
        with cols[feature_idx % len(cols)]:
            st.markdown("""
            <div class="feature-card-enhanced card-hover-4">
                <div class="card-glow"></div>
                <div class="card-icon">⏰</div>
                <h3>Smart Reminders</h3>
                <p>Intelligent medication tracking with water intake reminders</p>
                <div class="card-shimmer"></div>
            </div>
            """, unsafe_allow_html=True)
        feature_idx += 1
    
    if NEW_FEATURES_AVAILABLE:
        with cols[feature_idx % len(cols)]:
            st.markdown("""
            <div class="feature-card-enhanced card-hover-5">
                <div class="card-glow"></div>
                <div class="card-icon">🧠</div>
                <h3>Therapy Doctor</h3>
                <p>24/7 AI mental health companion and medical guidance</p>
                <div class="card-shimmer"></div>
            </div>
            """, unsafe_allow_html=True)
    
    # Show stats if reminders are available
    if REMINDERS_AVAILABLE:
        try:
            stats = st.session_state.reminder_system.get_adherence_stats()
            if stats['total_medications'] > 0:
                st.markdown("<h2 class='section-title gradient-text'>📊 Your Health Dashboard</h2>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""
                    <div class="stat-card stat-card-1">
                        <div class="stat-value">{stats['active_medications']}</div>
                        <div class="stat-label">Active Medications</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="stat-card stat-card-2">
                        <div class="stat-value">{stats['adherence_rate']:.1f}%</div>
                        <div class="stat-label">Adherence Rate</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="stat-card stat-card-3">
                        <div class="stat-value">{stats['streak_days']:.0f}</div>
                        <div class="stat-label">Day Streak</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="stat-card stat-card-4">
                        <div class="stat-value">{stats['total_doses_taken']}</div>
                        <div class="stat-label">Doses Taken</div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception:
            pass
    
    # CTA Buttons with enhanced styling
    st.markdown("<br>", unsafe_allow_html=True)
    
    if NEW_FEATURES_AVAILABLE and REMINDERS_AVAILABLE:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="cta-button-wrapper">
                <div class="cta-glow"></div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Analyze Prescription", type="primary", use_container_width=True):
                st.switch_page("🔍 Analyze")
        with col2:
            if st.button("⏰ Set Reminders", use_container_width=True):
                st.switch_page("⏰ Smart Reminders")
        with col3:
            if st.button("🧠 Talk to Dr. Sarah", use_container_width=True):
                st.switch_page("🧠 Therapy Doctor")
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Start Analysis", type="primary", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📚 Learn More", use_container_width=True):
                st.info("Upload a prescription to get started with AI-powered analysis!")
    
    # Creators Section with Levitating Effect
    st.markdown("""
    <div class="creators-section">
        <h2 class="creators-title">✨ Created with ❤️ by TEAM ELYTRA </h2>
        <div class="creators-container">
            <div class="creator-card levitate-1">
                <div class="creator-avatar">👨‍💻</div>
                <h3 class="creator-name neon-text">Vinayaka GC</h3>
                <p class="creator-role">BRAIN STROMER</p>
                <div class="creator-glow"></div>
            </div>
            <div class="creator-card levitate-2">
                <div class="creator-avatar">👩‍💻</div>
                <h3 class="creator-name neon-text">Inchara PM</h3>
                <p class="creator-role">CREATIVE CREATURE</p>
                <div class="creator-glow"></div>
            </div>
            <div class="creator-card levitate-3">
                <div class="creator-avatar">👩‍🔬</div>
                <h3 class="creator-name neon-text">Pragya RK</h3>
                <p class="creator-role">HIDDEN HIVE BULIDER</p>
                <div class="creator-glow"></div>
            </div>
        </div>
        <div class="creators-tagline">Building the future of healthcare, one prescription at a time 🚀</div>
    </div>
    """, unsafe_allow_html=True)

def show_analyze_page():
    st.markdown("<h1 class='page-title gradient-text'>🔍 Prescription Analysis</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="upload-section-enhanced">
            <h3 class="upload-title">Upload Prescription</h3>
        </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choose a prescription image or PDF",
            type=['png', 'jpg', 'jpeg', 'pdf'],
            help="Upload a clear image or PDF of the prescription"
        )
    
    with col2:
        st.markdown("""
        <div class="patient-info-card">
            <h3>Patient Information</h3>
        </div>
        """, unsafe_allow_html=True)
        age = st.number_input("Patient Age", min_value=0, max_value=120, value=30)
        
    if uploaded_file and st.button("🔍 Analyze Prescription", type="primary"):
        analyze_prescription(uploaded_file, age)

def analyze_prescription(uploaded_file, age):
    """Analyze prescription function"""
    # Progress container
    progress_container = st.empty()
    
    with progress_container.container():
        # Step indicator
        steps = ["OCR", "NER", "RxNorm", "Interactions", "Dosage", "Summary"]
        
        for i, step in enumerate(steps):
            with st.status(f"Step {i+1}: {step}", expanded=True) as status:
                
                if step == "OCR":
                    st.write("Extracting text from prescription...")
                    try:
                        file_bytes = uploaded_file.read()
                        file_type = uploaded_file.type
                        extracted_text = extract_text(file_bytes, file_type)
                        
                        # Check if we're in demo mode
                        if "PRESCRIPTION" in extracted_text and "Patient:" in extracted_text and len(extracted_text) < 1000:
                            st.info("ℹ️ Demo Mode: Using sample prescription text")
                            st.success(f"Sample prescription loaded for demonstration")
                        else:
                            st.success(f"Extracted {len(extracted_text)} characters")
                            
                            # Show debug info if text seems short
                            if len(extracted_text.strip()) < 50:
                                with st.expander("🔍 OCR Debug Info"):
                                    st.warning("OCR extracted very little text. This might indicate:")
                                    st.write("• Image quality issues (blurry, low contrast)")
                                    st.write("• Handwritten text (OCR works best with typed text)")
                                    st.write("• Unusual formatting or image orientation issues")
                                    st.code(extracted_text)
                                    st.info("💡 Try uploading a clear, typed prescription")
                            
                            # Show preview of extracted text
                            if len(extracted_text.strip()) > 20:
                                with st.expander("📄 Extracted Text Preview"):
                                    preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
                                    st.text(preview)
                        
                        status.update(label=f"✅ Step {i+1}: OCR Complete", state="complete")
                    except Exception as e:
                        st.error(f"OCR failed: {e}")
                        return
                
                elif step == "NER":
                    st.write("Identifying drugs and dosages...")
                    try:
                        entities = extract_entities(extracted_text)
                        st.success(f"Found {len(entities)} drug entities")
                        
                        if len(entities) == 0:
                            with st.expander("🔍 NER Debug Info"):
                                st.warning("No drug entities were identified. This might be because:")
                                st.write("• The prescription format is unusual")
                                st.write("• Drug names are not recognized")
                                st.write("• OCR text quality is poor")
                                st.info("💡 Try a prescription with clear drug names and dosages")
                        else:
                            with st.expander("💊 Identified Entities"):
                                for entity in entities:
                                    drug = entity.get('drug', 'Unknown')
                                    dose = entity.get('dose', 'No dose')
                                    freq = entity.get('frequency', 'No frequency')
                                    st.write(f"• **{drug}** - {dose} - {freq}")
                        
                        status.update(label=f"✅ Step {i+1}: NER Complete", state="complete")
                    except Exception as e:
                        st.error(f"NER failed: {e}")
                        return
                
                elif step == "RxNorm":
                    st.write("Mapping drugs to RxNorm codes...")
                    try:
                        for entity in entities:
                            rxcui = get_rxcui(entity.get('drug', ''))
                            entity['rxcui'] = rxcui
                        valid_entities = [e for e in entities if e.get('rxcui')]
                        st.success(f"Mapped {len(valid_entities)} drugs to RxNorm")
                        status.update(label=f"✅ Step {i+1}: RxNorm Complete", state="complete")
                    except Exception as e:
                        st.error(f"RxNorm mapping failed: {e}")
                        return
                
                elif step == "Interactions":
                    st.write("Checking drug-drug interactions...")
                    try:
                        rxcuis = [e['rxcui'] for e in valid_entities if e.get('rxcui')]
                        interactions = find_interactions(rxcuis)
                        st.success(f"Found {len(interactions)} potential interactions")
                        status.update(label=f"✅ Step {i+1}: Interactions Complete", state="complete")
                    except Exception as e:
                        st.error(f"Interaction check failed: {e}")
                        return
                
                elif step == "Dosage":
                    st.write("Verifying dosages...")
                    try:
                        dosage_results = check_dosage(valid_entities, age)
                        st.success(f"Analyzed dosages for {len(dosage_results)} drugs")
                        status.update(label=f"✅ Step {i+1}: Dosage Complete", state="complete")
                    except Exception as e:
                        st.error(f"Dosage check failed: {e}")
                        return
                
                elif step == "Summary":
                    st.write("Generating summary...")
                    try:
                        # Store results in session state
                        st.session_state.analysis_results = {
                            'extracted_text': extracted_text,
                            'entities': valid_entities,
                            'interactions': interactions,
                            'dosage_results': dosage_results,
                            'patient_age': age,
                            'timestamp': datetime.now().isoformat()
                        }
                        st.success("Analysis complete!")
                        status.update(label=f"✅ Step {i+1}: Summary Complete", state="complete")
                    except Exception as e:
                        st.error(f"Summary generation failed: {e}")
                        return
    
    # Clear progress and show results
    progress_container.empty()
    show_analysis_results()

def show_analysis_results():
    """Show analysis results"""
    if not st.session_state.analysis_results:
        st.warning("No analysis results available. Please run an analysis first.")
        return
    
    results = st.session_state.analysis_results
    
    # Success animation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        success_animation = load_lottie("ui/animations/success.json")
        if success_animation:
            st_lottie(success_animation, height=200, key="success_animation")
    
    # Summary banner
    num_interactions = len(results.get('interactions', []))
    high_severity = len([i for i in results.get('interactions', []) if i.get('severity') == 'high'])
    
    if high_severity > 0:
        st.markdown("""
        <div class="alert-banner alert-danger">
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
                <strong>{} interactions found</strong> • {} high severity
            </div>
        </div>
        """.format(num_interactions, high_severity), unsafe_allow_html=True)
    elif num_interactions > 0:
        st.markdown("""
        <div class="alert-banner alert-warning">
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
                <strong>{} interactions found</strong> • Low to medium severity
            </div>
        </div>
        """.format(num_interactions), unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-banner alert-success">
            <div class="alert-icon">✅</div>
            <div class="alert-content">
                <strong>No critical drug interactions detected</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.balloons()
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Drugs Identified", len(results.get('entities', [])))
    
    with col2:
        st.metric("Interactions Found", num_interactions)
    
    with col3:
        st.metric("High Severity", high_severity)
    
    with col4:
        st.metric("Patient Age", results.get('patient_age', 'Unknown'))
    
    # Offer to create reminders if available
    if REMINDERS_AVAILABLE and results.get('entities'):
        st.markdown("---")
        st.markdown("### ⏰ Create Medication Reminders")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Want to set up automatic reminders for these medications?")
        with col2:
            if st.button("✅ Create Reminders"):
                entities = st.session_state.analysis_results['entities']
                created = create_reminders_from_prescription(entities)
                st.success(f"Created {len(created)} medication reminders!")
                st.balloons()

def show_interactions_page():
    """Show drug interactions page"""
    st.markdown("<h1 class='page-title gradient-text'>⚠️ Drug Interactions</h1>", unsafe_allow_html=True)
    
    if not st.session_state.analysis_results:
        st.info("No analysis results available. Please analyze a prescription first.")
        return
    
    interactions = st.session_state.analysis_results.get('interactions', [])
    
    if not interactions:
        st.success("✅ No drug interactions detected!")
        return
    
    # Summary banner
    num_interactions = len(interactions)
    high_severity = len([i for i in interactions if i.get('severity') == 'high'])
    
    if high_severity > 0:
        st.error(f"⚠️ {num_interactions} interactions found • {high_severity} high severity")
    elif num_interactions > 0:
        st.warning(f"⚠️ {num_interactions} interactions found • Low to medium severity")
    
    for i, interaction in enumerate(interactions):
        severity = interaction.get('severity', 'medium')
        
        # Severity color mapping
        color_map = {
            'low': 'green',
            'medium': 'orange', 
            'high': 'red'
        }
        
        with st.expander(f"🔄 {interaction.get('drug_a', 'Drug A')} ↔ {interaction.get('drug_b', 'Drug B')}", expanded=(severity=='high')):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Interaction:** {interaction.get('description', 'No description available')}")
                
                if interaction.get('advice'):
                    try:
                        summary = summarize_advice(interaction['advice'])
                        st.markdown(f"**Recommendation:** {summary}")
                    except Exception:
                        st.markdown(f"**Recommendation:** {interaction['advice']}")
            
            with col2:
                st.markdown(f"<span style='color: {color_map.get(severity, 'gray')}; font-weight: bold;'>🚨 {severity.upper()}</span>", unsafe_allow_html=True)

def show_dosage_page():
    """Show dosage and alternatives page"""
    st.markdown("<h1 class='page-title gradient-text'>💊 Dosage & Alternatives</h1>", unsafe_allow_html=True)
    
    if not st.session_state.analysis_results:
        st.info("No analysis results available. Please analyze a prescription first.")
        return
    
    dosage_results = st.session_state.analysis_results.get('dosage_results', [])
    
    if not dosage_results:
        st.info("No dosage verification results available.")
        return
    
    for result in dosage_results:
        with st.container():
            st.markdown(f"### {result.get('drug', 'Unknown Drug')}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Current Prescription:**")
                st.info(f"**Dose:** {result.get('mentioned_dose', 'N/A')}")
                st.info(f"**Frequency:** {result.get('frequency', 'N/A')}")
                
                dose_status = result.get('dose_status', 'unknown')
                if dose_status in ['invalid', 'too_high', 'too_low']:
                    st.warning("⚠️ Dosage may need adjustment")
                elif dose_status in ['valid', 'appropriate']:
                    st.success("✅ Dosage is appropriate")
                elif dose_status == 'borderline':
                    st.warning("⚠️ Dosage is borderline - monitor closely")
                else:
                    st.info(f"**Status:** {dose_status}")
            
            with col2:
                st.markdown("**Alternatives & Suggestions:**")
                
                if result.get('suggested_dose'):
                    st.success(f"**Suggested:** {result['suggested_dose']}")
                
                if result.get('alternatives'):
                    st.markdown("**Brand alternatives:**")
                    for alt in result['alternatives'][:3]:  # Show top 3
                        st.markdown(f"• {alt}")
                
                if result.get('considerations'):
                    st.markdown("**Considerations:**")
                    for consideration in result['considerations']:
                        st.markdown(f"• {consideration}")
            
            st.markdown("---")

def show_exports_page():
    """Show exports page"""
    st.markdown("<h1 class='page-title gradient-text'>📄 Export Results</h1>", unsafe_allow_html=True)
    
    if not st.session_state.analysis_results:
        st.info("No analysis results available. Please analyze a prescription first.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 CSV Export")
        st.markdown("Download detailed analysis results in CSV format")
        
        if st.button("📥 Download CSV", type="primary"):
            try:
                csv_data = save_results_csv(st.session_state.analysis_results)
                st.download_button(
                    label="💾 Save CSV File",
                    data=csv_data,
                    file_name=f"prescription_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Error generating CSV: {e}")
    
    with col2:
        st.markdown("### 📋 PDF Report")
        st.markdown("Generate a comprehensive PDF report")
        
        if st.button("📄 Generate PDF", type="primary"):
            with st.spinner("Generating PDF report..."):
                try:
                    pdf_data = generate_pdf_report(st.session_state.analysis_results)
                    st.download_button(
                        label="💾 Save PDF Report",
                        data=pdf_data,
                        file_name=f"prescription_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
                    st.success("PDF report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

# NEW FEATURES - Only show if modules are available

def show_reminders_page():
    """NEW: Smart Reminders Page"""
    if not REMINDERS_AVAILABLE:
        st.error("Smart Reminders not available. Please install required dependencies.")
        return
        
    st.markdown("<h1 class='page-title gradient-text'>⏰ Smart Reminders</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Current Reminders", "💊 Medications", "💧 Water Intake", "📊 Analytics"])
    
    with tab1:
        show_current_reminders()
    
    with tab2:
        show_medication_reminders()
    
    with tab3:
        show_water_reminders()
    
    with tab4:
        show_reminder_analytics()

def show_current_reminders():
    """Show current due reminders"""
    try:
        notifications = get_current_notifications()
        
        if not notifications:
            st.success("🎉 All caught up! No pending reminders.")
            return
        
        st.markdown(f"### You have {len(notifications)} pending reminders:")
        
        for notification in notifications:
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 2])
                
                with col1:
                    st.markdown(f"## {notification.get('icon', '⚠️')}")
                
                with col2:
                    st.markdown(f"**{notification.get('title', 'Reminder')}**")
                    st.markdown(notification.get('message', ''))
                
                with col3:
                    if notification.get('type') == 'medication':
                        if st.button("✅ Taken", key=f"take_{notification['id']}"):
                            mark_dose_taken(notification['id'])
                            st.success("Medication marked as taken!")
                            st.rerun()
                        
                        if st.button("⏰ Snooze", key=f"snooze_{notification['id']}"):
                            st.info("Reminder snoozed for 10 minutes")
                    
                    elif notification.get('type') == 'water':
                        if st.button("💧 Drank", key=f"water_{notification['id']}"):
                            mark_water_drunk(notification['id'])
                            st.success("Water intake recorded!")
                            st.rerun()
                
                st.markdown("---")
    except Exception as e:
        st.error(f"Error loading reminders: {e}")

def show_medication_reminders():
    """Medication reminders management"""
    st.markdown("### 💊 Medication Reminders")
    
    # Create from prescription button
    if st.session_state.analysis_results:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### Add medications from your latest prescription analysis")
        with col2:
            if st.button("📋 Use Last Analysis"):
                entities = st.session_state.analysis_results.get('entities', [])
                if entities:
                    created = create_reminders_from_prescription(entities)
                    st.success(f"Created {len(created)} medication reminders!")
                    st.rerun()
    
    # Show existing reminders
    try:
        reminder_system = st.session_state.reminder_system
        if hasattr(reminder_system, 'medication_reminders') and reminder_system.medication_reminders:
            st.markdown("#### Current Medication Reminders")
            
            for reminder_id, reminder in reminder_system.medication_reminders.items():
                if not hasattr(reminder, 'is_active') or reminder.is_active:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{getattr(reminder, 'drug_name', 'Unknown')}**")
                            dosage = getattr(reminder, 'dosage', 'Unknown dosage')
                            frequency = getattr(reminder, 'frequency', 'Unknown frequency')
                            st.caption(f"{dosage} • {frequency}")
                        
                        with col2:
                            st.markdown("**Times:**")
                            times = getattr(reminder, 'times', [])
                            st.caption(", ".join(times) if times else "No times set")
                        
                        with col3:
                            st.markdown("**Streak:**")
                            streak = getattr(reminder, 'streak_days', 0)
                            st.caption(f"{streak} days")
                        
                        with col4:
                            if st.button("🗑️", key=f"delete_{reminder_id}"):
                                if hasattr(reminder, 'is_active'):
                                    reminder.is_active = False
                                    reminder_system.save_data()
                                st.rerun()
                        
                        st.markdown("---")
        else:
            st.info("No medication reminders set up yet. Analyze a prescription to get started!")
    except Exception as e:
        st.error(f"Error loading medication reminders: {e}")

def show_water_reminders():
    """Water intake reminders"""
    st.markdown("### 💧 Water Intake Reminders")
    
    try:
        reminder_system = st.session_state.reminder_system
        
        # Water reminder settings
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Daily Water Goal")
            target_glasses = st.number_input("Target glasses per day", min_value=1, max_value=20, value=8)
            glass_size = st.number_input("Glass size (ml)", min_value=100, max_value=500, value=250)
            
            st.info(f"Daily target: {target_glasses * glass_size}ml ({target_glasses} glasses)")
        
        with col2:
            st.markdown("#### Reminder Settings")
            interval = st.number_input("Reminder interval (minutes)", min_value=30, max_value=300, value=120)
            
            if st.button("💧 Create Water Reminder"):
                water_reminder = reminder_system.create_water_reminder(target_glasses, interval)
                st.success("Water reminder created!")
                st.rerun()
        
        # Today's water intake
        if hasattr(reminder_system, 'water_reminders') and reminder_system.water_reminders:
            water_reminders = list(reminder_system.water_reminders.values())
            if water_reminders:
                reminder = water_reminders[0]  # Use first active reminder
                
                st.markdown("#### Today's Progress")
                
                current_intake = getattr(reminder, 'current_intake', 0)
                target = getattr(reminder, 'target_glasses', 8)
                progress = min(current_intake / target, 1.0) if target > 0 else 0
                
                st.progress(progress)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Consumed", f"{current_intake} glasses")
                with col2:
                    st.metric("Remaining", f"{max(0, target - current_intake)} glasses")
                with col3:
                    if st.button("💧 Add Glass"):
                        mark_water_drunk(getattr(reminder, 'id', 'water_1'))
                        st.rerun()
    
    except Exception as e:
        st.error(f"Error with water reminders: {e}")

def show_reminder_analytics():
    """Reminder analytics and insights"""
    st.markdown("### 📊 Analytics & Insights")
    
    try:
        reminder_system = st.session_state.reminder_system
        stats = reminder_system.get_adherence_stats()
        
        # Weekly report
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Medication Adherence")
            
            adherence_rate = stats.get('adherence_rate', 0)
            st.metric("Adherence Rate", f"{adherence_rate:.1f}%")
            st.metric("Current Streak", f"{stats.get('streak_days', 0):.0f} days")
            st.metric("Doses Taken", f"{stats.get('total_doses_taken', 0)}")
            
            # Recommendations
            if adherence_rate < 80:
                st.warning("💡 **Tip:** Try setting more frequent reminder notifications")
            elif adherence_rate >= 95:
                st.success("🎉 **Excellent!** You're doing great with your medications!")
        
        with col2:
            st.markdown("#### Weekly Summary")
            
            weekly_report = reminder_system.get_weekly_report()
            
            st.json({
                "Week Ending": weekly_report.get('week_ending', 'Unknown'),
                "Doses Taken": weekly_report.get('doses_taken', 0),
                "Current Streak": f"{weekly_report.get('current_streak', 0):.0f} days",
                "Active Medications": stats.get('active_medications', 0)
            })
            
            # Export report button
            if st.button("📄 Export Weekly Report"):
                try:
                    report_df = pd.DataFrame([weekly_report])
                    csv = report_df.to_csv(index=False)
                    st.download_button(
                        "💾 Download CSV",
                        csv,
                        f"adherence_report_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
                except Exception as e:
                    st.error(f"Error generating report: {e}")
    
    except Exception as e:
        st.error(f"Error loading analytics: {e}")

def show_therapy_page():
    """NEW: Therapy Doctor Chatbot Page"""
    if not NEW_FEATURES_AVAILABLE:
        st.error("Therapy Doctor not available. Please install google-generativeai: pip install google-generativeai")
        return
        
    st.markdown("<h1 class='page-title gradient-text'>🧠 Dr. Sarah - Therapy Doctor</h1>", unsafe_allow_html=True)
    st.markdown("*Your AI companion for mental health support and medical guidance*")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 💡 I can help with:")
        st.markdown("""
        - 🧘 **Stress & Anxiety** management
        - 😔 **Mood** support and coping strategies  
        - 💊 **Medication** questions and guidance
        - 🏥 **Health** advice and explanations
        - 💤 **Sleep** and lifestyle recommendations
        - 🆘 **Crisis** support and resources
        """)
        
        # Quick action buttons
        st.markdown("#### Quick Help:")
        if st.button("😰 I'm feeling anxious"):
            quick_message = "I'm feeling anxious and need some help managing it."
            st.session_state.chat_history.append({"role": "user", "content": quick_message})
            st.rerun()
            
        if st.button("💊 Medication question"):
            quick_message = "I have a question about my medications."
            st.session_state.chat_history.append({"role": "user", "content": quick_message})
            st.rerun()
            
        if st.button("😴 Sleep problems"):
            quick_message = "I'm having trouble sleeping lately."
            st.session_state.chat_history.append({"role": "user", "content": quick_message})
            st.rerun()
    
    with col1:
        st.markdown("### 💬 Chat with Dr. Sarah")
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"**You:** {message['content']}")
                else:
                    st.markdown(f"**Dr. Sarah:** {message['content']}")
                st.markdown("---")
        
        # Chat input
        user_input = st.text_area(
            "Ask Dr. Sarah anything...", 
            placeholder="How are you feeling today? What's on your mind?",
            key="therapy_input",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            send_button = st.button("Send 💬", type="primary")
        
        if send_button and user_input:
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Prepare context from current analysis
            context = {}
            if st.session_state.analysis_results:
                entities = st.session_state.analysis_results.get('entities', [])
                interactions = st.session_state.analysis_results.get('interactions', [])
                
                context['current_medications'] = [e.get('drug', '') for e in entities]
                context['drug_interactions'] = interactions
                context['patient_age'] = st.session_state.analysis_results.get('patient_age')
            
            # Get bot response
            with st.spinner("Dr. Sarah is typing..."):
                try:
                    response = get_therapy_response(user_input, context)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_response = "I apologize, but I'm having technical difficulties right now. Please try again in a moment, or if this is urgent, please contact your healthcare provider or crisis services."
                    st.session_state.chat_history.append({"role": "assistant", "content": error_response})
                    st.error(f"Therapy bot error: {e}")
            
            # Clear input and refresh
            st.rerun()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Emergency resources
        with st.expander("🆘 Crisis Resources"):
            st.markdown("""
            **If you're in crisis or having thoughts of self-harm:**
            
            🇺🇸 **US Resources:**
            - National Suicide Prevention Lifeline: **112**
            - Crisis Text Line: Text **HOME** to **741741**
            
            🌍 **International:**
            - International Association for Suicide Prevention: [iasp.info](https://www.iasp.info/resources/Crisis_Centres/)
            
            🚨 **Emergency:** Call your local emergency number (108, 112, etc.)
            """)

if __name__ == "__main__":
    main()