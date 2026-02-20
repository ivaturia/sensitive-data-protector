#!/usr/bin/env python3
"""
Sensitive Data Protector Demo
==============================
A demonstration of how to protect sensitive data (PII) when using AI APIs.

This application shows:
1. How to detect and mask sensitive data before sending to OpenAI
2. How to process the AI response
3. How to unmask the response to restore original values

Usage:
    python main.py

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key (set in .env file)
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

from privacy_gateway import PrivacyGateway


def print_header():
    """Print application header."""
    print("\n" + "=" * 70)
    print("🛡️  SENSITIVE DATA PROTECTOR - Privacy-First AI Demo")
    print("=" * 70)
    print("\nThis demo shows how to safely use AI APIs without exposing sensitive data.")
    print("Your PII (credit cards, SSN, emails, etc.) is masked before sending to OpenAI.\n")


def print_section(title: str, content: str, emoji: str = ""):
    """Print a formatted section."""
    print(f"\n{emoji} {title}")
    print("-" * 50)
    print(content)


def get_user_input() -> str:
    """Get input from the user or use a demo prompt."""
    print("\n📝 Enter your prompt (or press Enter for demo):")
    print("   (Include sensitive data like names, emails, credit cards, SSN, phone)")
    print("-" * 50)
    
    user_input = input("> ").strip()
    
    if not user_input:
        # Demo prompt with various PII types
        user_input = """
Hi, my name is Sarah Johnson and I need financial advice.
My credit card 4111-2222-3333-4444 was charged $500 yesterday.
My SSN is 987-65-4321 and email is sarah.johnson@example.com.
You can call me at (555) 987-6543.
Can you help me understand if this charge is legitimate and what I should do?
"""
        print("\n[Using demo prompt with sample sensitive data]")
        print(user_input)
    
    return user_input


def call_openai_api(client: OpenAI, masked_prompt: str) -> str:
    """Send the masked prompt to OpenAI and return the response."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a cost-effective model for demo
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful financial advisor assistant. 
                    When you see placeholders like [NAME_1], [CREDIT_CARD_1], [EMAIL_1], etc., 
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
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        print("\n❌ ERROR: OpenAI API key not found!")
        print("\nPlease set your API key in the .env file:")
        print("  1. Open the .env file")
        print("  2. Replace 'your-openai-api-key-here' with your actual API key")
        print("  3. Run this script again")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    # Initialize OpenAI client and Privacy Gateway
    client = OpenAI(api_key=api_key)
    gateway = PrivacyGateway()
    
    print_header()
    
    # Get user input
    user_prompt = get_user_input()
    
    # Step 1: Mask sensitive data
    print("\n" + "=" * 70)
    print("STEP 1: MASKING SENSITIVE DATA")
    print("=" * 70)
    
    masked_prompt, mapping = gateway.mask(user_prompt)
    
    print_section("ORIGINAL INPUT (contains PII)", user_prompt, "🔴")
    print_section("MASKED INPUT (safe to send to API)", masked_prompt, "🟢")
    
    if mapping:
        print("\n🗺️  PII MAPPING (stored locally, never sent to API)")
        print("-" * 50)
        for placeholder, original in mapping.items():
            # Partially obscure the original value for display
            display_value = original[:3] + "***" + original[-3:] if len(original) > 6 else "***"
            print(f"   {placeholder} → {original} (shown as: {display_value})")
    else:
        print("\n✅ No sensitive data detected in input.")
    
    # Step 2: Send to OpenAI
    print("\n" + "=" * 70)
    print("STEP 2: CALLING OPENAI API")
    print("=" * 70)
    print("\n⏳ Sending masked prompt to OpenAI...")
    
    ai_response = call_openai_api(client, masked_prompt)
    
    print_section("AI RESPONSE (with placeholders)", ai_response, "🤖")
    
    # Step 3: Unmask the response
    print("\n" + "=" * 70)
    print("STEP 3: UNMASKING RESPONSE")
    print("=" * 70)
    
    final_response = gateway.unmask(ai_response, mapping)
    
    print_section("FINAL RESPONSE (restored for user)", final_response, "✨")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"""
✅ PII items detected and masked: {len(mapping)}
✅ Sensitive data never sent to external API
✅ Original values restored in final response
✅ Your privacy protected!

This demonstrates how you can use powerful AI APIs while keeping
sensitive data secure. The AI never sees your actual personal information!
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
        sys.exit(1)


if __name__ == "__main__":
    main()
