"""
Privacy Gateway Module
======================
Detects and masks sensitive data (PII) before sending to external AI APIs.
Provides unmasking functionality to restore original values in responses.

Supported PII Types:
- Credit Card Numbers
- Social Security Numbers (SSN)
- Email Addresses
- Phone Numbers
- Person Names (common patterns)
"""

import re
from typing import Dict, Tuple


class PrivacyGateway:
    """
    A privacy gateway that masks sensitive data before sending to AI APIs
    and unmasks the response to restore original values.
    """

    def __init__(self):
        # Mapping to store original values: {placeholder: original_value}
        self.mapping: Dict[str, str] = {}
        self.counters = {
            'credit_card': 0,
            'ssn': 0,
            'email': 0,
            'phone': 0,
            'name': 0
        }

    def reset(self):
        """Reset the mapping and counters for a new masking session."""
        self.mapping = {}
        for key in self.counters:
            self.counters[key] = 0

    def _create_placeholder(self, pii_type: str) -> str:
        """Generate a unique placeholder for a PII type."""
        self.counters[pii_type] += 1
        return f"[{pii_type.upper()}_{self.counters[pii_type]}]"

    def _mask_credit_cards(self, text: str) -> str:
        """Mask credit card numbers (13-19 digits, with optional spaces/dashes)."""
        # Pattern matches common credit card formats
        pattern = r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{1,7})\b'
        
        def replace(match):
            original = match.group(1)
            placeholder = self._create_placeholder('credit_card')
            self.mapping[placeholder] = original
            return placeholder
        
        return re.sub(pattern, replace, text)

    def _mask_ssn(self, text: str) -> str:
        """Mask Social Security Numbers (XXX-XX-XXXX format)."""
        pattern = r'\b(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b'
        
        def replace(match):
            original = match.group(1)
            # Verify it looks like an SSN (not a phone number)
            digits_only = re.sub(r'[-\s]', '', original)
            if len(digits_only) == 9:
                placeholder = self._create_placeholder('ssn')
                self.mapping[placeholder] = original
                return placeholder
            return original
        
        return re.sub(pattern, replace, text)

    def _mask_emails(self, text: str) -> str:
        """Mask email addresses."""
        pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        
        def replace(match):
            original = match.group(1)
            placeholder = self._create_placeholder('email')
            self.mapping[placeholder] = original
            return placeholder
        
        return re.sub(pattern, replace, text)

    def _mask_phone_numbers(self, text: str) -> str:
        """Mask phone numbers (various US formats)."""
        # Matches: (123) 456-7890, 123-456-7890, 123.456.7890, 1234567890
        pattern = r'\b(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b'
        
        def replace(match):
            original = match.group(1)
            # Skip if it's already masked as SSN
            if '[SSN_' not in text[:match.start()]:
                placeholder = self._create_placeholder('phone')
                self.mapping[placeholder] = original
                return placeholder
            return original
        
        return re.sub(pattern, replace, text)

    def _mask_names(self, text: str) -> str:
        """
        Mask common name patterns.
        This is a simplified approach - for production, use NER libraries like spaCy.
        Looks for patterns like "name is John Smith" or "I'm Jane Doe"
        """
        # Pattern for "my name is X" or "I'm X" or "I am X"
        name_patterns = [
            (r"(?i)(my name is\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", 2),
            (r"(?i)(I'?m\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", 2),
            (r"(?i)(I am\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", 2),
            (r"(?i)(name:\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", 2),
        ]
        
        for pattern, group_idx in name_patterns:
            def make_replace(grp_idx):
                def replace(match):
                    original = match.group(grp_idx)
                    placeholder = self._create_placeholder('name')
                    self.mapping[placeholder] = original
                    # Return prefix + placeholder
                    return match.group(1) + placeholder
                return replace
            
            text = re.sub(pattern, make_replace(group_idx), text)
        
        return text

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Mask all sensitive data in the input text.
        
        Args:
            text: The input text potentially containing sensitive data.
            
        Returns:
            A tuple of (masked_text, mapping_dict) where mapping_dict
            contains {placeholder: original_value} pairs.
        """
        self.reset()
        
        # Apply masking in a specific order to avoid conflicts
        masked_text = text
        masked_text = self._mask_credit_cards(masked_text)
        masked_text = self._mask_ssn(masked_text)
        masked_text = self._mask_emails(masked_text)
        masked_text = self._mask_phone_numbers(masked_text)
        masked_text = self._mask_names(masked_text)
        
        return masked_text, self.mapping.copy()

    def unmask(self, text: str, mapping: Dict[str, str] = None) -> str:
        """
        Restore original values in the text using the mapping.
        
        Args:
            text: The text containing placeholders.
            mapping: Optional mapping dict. If not provided, uses internal mapping.
            
        Returns:
            Text with placeholders replaced by original values.
        """
        if mapping is None:
            mapping = self.mapping
        
        unmasked_text = text
        for placeholder, original in mapping.items():
            unmasked_text = unmasked_text.replace(placeholder, original)
        
        return unmasked_text


def demonstrate_masking():
    """Demonstrate the masking functionality with example text."""
    gateway = PrivacyGateway()
    
    sample_text = """
    Hello, my name is John Smith and I need help with my account.
    My credit card number is 4532-1234-5678-9012 and my SSN is 123-45-6789.
    You can reach me at john.smith@email.com or call me at (555) 123-4567.
    Please review my recent transactions and provide spending advice.
    """
    
    print("=" * 60)
    print("PRIVACY GATEWAY DEMONSTRATION")
    print("=" * 60)
    
    print("\n📝 ORIGINAL TEXT:")
    print("-" * 40)
    print(sample_text)
    
    masked_text, mapping = gateway.mask(sample_text)
    
    print("\n🔒 MASKED TEXT (Safe to send to AI API):")
    print("-" * 40)
    print(masked_text)
    
    print("\n🗺️  MAPPING (Stored locally, never sent to API):")
    print("-" * 40)
    for placeholder, original in mapping.items():
        print(f"  {placeholder} → {original}")
    
    # Simulate AI response with placeholders
    simulated_response = """
    Hello [NAME_1]! I've reviewed the account associated with card [CREDIT_CARD_1].
    Based on your transaction history, I recommend setting up automatic payments.
    I'll send a detailed report to [EMAIL_1].
    """
    
    print("\n🤖 SIMULATED AI RESPONSE (with placeholders):")
    print("-" * 40)
    print(simulated_response)
    
    unmasked_response = gateway.unmask(simulated_response, mapping)
    
    print("\n🔓 UNMASKED RESPONSE (Restored for user):")
    print("-" * 40)
    print(unmasked_response)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demonstrate_masking()
