"""
AI Chatbot service for GSuite CLI - Gemini Powered (v3)
"""

import logging
from typing import Optional
from google import genai

logger = logging.getLogger(__name__)

class AIChatBot:
    """Chatbot service powered by Google Gemini (New SDK)"""
    
    def __init__(self, gemini_key: str = ''):
        self.gemini_key = gemini_key
        self.model_name = "gemini-1.5-flash" # Use standard flash model for speed/efficiency
        self._client = None
        self.system_prompt = """
        You are the GSuite CLI AI assistant, a professional and efficient helper designed to manage 
        Google Workspace services (Calendar, Gmail, Sheets, Drive, Docs, Tasks) via the command line.
        
        Your goals:
        1. Help users interact with their Google services accurately.
        2. Provide concise, professional, and actionable advice.
        3. Suggest 'gs' CLI commands when appropriate.
        4. Be context-aware and polite.
        
        Current environment: Windows CLI.
        Tool name: GSuite CLI (alias: gs).
        """
    
    @property
    def client(self):
        """Lazy initialization of the Gemini client"""
        if self._client is None and self.gemini_key:
            self._client = genai.Client(api_key=self.gemini_key)
        return self._client
    
    def chat(self, message: str) -> str:
        """Send a message to Gemini and get a response using the new SDK"""
        if not self.gemini_key:
            return "❌ Gemini API key not configured. Set it with 'gs config set ai.gemini_api_key YOUR_KEY'"
        
        try:
            if not self.client:
                return "❌ Failed to initialize Gemini client."
                
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[self.system_prompt, message]
            )
            
            if response and response.text:
                return response.text
            return "❌ No response from Gemini"
            
        except Exception as e:
            logger.error(f"Gemini SDK error: {e}")
            return f"❌ Gemini AI Error: {str(e)}"
