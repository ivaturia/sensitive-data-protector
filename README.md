# Sensitive Data Protector

A demonstration project showing how to protect sensitive data (PII) when using AI APIs like OpenAI.

## Overview

When building AI-powered applications, sending sensitive data directly to external APIs poses significant privacy and security risks. This project demonstrates a **Privacy Gateway** pattern that:

1. **Detects** sensitive data (credit cards, SSN, emails, phone numbers, names)
2. **Masks** the data with placeholders before sending to the AI API
3. **Processes** the AI response
4. **Unmasks** the response to restore original values for the user

The sensitive data **never leaves your local environment** - only anonymized placeholders are sent to the external API.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   User Input          Privacy Gateway         OpenAI API    │
│   ───────────────>   ────────────────>    ─────────────>   │
│   "My SSN is         "My SSN is           Process masked   │
│    123-45-6789"       [SSN_1]"             request          │
│                                                              │
│   Final Response  <── Unmask Response  <── AI Response      │
│   "Your SSN            with mapping        with [SSN_1]     │
│    123-45-6789                             placeholder      │
│    is secure"                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Two Approaches

This project demonstrates **two approaches** to PII detection:

| Approach | File | PII Detection | Requirements | Best For |
|----------|------|---------------|--------------|----------|
| **Regex-based** | `main.py` | Pattern matching | OpenAI API key only | Simple, fast, no extra setup |
| **Local LLM** | `main_with_local_llm.py` | Ollama + LLM | OpenAI + Ollama | Smarter detection, handles edge cases |

### Regex Approach (Simple)
Uses regular expressions to detect common PII patterns. Fast and lightweight, but may miss complex or ambiguous cases.

### Local LLM Approach (Hybrid Architecture)
Uses a local LLM (Ollama with Llama 3.2) to intelligently detect PII. More accurate for:
- Names in various formats
- Addresses
- Dates of birth
- Context-dependent information

The local LLM handles all sensitive data locally, while OpenAI is only used for complex reasoning on anonymized data.

## Supported PII Types

| Type | Example | Masked As |
|------|---------|-----------|
| Credit Card | `4532-1234-5678-9012` | `[CREDIT_CARD_1]` |
| SSN | `123-45-6789` | `[SSN_1]` |
| Email | `user@example.com` | `[EMAIL_1]` |
| Phone | `(555) 123-4567` | `[PHONE_1]` |
| Names | `John Smith` | `[NAME_1]` |
| Addresses* | `123 Main St, NY` | `[ADDRESSES_1]` |
| DOB* | `March 15, 1985` | `[DATES_OF_BIRTH_1]` |

*\* Only detected by the Local LLM approach*

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/sensitive-data-protector.git
cd sensitive-data-protector
```

### 2. Set Up Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and configure:
```

**Required:**
```env
OPENAI_API_KEY=your-openai-api-key-here
```

**Optional (for Local LLM approach):**
```env
OLLAMA_MODEL=llama3.1:8b          # Model to use (llama3.1:8b, mistral:latest, etc.)
OLLAMA_URL=http://localhost:11434  # Ollama API endpoint
```

Get your OpenAI key at: https://platform.openai.com/api-keys

### 4. Run the Demo

**Option A: Regex-based (Simple)**
```bash
python main.py
```

**Option B: Local LLM (Hybrid Architecture)**
```bash
# First, install and start Ollama: https://ollama.ai
ollama pull llama3.2
ollama serve  # In a separate terminal

# Then run the hybrid demo
python main_with_local_llm.py
```

## Example Output

```
======================================================================
🛡️  SENSITIVE DATA PROTECTOR - Privacy-First AI Demo
======================================================================

📝 Enter your prompt (or press Enter for demo):
> Hi, my name is Sarah Johnson. My credit card 4111-2222-3333-4444 was charged $500.

======================================================================
STEP 1: MASKING SENSITIVE DATA
======================================================================

🔴 ORIGINAL INPUT (contains PII)
--------------------------------------------------
Hi, my name is Sarah Johnson. My credit card 4111-2222-3333-4444 was charged $500.

🟢 MASKED INPUT (safe to send to API)
--------------------------------------------------
Hi, my name is [NAME_1]. My credit card [CREDIT_CARD_1] was charged $500.

🗺️  PII MAPPING (stored locally, never sent to API)
--------------------------------------------------
   [NAME_1] → Sarah Johnson
   [CREDIT_CARD_1] → 4111-2222-3333-4444

======================================================================
STEP 2: CALLING OPENAI API
======================================================================
⏳ Sending masked prompt to OpenAI...

🤖 AI RESPONSE (with placeholders)
--------------------------------------------------
Hello [NAME_1]! I can help you investigate the $500 charge on [CREDIT_CARD_1]...

======================================================================
STEP 3: UNMASKING RESPONSE
======================================================================

✨ FINAL RESPONSE (restored for user)
--------------------------------------------------
Hello Sarah Johnson! I can help you investigate the $500 charge on 4111-2222-3333-4444...
```

## Project Structure

```
sensitive-data-protector/
├── main.py                  # Demo app (regex-based PII detection)
├── main_with_local_llm.py   # Demo app (local LLM PII detection)
├── privacy_gateway.py       # Regex-based PII masking module
├── local_llm_gateway.py     # Local LLM (Ollama) PII masking module
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment configuration
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
└── README.md               # This file
```

## How It Works

### PrivacyGateway Class

The core of this project is the `PrivacyGateway` class in `privacy_gateway.py`:

```python
from privacy_gateway import PrivacyGateway

gateway = PrivacyGateway()

# Mask sensitive data
text = "My SSN is 123-45-6789 and email is user@example.com"
masked_text, mapping = gateway.mask(text)
# masked_text: "My SSN is [SSN_1] and email is [EMAIL_1]"
# mapping: {"[SSN_1]": "123-45-6789", "[EMAIL_1]": "user@example.com"}

# After getting AI response, unmask it
response = "Your SSN [SSN_1] is valid"
final = gateway.unmask(response, mapping)
# final: "Your SSN 123-45-6789 is valid"
```

### Integration with OpenAI

```python
from openai import OpenAI
from privacy_gateway import PrivacyGateway

client = OpenAI()
gateway = PrivacyGateway()

# 1. Mask the user input
masked_prompt, mapping = gateway.mask(user_input)

# 2. Send masked prompt to OpenAI (no PII exposed!)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": masked_prompt}]
)

# 3. Unmask the response
final_response = gateway.unmask(response.choices[0].message.content, mapping)
```

## Security Considerations

- **Never commit `.env` files** - They contain your API keys
- **The mapping stays local** - Only placeholders are sent to external APIs
- **For production use** - Consider using more robust PII detection libraries like [Microsoft Presidio](https://github.com/microsoft/presidio) or [spaCy NER](https://spacy.io/)
- **Validate your masking** - Test with various input patterns to ensure all PII is caught

## Extending the Project

### Adding New PII Types

To add detection for new types of sensitive data, extend the `PrivacyGateway` class:

```python
def _mask_custom_id(self, text: str) -> str:
    """Mask custom identifier patterns."""
    pattern = r'\b(CUSTOM-\d{6})\b'
    
    def replace(match):
        original = match.group(1)
        placeholder = self._create_placeholder('custom_id')
        self.mapping[placeholder] = original
        return placeholder
    
    return re.sub(pattern, replace, text)
```

### Using the Local LLM Gateway

For smarter PII detection using Ollama:

```python
from local_llm_gateway import LocalLLMGateway

gateway = LocalLLMGateway(model="llama3.2")

# Check if Ollama is running
status = gateway.get_status()
print(f"Ollama ready: {status['ollama_running'] and status['model_available']}")

# Mask with local LLM (detects more PII types)
text = "John Smith lives at 123 Main St and was born on March 15, 1985"
masked_text, mapping = gateway.mask(text)
# masked_text: "[NAMES_1] lives at [ADDRESSES_1] and was born on [DATES_OF_BIRTH_1]"
```

### Using with Other AI Providers

Both gateways are provider-agnostic. Use them with any AI API:

```python
# With Anthropic Claude
masked_prompt, mapping = gateway.mask(user_input)
response = anthropic.messages.create(messages=[{"content": masked_prompt}])
final = gateway.unmask(response.content, mapping)

# With Google Gemini
masked_prompt, mapping = gateway.mask(user_input)
response = genai.generate_content(masked_prompt)
final = gateway.unmask(response.text, mapping)
```

## Related Resources

- [Protecting Sensitive Data When Using AI APIs](https://codetocognition.dev/protecting-sensitive-data-when-using-ai-apis/) - Blog post explaining the concepts
- [Microsoft Presidio](https://github.com/microsoft/presidio) - Production-grade PII detection
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)

## License

MIT License - Feel free to use this in your own projects!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
