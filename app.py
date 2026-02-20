#!/usr/bin/env python3
"""
Sensitive Data Protector - Web UI
==================================
A Flask web application that demonstrates the privacy gateway visually.
Perfect for taking screenshots for blog posts and documentation.

Usage:
    python app.py
    Open http://localhost:5000 in your browser
"""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

from privacy_gateway import PrivacyGateway
from local_llm_gateway import LocalLLMGateway

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize gateways
regex_gateway = PrivacyGateway()
local_llm_gateway = None  # Initialized on demand

def get_openai_client():
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        return None
    return OpenAI(api_key=api_key)

def check_ollama_status():
    """Check if Ollama is available."""
    global local_llm_gateway
    try:
        if local_llm_gateway is None:
            local_llm_gateway = LocalLLMGateway()  # Reads from .env
        status = local_llm_gateway.get_status()
        status["model_name"] = local_llm_gateway.model
        return status
    except:
        return {"ollama_running": False, "model_available": False, "model_name": "unknown"}

@app.route("/")
def index():
    """Render the main page."""
    ollama_status = check_ollama_status()
    openai_available = get_openai_client() is not None
    return render_template("index.html", 
                         ollama_status=ollama_status,
                         openai_available=openai_available)

@app.route("/process", methods=["POST"])
def process():
    """Process the input text through the privacy gateway."""
    global local_llm_gateway
    
    data = request.json
    user_input = data.get("input", "")
    use_local_llm = data.get("use_local_llm", False)
    call_openai = data.get("call_openai", True)
    
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
        # Step 1 & 2: Detect and mask PII
        if use_local_llm:
            if local_llm_gateway is None:
                local_llm_gateway = LocalLLMGateway()  # Reads from .env
            
            # Detect and mask in ONE LLM call (efficient!)
            detected, masked_input, mapping = local_llm_gateway.detect_and_mask(user_input)
            for pii_type, values in detected.items():
                for value in values:
                    if value:
                        result["detected_pii"].append({
                            "type": pii_type.upper(),
                            "value": value
                        })
        else:
            # Use regex gateway
            masked_input, mapping = regex_gateway.mask(user_input)
            for placeholder, value in mapping.items():
                pii_type = placeholder.replace("[", "").replace("]", "").rsplit("_", 1)[0]
                result["detected_pii"].append({
                    "type": pii_type,
                    "value": value
                })
        
        result["masked_input"] = masked_input
        result["mapping"] = mapping
        
        # Step 3: Call OpenAI (if requested)
        if call_openai and mapping:  # Only call if there's something masked
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
                if use_local_llm:
                    result["ai_response_unmasked"] = local_llm_gateway.unmask(
                        result["ai_response_masked"], mapping
                    )
                else:
                    result["ai_response_unmasked"] = regex_gateway.unmask(
                        result["ai_response_masked"], mapping
                    )
            else:
                result["error"] = "OpenAI API key not configured"
        elif call_openai and not mapping:
            result["ai_response_masked"] = "No PII detected - nothing to demonstrate"
            result["ai_response_unmasked"] = result["ai_response_masked"]
            
    except Exception as e:
        result["error"] = str(e)
    
    return jsonify(result)

@app.route("/status")
def status():
    """Check system status."""
    return jsonify({
        "ollama": check_ollama_status(),
        "openai": get_openai_client() is not None
    })

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛡️  Sensitive Data Protector - Web UI")
    print("=" * 60)
    print("\n📍 Open http://localhost:5001 in your browser")
    print("📸 Take screenshots of each step for your blog!\n")
    app.run(debug=True, host="0.0.0.0", port=5001)
