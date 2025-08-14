import os

import logging
from typing import Optional, Dict, List
import google.generativeai as genai
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TherapyDoctorBot:
    """
    AI Therapy Doctor using Google Gemini API
    Provides mental health support and medical guidance
    """
    
    def __init__(self):
        self.api_key = os.getenv('MISTRAL_AI_API')
        self.model = None
        self.chat_session = None
        self.setup_api()
        
        # Medical context and guidelines
        self.system_prompt = """
You are Dr. Sarah, a compassionate and experienced therapy doctor and medical advisor. 
You provide:

1. **Mental Health Support**: 
   - Listen empathetically to patients' concerns
   - Provide stress management techniques
   - Offer coping strategies for anxiety, depression
   - Suggest mindfulness and relaxation exercises

2. **Medical Guidance**:
   - Answer questions about medications and side effects
   - Provide general health advice
   - Explain medical conditions in simple terms
   - Suggest when to seek immediate medical attention

3. **Lifestyle Recommendations**:
   - Healthy diet suggestions
   - Exercise recommendations
   - Sleep hygiene tips
   - Work-life balance advice

**IMPORTANT GUIDELINES**:
- Always be empathetic and supportive
- Never diagnose serious conditions - refer to specialists
- Encourage professional help when needed
- Keep responses concise but thorough
- Use simple, non-medical language
- Always prioritize patient safety

**SAFETY NOTES**:
- If patient mentions self-harm, immediately provide crisis resources
- For emergency symptoms, advise immediate medical attention
- Remind that this is supportive guidance, not replacement for professional care

Remember: You are here to support, guide, and provide comfort while maintaining professional medical ethics.
"""

    def setup_api(self):
        """Initialize Gemini API"""
        try:
            if not self.api_key:
                logger.warning("Gemini API key not found. Bot will use fallback responses.")
                return False
            
            genai.configure(api_key=self.api_key)
            
            # Configure the model
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name="gemini-pro",
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=self.system_prompt
            )
            
            # Start chat session
            self.chat_session = self.model.start_chat(history=[])
            
            logger.info("✅ Gemini API initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            return False

    def get_response(self, user_message: str, context: Dict = None) -> str:
        """
        Get response from therapy doctor bot
        
        Args:
            user_message: User's input message
            context: Additional context (medications, analysis results, etc.)
            
        Returns:
            Bot's response message
        """
        try:
            if not self.model or not self.chat_session:
                return self.get_fallback_response(user_message)
            
            # Prepare enhanced message with context
            enhanced_message = self.prepare_message_with_context(user_message, context)
            
            # Get response from Gemini
            response = self.chat_session.send_message(enhanced_message)
            
            # Log the interaction
            logger.info(f"Therapy bot interaction completed")
            
            return self.format_response(response.text)
            
        except Exception as e:
            logger.error(f"Error getting bot response: {e}")
            return self.get_fallback_response(user_message)

    def prepare_message_with_context(self, message: str, context: Dict = None) -> str:
        """Prepare message with additional context"""
        
        enhanced_message = f"Patient: {message}"
        
        if context:
            context_info = []
            
            # Add medication context
            if context.get('current_medications'):
                meds = ', '.join(context['current_medications'])
                context_info.append(f"Current medications: {meds}")
            
            # Add interaction warnings
            if context.get('drug_interactions'):
                interactions = len(context['drug_interactions'])
                if interactions > 0:
                    context_info.append(f"Note: {interactions} drug interactions detected in recent analysis")
            
            # Add patient age
            if context.get('patient_age'):
                context_info.append(f"Patient age: {context['patient_age']}")
            
            if context_info:
                enhanced_message += f"\n\nContext: {'; '.join(context_info)}"
        
        return enhanced_message

    def format_response(self, response: str) -> str:
        """Format and clean the bot response"""
        
        # Remove markdown formatting for cleaner display
        response = response.replace('**', '').replace('*', '')
        
        # Ensure proper greeting format
        if not response.startswith(('Hello', 'Hi', 'Dr. Sarah here')):
            response = f"Dr. Sarah here. {response}"
        
        # Add supportive closing if not present
        supportive_closings = [
            'take care', 'be well', 'stay strong', 'feel better', 
            'reach out', 'support', 'here for you'
        ]
        
        if not any(closing in response.lower() for closing in supportive_closings):
            response += "\n\nRemember, I'm here to support you. Take care! 💙"
        
        return response

    def get_fallback_response(self, user_message: str) -> str:
        """Provide fallback responses when API is unavailable"""
        
        message_lower = user_message.lower()
        
        # Mental health support responses
        if any(word in message_lower for word in ['anxious', 'anxiety', 'worried', 'stress', 'panic']):
            return """Dr. Sarah here. I understand you're feeling anxious. Here are some immediate techniques that can help:

🌬️ **Breathing Exercise**: Try 4-7-8 breathing - inhale for 4, hold for 7, exhale for 8
🧘 **Grounding**: Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
💭 **Mindfulness**: Focus on the present moment, not future worries

Remember, anxiety is treatable. If symptoms persist, please consider speaking with a mental health professional.

Take care! 💙"""

        elif any(word in message_lower for word in ['sad', 'depressed', 'down', 'hopeless']):
            return """Dr. Sarah here. I hear that you're going through a difficult time. Your feelings are valid, and reaching out shows strength.

💡 **Small Steps**: Start with tiny achievable goals today
🌞 **Sunlight**: Try to get some natural light, even briefly  
🤝 **Connection**: Reach out to someone you trust
📝 **Journaling**: Write down three things you're grateful for

If you're having thoughts of self-harm, please contact:
• National Suicide Prevention Lifeline: 988
• Crisis Text Line: Text HOME to 741741

You matter, and help is available. 💙"""

        elif any(word in message_lower for word in ['medication', 'pills', 'drug', 'medicine']):
            return """Dr. Sarah here. I can provide general guidance about medications:

💊 **Taking Medications**:
• Take exactly as prescribed
• Don't skip doses
• Set reminders if needed
• Store properly

⚠️ **Side Effects**:
• Contact your doctor for concerning symptoms
• Don't stop medications abruptly
• Keep a symptom diary

🔍 **Questions**:
• Always ask your pharmacist or doctor about interactions
• Verify dosages
• Understand what each medication does

For specific medical concerns, please consult your healthcare provider.

Stay healthy! 💙"""

        else:
            return """Dr. Sarah here. Thank you for reaching out. I'm here to provide support and guidance on:

🧠 **Mental Health**: Anxiety, stress, mood concerns
💊 **Medical Questions**: Medication guidance, health tips  
🌱 **Wellness**: Lifestyle recommendations, healthy habits
🆘 **Crisis Support**: When you need immediate help

How can I best support you today? Remember, while I provide guidance, for serious medical concerns, please consult with healthcare professionals.

I'm here for you! 💙"""

    def get_crisis_resources(self) -> str:
        """Return crisis support resources"""
        return """🆘 **IMMEDIATE CRISIS RESOURCES**:

**Suicide Prevention**:
• National Suicide Prevention Lifeline: 988
• Crisis Text Line: Text HOME to 741741
• International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

**Mental Health Crisis**:
• NAMI Helpline: 1-800-950-NAMI (6264)
• SAMHSA Helpline: 1-800-662-4357

**Emergency**: Call 911 or go to nearest emergency room

You are not alone. Help is available 24/7. 💙"""

    def analyze_medication_mood_impact(self, medications: List[str], mood_symptoms: str) -> str:
        """Analyze potential medication effects on mood"""
        
        # Common medications that can affect mood
        mood_affecting_meds = {
            'beta-blockers': ['metoprolol', 'propranolol', 'atenolol'],
            'corticosteroids': ['prednisone', 'prednisolone', 'dexamethasone'],
            'interferons': ['interferon'],
            'anticonvulsants': ['phenytoin', 'carbamazepine'],
            'antimalarials': ['mefloquine'],
            'hormones': ['birth control', 'contraceptive', 'hormone']
        }
        
        potentially_affecting = []
        for category, med_list in mood_affecting_meds.items():
            for med in medications:
                if any(drug.lower() in med.lower() for drug in med_list):
                    potentially_affecting.append((med, category))
        
        if potentially_affecting:
            response = "I notice you're taking medications that can sometimes affect mood:\n\n"
            for med, category in potentially_affecting:
                response += f"• {med} ({category})\n"
            
            response += "\nThis doesn't mean your medication is causing issues, but it's worth discussing with your doctor if you notice mood changes. Never stop medications without medical guidance.\n\n"
            response += "Keep a mood diary to track patterns and share with your healthcare provider."
            
            return response
        
        return "Your current medications don't commonly affect mood, but individual responses vary. Always discuss any mood changes with your healthcare provider."

# Convenience function
def get_therapy_response(message: str, context: Dict = None) -> str:
    """Get response from therapy doctor bot"""
    bot = TherapyDoctorBot()
    return bot.get_response(message, context)