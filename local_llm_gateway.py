"""
Local LLM Privacy Gateway
=========================
Uses a local LLM (via Ollama) for intelligent PII detection and masking.
This is more accurate than regex patterns for complex or ambiguous cases.

Requirements:
    - Ollama installed: https://ollama.ai
    - A model pulled: ollama pull llama3.1:8b

Configuration (via .env file):
    - OLLAMA_MODEL: Model to use (default: llama3.1:8b)
    - OLLAMA_URL: Ollama API endpoint (default: http://localhost:11434)

This demonstrates "Strategy 2: Local LLM for Sensitive Processing" from the blog.
"""

import json
import os
import re
import requests
from typing import Dict, Tuple, Optional

# Default configuration
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class LocalLLMGateway:
    """
    A privacy gateway that uses a local LLM (Ollama) for intelligent
    PII detection and masking before sending data to external AI APIs.
    """

    def __init__(self, model: str = None, ollama_url: str = None):
        """
        Initialize the Local LLM Gateway.
        
        Args:
            model: The Ollama model to use (reads from OLLAMA_MODEL env var if not provided)
            ollama_url: The Ollama API endpoint (reads from OLLAMA_URL env var if not provided)
        """
        # Read from environment variables with fallback to defaults
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        self.mapping: Dict[str, str] = {}

    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _check_model_available(self) -> bool:
        """Check if the specified model is available in Ollama."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(m.get("name", "").startswith(self.model) for m in models)
            return False
        except requests.exceptions.RequestException:
            return False

    def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """
        Call the local Ollama model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            
        Returns:
            The model's response text
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent output
                "num_predict": 2000
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120  # Local models can be slow
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call Ollama: {e}")

    def detect_pii(self, text: str) -> Dict[str, list]:
        """
        Use the local LLM to detect PII in the text.
        
        Args:
            text: The input text to analyze
            
        Returns:
            A dictionary of detected PII by type
        """
        system_prompt = """You are a PII (Personally Identifiable Information) detector.
Your job is to identify sensitive data in text and return it in a structured JSON format.

Detect these types of PII:
- credit_cards: Credit/debit card numbers
- ssn: Social Security Numbers
- emails: Email addresses
- phones: Phone numbers
- names: Person names (full names or first+last names)
- addresses: Physical addresses
- dates_of_birth: Birth dates
- account_numbers: Bank account or other account numbers

Return ONLY valid JSON in this exact format (no other text):
{
    "credit_cards": ["list of detected credit card numbers"],
    "ssn": ["list of detected SSN"],
    "emails": ["list of detected emails"],
    "phones": ["list of detected phone numbers"],
    "names": ["list of detected person names"],
    "addresses": ["list of detected addresses"],
    "dates_of_birth": ["list of detected birth dates"],
    "account_numbers": ["list of detected account numbers"]
}

If no PII is found for a category, use an empty list [].
Only include actual PII found in the text, not placeholders or examples."""

        prompt = f"""Analyze this text and identify all PII (Personally Identifiable Information).
Return ONLY the JSON result, no explanation.

Text to analyze:
---
{text}
---

JSON result:"""

        response = self._call_ollama(prompt, system_prompt)
        
        # Parse the JSON response
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError:
            # If parsing fails, return empty dict
            return {}

    def mask(self, text: str, detected_pii: Dict[str, list] = None) -> Tuple[str, Dict[str, str]]:
        """
        Use the local LLM to detect and mask all PII in the text.
        
        Args:
            text: The input text potentially containing sensitive data
            detected_pii: Optional pre-detected PII dict (to avoid calling LLM again)
            
        Returns:
            A tuple of (masked_text, mapping_dict)
        """
        self.mapping = {}
        
        # Detect PII using local LLM (skip if already provided)
        if detected_pii is None:
            detected_pii = self.detect_pii(text)
        
        masked_text = text
        counters = {}
        
        # Create mappings and replace PII with placeholders
        for pii_type, values in detected_pii.items():
            if not values:
                continue
                
            counters[pii_type] = 0
            for value in values:
                if value and value in masked_text:
                    counters[pii_type] += 1
                    placeholder = f"[{pii_type.upper()}_{counters[pii_type]}]"
                    self.mapping[placeholder] = value
                    masked_text = masked_text.replace(value, placeholder)
        
        return masked_text, self.mapping.copy()
    
    def detect_and_mask(self, text: str) -> Tuple[Dict[str, list], str, Dict[str, str]]:
        """
        Detect PII and mask in a single operation (efficient - only one LLM call).
        
        Args:
            text: The input text potentially containing sensitive data
            
        Returns:
            A tuple of (detected_pii, masked_text, mapping_dict)
        """
        detected_pii = self.detect_pii(text)
        masked_text, mapping = self.mask(text, detected_pii)
        return detected_pii, masked_text, mapping

    def unmask(self, text: str, mapping: Dict[str, str] = None) -> str:
        """
        Restore original values in the text using the mapping.
        
        Args:
            text: The text containing placeholders
            mapping: Optional mapping dict. If not provided, uses internal mapping.
            
        Returns:
            Text with placeholders replaced by original values
        """
        if mapping is None:
            mapping = self.mapping
        
        unmasked_text = text
        for placeholder, original in mapping.items():
            unmasked_text = unmasked_text.replace(placeholder, original)
        
        return unmasked_text

    def get_status(self) -> Dict[str, bool]:
        """
        Check the status of Ollama and the model.
        
        Returns:
            Dict with 'ollama_running' and 'model_available' status
        """
        return {
            "ollama_running": self._check_ollama_available(),
            "model_available": self._check_model_available()
        }


def demonstrate_local_llm_masking():
    """Demonstrate the local LLM masking functionality."""
    gateway = LocalLLMGateway()
    
    print("=" * 60)
    print("LOCAL LLM PRIVACY GATEWAY DEMONSTRATION")
    print("=" * 60)
    
    # Check Ollama status
    status = gateway.get_status()
    print(f"\n🔍 Checking Ollama status...")
    print(f"   Ollama running: {'✅' if status['ollama_running'] else '❌'}")
    print(f"   Model available: {'✅' if status['model_available'] else '❌'}")
    
    if not status['ollama_running']:
        print("\n❌ Ollama is not running!")
        print("   Start Ollama with: ollama serve")
        print("   Or install from: https://ollama.ai")
        return
    
    if not status['model_available']:
        print(f"\n❌ Model '{gateway.model}' is not available!")
        print(f"   Pull it with: ollama pull {gateway.model}")
        return
    
    sample_text = """
    Hello, my name is John Smith and I need help with my account.
    My credit card number is 4532-1234-5678-9012 and my SSN is 123-45-6789.
    You can reach me at john.smith@email.com or call me at (555) 123-4567.
    I live at 123 Main Street, New York, NY 10001.
    My date of birth is March 15, 1985.
    Please review my recent transactions and provide spending advice.
    """
    
    print("\n📝 ORIGINAL TEXT:")
    print("-" * 40)
    print(sample_text)
    
    print("\n⏳ Analyzing text with local LLM...")
    
    # Detect PII
    detected = gateway.detect_pii(sample_text)
    print("\n🔍 DETECTED PII (by local LLM):")
    print("-" * 40)
    for pii_type, values in detected.items():
        if values:
            print(f"   {pii_type}: {values}")
    
    # Mask the text
    masked_text, mapping = gateway.mask(sample_text)
    
    print("\n🔒 MASKED TEXT (Safe to send to AI API):")
    print("-" * 40)
    print(masked_text)
    
    print("\n🗺️  MAPPING (Stored locally, never sent to API):")
    print("-" * 40)
    for placeholder, original in mapping.items():
        print(f"   {placeholder} → {original}")
    
    # Simulate AI response
    simulated_response = """
    Hello [NAMES_1]! I've reviewed the account associated with card [CREDIT_CARDS_1].
    Based on your transaction history at [ADDRESSES_1], I recommend setting up 
    automatic payments. I'll send a detailed report to [EMAILS_1].
    """
    
    print("\n🤖 SIMULATED AI RESPONSE (with placeholders):")
    print("-" * 40)
    print(simulated_response)
    
    unmasked_response = gateway.unmask(simulated_response, mapping)
    
    print("\n🔓 UNMASKED RESPONSE (Restored for user):")
    print("-" * 40)
    print(unmasked_response)
    
    print("\n" + "=" * 60)
    print("✅ Local LLM successfully detected and masked PII!")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_local_llm_masking()
