#!/usr/bin/env python3
"""
Sensitive Data Protector - Simple Web UI (Regex Only)
======================================================
A streamlined Flask web application that demonstrates the privacy gateway
using fast regex-based PII detection. No Ollama required.

Usage:
    python app_simple.py
    Open http://localhost:5002 in your browser
"""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

from privacy_gateway import PrivacyGateway

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')

# Initialize gateway
gateway = PrivacyGateway()

def get_openai_client():
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        return None
    return OpenAI(api_key=api_key)

@app.route("/")
def index():
    """Render the main page."""
    openai_available = get_openai_client() is not None
    return render_template("index_simple.html", openai_available=openai_available)

@app.route("/process", methods=["POST"])
def process():
    """Process the input text through the privacy gateway."""
    data = request.json
    user_input = data.get("input", "")
    
    result = {
        "original_input": user_input,
        "detected_pii": [],
        "masked_input": "",
        "mapping": {},
        "ai_response_masked": "",
        "ai_response_unmasked": "",
        "error": None
    }
    
    try:
        # Step 1 & 2: Detect and mask PII using regex
        masked_input, mapping = gateway.mask(user_input)
        
        for placeholder, value in mapping.items():
            pii_type = placeholder.replace("[", "").replace("]", "").rsplit("_", 1)[0]
            result["detected_pii"].append({
                "type": pii_type,
                "value": value
            })
        
        result["masked_input"] = masked_input
        result["mapping"] = mapping
        
        # Step 3: Call OpenAI
        if mapping:
            client = get_openai_client()
            if client:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a helpful assistant. When you see placeholders 
                            like [NAME_1], [CREDIT_CARD_1], [EMAIL_1], etc., treat them as actual 
                            values and refer to them naturally in your response. Keep the placeholders 
                            in your response so they can be unmasked later. Keep your response concise."""
                        },
                        {
                            "role": "user",
                            "content": masked_input
                        }
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                result["ai_response_masked"] = response.choices[0].message.content
                
                # Step 4: Unmask the response
                result["ai_response_unmasked"] = gateway.unmask(
                    result["ai_response_masked"], mapping
                )
            else:
                result["error"] = "OpenAI API key not configured"
        else:
            result["ai_response_masked"] = "No PII detected in input."
            result["ai_response_unmasked"] = result["ai_response_masked"]
            
    except Exception as e:
        result["error"] = str(e)
    
    return jsonify(result)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛡️  Sensitive Data Protector - Simple UI (Regex)")
    print("=" * 60)
    print("\n📍 Open http://localhost:5002 in your browser")
    print("⚡ Fast regex-based PII detection - no Ollama needed!")
    print("📸 Take screenshots of each step for your blog!\n")
    app.run(debug=True, host="0.0.0.0", port=5002)
