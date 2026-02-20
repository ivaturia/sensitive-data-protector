#!/usr/bin/env python3
"""
Sensitive Data Protector - Local LLM Edition
=============================================
Demonstrates the hybrid architecture: Local LLM for PII detection + External API for reasoning.

This is "Strategy 2" from the blog: Use a local LLM to handle sensitive data processing,
and only send anonymized data to powerful external APIs.

Architecture:
    User Input → Local LLM (Ollama) → Mask PII → OpenAI API → Unmask → User

Requirements:
    - Ollama installed and running: https://ollama.ai
    - A model pulled: ollama pull llama3.2
    - OpenAI API key in .env file

Usage:
    python main_with_local_llm.py
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

from local_llm_gateway import LocalLLMGateway


def print_header():
    """Print application header."""
    print("\n" + "=" * 70)
    print("🛡️  SENSITIVE DATA PROTECTOR - Local LLM + OpenAI Hybrid Demo")
    print("=" * 70)
    print("\nThis demo uses a LOCAL LLM (Ollama) to detect and mask PII,")
    print("then sends only anonymized data to OpenAI for processing.")
    print("\n🏠 Sensitive data processing: LOCAL (Ollama)")
    print("☁️  Complex reasoning: EXTERNAL (OpenAI)")
    print("🔒 Your PII never leaves your machine!\n")


def print_section(title: str, content: str, emoji: str = ""):
    """Print a formatted section."""
    print(f"\n{emoji} {title}")
    print("-" * 50)
    print(content)


def check_prerequisites(gateway: LocalLLMGateway) -> bool:
    """Check if Ollama and the model are available."""
    print("🔍 Checking prerequisites...")
    
    status = gateway.get_status()
    
    print(f"   Ollama running: {'✅ Yes' if status['ollama_running'] else '❌ No'}")
    
    if not status['ollama_running']:
        print("\n❌ Ollama is not running!")
        print("\nTo fix this:")
        print("  1. Install Ollama from: https://ollama.ai")
        print("  2. Start Ollama: ollama serve")
        print("  3. Run this script again")
        return False
    
    print(f"   Model available: {'✅ Yes' if status['model_available'] else '❌ No'}")
    
    if not status['model_available']:
        print(f"\n❌ Model '{gateway.model}' is not available!")
        print(f"\nTo fix this, run: ollama pull {gateway.model}")
        return False
    
    print("   ✅ All prerequisites met!\n")
    return True


def get_user_input() -> str:
    """Get input from the user or use a demo prompt."""
    print("\n📝 Enter your prompt (or press Enter for demo):")
    print("   (Include sensitive data like names, emails, credit cards, SSN, addresses)")
    print("-" * 50)
    
    user_input = input("> ").strip()
    
    if not user_input:
        # Demo prompt with various PII types
        user_input = """
Hi, my name is Sarah Johnson and I need financial advice.
My credit card 4111-2222-3333-4444 was charged $500 yesterday.
My SSN is 987-65-4321 and email is sarah.johnson@example.com.
You can call me at (555) 987-6543 or visit me at 456 Oak Avenue, Boston, MA 02101.
My date of birth is June 12, 1990.
Can you help me understand if this charge is legitimate and what I should do?
"""
        print("\n[Using demo prompt with sample sensitive data]")
        print(user_input)
    
    return user_input


def call_openai_api(client: OpenAI, masked_prompt: str) -> str:
    """Send the masked prompt to OpenAI and return the response."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful financial advisor assistant. 
                    When you see placeholders like [NAMES_1], [CREDIT_CARDS_1], [EMAILS_1], etc., 
                    treat them as actual values and refer to them naturally in your response.
                    Keep the placeholders in your response so they can be unmasked later."""
                },
                {
                    "role": "user",
                    "content": masked_prompt
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"


def run_demo():
    """Run the main demonstration."""
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        print("\n❌ ERROR: OpenAI API key not found!")
        print("\nPlease set your API key in the .env file:")
        print("  1. Open the .env file")
        print("  2. Replace 'your-openai-api-key-here' with your actual API key")
        print("  3. Run this script again")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    # Initialize gateways (reads OLLAMA_MODEL and OLLAMA_URL from .env)
    gateway = LocalLLMGateway()
    client = OpenAI(api_key=api_key)
    
    print_header()
    
    # Check Ollama prerequisites
    if not check_prerequisites(gateway):
        print("\n💡 TIP: You can still use the regex-based version:")
        print("   python main.py")
        sys.exit(1)
    
    # Get user input
    user_prompt = get_user_input()
    
    # Step 1: Local LLM detects and masks PII
    print("\n" + "=" * 70)
    print("STEP 1: LOCAL LLM DETECTING & MASKING PII (Ollama)")
    print("=" * 70)
    
    print("\n⏳ Analyzing text with local LLM (this may take a moment)...")
    
    # First show detected PII
    detected_pii = gateway.detect_pii(user_prompt)
    
    print("\n🔍 PII DETECTED BY LOCAL LLM:")
    print("-" * 50)
    pii_count = 0
    for pii_type, values in detected_pii.items():
        if values:
            pii_count += len(values)
            for value in values:
                print(f"   [{pii_type.upper()}] {value}")
    
    if pii_count == 0:
        print("   No PII detected.")
    
    # Mask the text
    masked_prompt, mapping = gateway.mask(user_prompt)
    
    print_section("ORIGINAL INPUT (contains PII)", user_prompt, "🔴")
    print_section("MASKED INPUT (safe to send to API)", masked_prompt, "🟢")
    
    if mapping:
        print("\n🗺️  PII MAPPING (stored locally, never sent to API)")
        print("-" * 50)
        for placeholder, original in mapping.items():
            print(f"   {placeholder} → {original}")
    
    # Step 2: Send to OpenAI
    print("\n" + "=" * 70)
    print("STEP 2: SENDING MASKED DATA TO OPENAI (External API)")
    print("=" * 70)
    print("\n⏳ Sending masked prompt to OpenAI...")
    print("   (Only anonymized data is transmitted)")
    
    ai_response = call_openai_api(client, masked_prompt)
    
    print_section("AI RESPONSE (with placeholders)", ai_response, "🤖")
    
    # Step 3: Unmask the response
    print("\n" + "=" * 70)
    print("STEP 3: UNMASKING RESPONSE (Local Processing)")
    print("=" * 70)
    
    final_response = gateway.unmask(ai_response, mapping)
    
    print_section("FINAL RESPONSE (restored for user)", final_response, "✨")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY - HYBRID ARCHITECTURE IN ACTION")
    print("=" * 70)
    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│  WHAT STAYED LOCAL (Private)          WHAT WENT TO CLOUD       │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Your actual PII ({pii_count} items)       ☁️  Anonymized prompt       │
│  ✅ The mapping dictionary            ☁️  Generic placeholders    │
│  ✅ PII detection (Ollama)            ☁️  Complex reasoning       │
│  ✅ Final unmasking                                              │
└─────────────────────────────────────────────────────────────────┘

🏠 Local LLM (Ollama {gateway.model}): Handled all sensitive data
☁️  External API (OpenAI): Only saw anonymized placeholders
🔒 Result: Powerful AI capabilities WITHOUT exposing your PII!
""")


def main():
    """Main entry point."""
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
