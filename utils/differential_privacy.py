"""
Differential Privacy utilities for protecting sensitive data during AI processing.
This adds calibrated noise to preserve privacy while maintaining AI utility.
"""

import re
import random
import string
from typing import List, Union, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DifferentialPrivacy:
    """Differential Privacy implementation for text and numerical data."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize differential privacy parameters.
        
        Args:
            epsilon: Privacy budget (lower = more private, higher = more accurate)
            delta: Probability of privacy failure
        """
        self.epsilon = epsilon
        self.delta = delta
        self.noise_scale = 1.0 / epsilon
        
    def add_noise_to_text(self, text: str, noise_probability: float = 0.1) -> str:
        """
        Add noise to text data while preserving meaning.
        
        Args:
            text: Input text to anonymize
            noise_probability: Probability of adding noise to each token
            
        Returns:
            Text with added noise
        """
        if not text:
            return text
            
        # Split into sentences for better noise addition
        sentences = re.split(r'[.!?]+', text)
        noisy_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                noisy_sentence = self._add_sentence_noise(sentence.strip(), noise_probability)
                noisy_sentences.append(noisy_sentence)
        
        return '. '.join(noisy_sentences) + '.'
    
    def _add_sentence_noise(self, sentence: str, noise_probability: float) -> str:
        """Add noise to individual sentences."""
        
        # Split into words
        words = sentence.split()
        noisy_words = []
        
        for word in words:
            if random.random() < noise_probability:
                # Add noise to this word
                noisy_word = self._add_word_noise(word)
                noisy_words.append(noisy_word)
            else:
                noisy_words.append(word)
        
        return ' '.join(noisy_words)
    
    def _add_word_noise(self, word: str) -> str:
        """Add noise to individual words while preserving structure."""
        
        if len(word) <= 2:
            return word  # Don't modify very short words
            
        # Different noise strategies based on word type
        if word.isdigit():
            # Add noise to numbers
            return self._add_number_noise(word)
        elif word.lower() in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
            # Common words - minimal noise
            return word
        elif word[0].isupper():
            # Proper nouns - add slight noise
            return self._add_proper_noun_noise(word)
        else:
            # Regular words - add moderate noise
            return self._add_regular_word_noise(word)
    
    def _add_number_noise(self, number_str: str) -> str:
        """Add noise to numerical values."""
        
        try:
            number = float(number_str)
            
            # Add Laplace noise for differential privacy
            import numpy as np
            noise = np.random.laplace(0, self.noise_scale)
            noisy_number = number + noise
            
            # Format based on original format
            if '.' in number_str:
                # Decimal number
                decimal_places = len(number_str.split('.')[1])
                return f"{noisy_number:.{decimal_places}f}"
            else:
                # Integer
                return str(int(round(noisy_number)))
                
        except ValueError:
            return number_str
    
    def _add_proper_noun_noise(self, word: str) -> str:
        """Add minimal noise to proper nouns."""
        
        if random.random() < 0.3:  # 30% chance of noise
            # Replace with similar word or add slight modification
            if word.lower() in ['john', 'jane', 'mike', 'sarah']:
                # Common names - replace with similar
                replacements = {
                    'john': 'james', 'jane': 'jill', 'mike': 'mark', 'sarah': 'susan'
                }
                return replacements.get(word.lower(), word).title()
            else:
                # Other proper nouns - slight modification
                return word + random.choice(['', 's', 'n'])
        
        return word
    
    def _add_regular_word_noise(self, word: str) -> str:
        """Add noise to regular words."""
        
        if random.random() < 0.2:  # 20% chance of noise
            # Add slight modification
            if len(word) > 3:
                # Change middle character
                mid = len(word) // 2
                new_char = random.choice(string.ascii_lowercase)
                return word[:mid] + new_char + word[mid+1:]
        
        return word
    
    def anonymize_personal_identifiers(self, text: str) -> str:
        """
        Anonymize personal identifiers like names, emails, phone numbers.
        
        Args:
            text: Input text
            
        Returns:
            Text with personal identifiers anonymized
        """
        
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     '[EMAIL]', text)
        
        # Phone numbers (various formats)
        text = re.sub(r'\b(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', 
                     '[PHONE]', text)
        
        # Credit card numbers
        text = re.sub(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b', 
                     '[CREDIT_CARD]', text)
        
        # Social Security Numbers (US)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        
        # IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', text)
        
        return text
    
    def add_noise_to_structured_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add noise to structured data (JSON-like structures).
        
        Args:
            data: Structured data to anonymize
            
        Returns:
            Anonymized structured data
        """
        
        if isinstance(data, dict):
            noisy_data = {}
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    # Add noise to numbers
                    noisy_data[key] = self._add_number_noise(str(value))
                elif isinstance(value, str):
                    # Add noise to text
                    noisy_data[key] = self.add_noise_to_text(value)
                elif isinstance(value, list):
                    # Recursively process lists
                    noisy_data[key] = [self.add_noise_to_structured_data(item) 
                                     if isinstance(item, (dict, list)) else item 
                                     for item in value]
                elif isinstance(value, dict):
                    # Recursively process nested dicts
                    noisy_data[key] = self.add_noise_to_structured_data(value)
                else:
                    # Keep other types as-is
                    noisy_data[key] = value
            return noisy_data
        elif isinstance(data, list):
            return [self.add_noise_to_structured_data(item) 
                   if isinstance(item, (dict, list)) else item 
                   for item in data]
        else:
            return data
    
    def get_privacy_guarantees(self) -> Dict[str, float]:
        """
        Get the privacy guarantees provided by current settings.
        
        Returns:
            Dictionary with privacy parameters
        """
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "noise_scale": self.noise_scale,
            "privacy_level": "high" if self.epsilon < 0.5 else "medium" if self.epsilon < 2.0 else "low"
        }

# Convenience functions
def add_differential_privacy(data: Union[str, Dict[str, Any]], 
                           epsilon: float = 1.0) -> Union[str, Dict[str, Any]]:
    """
    Convenience function to add differential privacy to data.
    
    Args:
        data: Text or structured data to anonymize
        epsilon: Privacy budget
        
    Returns:
        Anonymized data
    """
    dp = DifferentialPrivacy(epsilon=epsilon)
    
    if isinstance(data, str):
        return dp.add_noise_to_text(data)
    elif isinstance(data, dict):
        return dp.add_noise_to_structured_data(data)
    else:
        return data

def anonymize_personal_data(text: str) -> str:
    """
    Convenience function to anonymize personal identifiers.
    
    Args:
        text: Text to anonymize
        
    Returns:
        Anonymized text
    """
    dp = DifferentialPrivacy()
    return dp.anonymize_personal_identifiers(text)
