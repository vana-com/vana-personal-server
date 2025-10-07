"""
Synthetic Data Generation Engine for Privacy-Preserving AI.
This system generates artificial data that preserves the statistical and semantic properties
of original data while containing no actual user information.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Union, Optional, Tuple
from dataclasses import dataclass
import random
import string
import re
from collections import Counter, defaultdict
import json
import time

logger = logging.getLogger(__name__)

@dataclass
class SyntheticDataResult:
    """Result of synthetic data generation with quality metrics."""
    synthetic_data: Union[List[str], Dict[str, Any], np.ndarray]
    original_data: Union[List[str], Dict[str, Any], np.ndarray]
    quality_metrics: Dict[str, float]
    privacy_metrics: Dict[str, float]
    generation_metadata: Dict[str, Any]

class SyntheticDataGenerator:
    """Generates synthetic data that preserves utility while protecting privacy."""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize synthetic data generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        # Common patterns for text generation
        self.common_words = [
            "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "up", "about", "into", "through", "during", "before",
            "after", "above", "below", "between", "among", "within", "without"
        ]
        
        # Financial patterns
        self.financial_patterns = {
            "amounts": ["$100", "$250", "$500", "$1000", "$2500", "$5000"],
            "categories": ["groceries", "transportation", "entertainment", "utilities", "shopping"],
            "merchants": ["Walmart", "Target", "Amazon", "Gas Station", "Restaurant", "Bank"]
        }
        
        # Medical patterns
        self.medical_patterns = {
            "symptoms": ["headache", "fever", "fatigue", "pain", "nausea", "dizziness"],
            "treatments": ["medication", "therapy", "surgery", "rest", "exercise", "diet"],
            "specialists": ["cardiologist", "dermatologist", "neurologist", "orthopedist"]
        }
        
        # Business patterns
        self.business_patterns = {
            "industries": ["technology", "healthcare", "finance", "retail", "manufacturing"],
            "company_sizes": ["startup", "small", "medium", "large", "enterprise"],
            "roles": ["manager", "director", "executive", "specialist", "analyst"]
        }
    
    def generate_synthetic_text(self, original_texts: List[str], 
                               privacy_level: float = 1.0,
                               preserve_structure: bool = True) -> SyntheticDataResult:
        """
        Generate synthetic text data preserving statistical properties.
        
        Args:
            original_texts: List of original text strings
            privacy_level: Privacy level (0.1 = max privacy, 5.0 = min privacy)
            preserve_structure: Whether to preserve text structure
            
        Returns:
            SyntheticDataResult with generated text and quality metrics
        """
        
        if not original_texts:
            raise ValueError("Original texts list cannot be empty")
        
        logger.info(f"Generating synthetic text for {len(original_texts)} documents")
        
        # Analyze original text patterns
        text_patterns = self._analyze_text_patterns(original_texts)
        
        # Generate synthetic texts
        synthetic_texts = []
        for i, original_text in enumerate(original_texts):
            synthetic_text = self._generate_single_synthetic_text(
                original_text, text_patterns, privacy_level, preserve_structure
            )
            synthetic_texts.append(synthetic_text)
        
        # Calculate quality metrics
        quality_metrics = self._calculate_text_quality_metrics(original_texts, synthetic_texts)
        
        # Calculate privacy metrics
        privacy_metrics = self._calculate_text_privacy_metrics(original_texts, synthetic_texts)
        
        # Create metadata
        generation_metadata = {
            "generation_type": "text",
            "privacy_level": privacy_level,
            "preserve_structure": preserve_structure,
            "original_count": len(original_texts),
            "synthetic_count": len(synthetic_texts),
            "timestamp": time.time()
        }
        
        return SyntheticDataResult(
            synthetic_data=synthetic_texts,
            original_data=original_texts,
            quality_metrics=quality_metrics,
            privacy_metrics=privacy_metrics,
            generation_metadata=generation_metadata
        )
    
    def generate_synthetic_features(self, original_features: Dict[str, Any],
                                  privacy_level: float = 1.0) -> SyntheticDataResult:
        """
        Generate synthetic feature data preserving statistical distributions.
        
        Args:
            original_features: Original feature dictionary
            privacy_level: Privacy level (0.1 = max privacy, 5.0 = min privacy)
            
        Returns:
            SyntheticDataResult with generated features and quality metrics
        """
        
        logger.info("Generating synthetic features")
        
        # Analyze feature patterns
        feature_patterns = self._analyze_feature_patterns(original_features)
        
        # Generate synthetic features
        synthetic_features = {}
        for key, value in original_features.items():
            synthetic_value = self._generate_synthetic_feature_value(
                value, feature_patterns.get(key, {}), privacy_level
            )
            synthetic_features[key] = synthetic_value
        
        # Calculate quality metrics
        quality_metrics = self._calculate_feature_quality_metrics(original_features, synthetic_features)
        
        # Calculate privacy metrics
        privacy_metrics = self._calculate_feature_privacy_metrics(original_features, synthetic_features)
        
        # Create metadata
        generation_metadata = {
            "generation_type": "features",
            "privacy_level": privacy_level,
            "feature_count": len(original_features),
            "timestamp": time.time()
        }
        
        return SyntheticDataResult(
            synthetic_data=synthetic_features,
            original_data=original_features,
            quality_metrics=quality_metrics,
            privacy_metrics=privacy_metrics,
            generation_metadata=generation_metadata
        )
    
    def _analyze_text_patterns(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze patterns in original texts for synthetic generation."""
        
        patterns = {
            "length_stats": {},
            "word_patterns": {},
            "sentence_patterns": {},
            "topic_patterns": {},
            "style_patterns": {}
        }
        
        # Length statistics
        lengths = [len(text) for text in texts]
        patterns["length_stats"] = {
            "mean": np.mean(lengths),
            "std": np.std(lengths),
            "min": min(lengths),
            "max": max(lengths)
        }
        
        # Word patterns
        all_words = []
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            all_words.extend(words)
        
        word_freq = Counter(all_words)
        patterns["word_patterns"] = {
            "vocabulary_size": len(word_freq),
            "total_words": len(all_words),
            "avg_word_length": np.mean([len(word) for word in all_words]),
            "common_words": dict(word_freq.most_common(20))
        }
        
        # Sentence patterns
        all_sentences = []
        for text in texts:
            sentences = re.split(r'[.!?]+', text)
            all_sentences.extend([s.strip() for s in sentences if s.strip()])
        
        patterns["sentence_patterns"] = {
            "sentence_count": len(all_sentences),
            "avg_sentence_length": np.mean([len(s) for s in all_sentences]),
            "sentence_length_std": np.std([len(s) for s in all_sentences])
        }
        
        # Topic patterns (simple keyword-based)
        topic_keywords = {
            "financial": ["bank", "account", "money", "transaction", "payment"],
            "medical": ["patient", "diagnosis", "treatment", "symptom", "medical"],
            "business": ["company", "business", "market", "customer", "product"],
            "technical": ["technology", "software", "system", "data", "network"]
        }
        
        topic_scores = defaultdict(int)
        for text in texts:
            text_lower = text.lower()
            for topic, keywords in topic_keywords.items():
                score = sum(text_lower.count(keyword) for keyword in keywords)
                topic_scores[topic] += score
        
        patterns["topic_patterns"] = dict(topic_scores)
        
        return patterns
    
    def _generate_single_synthetic_text(self, original_text: str, 
                                       patterns: Dict[str, Any],
                                       privacy_level: float,
                                       preserve_structure: bool) -> str:
        """Generate a single synthetic text document."""
        
        # Determine text type based on content
        text_type = self._classify_text_type(original_text)
        
        if text_type == "financial":
            return self._generate_financial_text(patterns, privacy_level, preserve_structure)
        elif text_type == "medical":
            return self._generate_medical_text(patterns, privacy_level, preserve_structure)
        elif text_type == "business":
            return self._generate_business_text(patterns, privacy_level, preserve_structure)
        else:
            return self._generate_general_text(patterns, privacy_level, preserve_structure)
    
    def _classify_text_type(self, text: str) -> str:
        """Classify text type for appropriate synthetic generation."""
        text_lower = text.lower()
        
        financial_indicators = ["bank", "account", "transaction", "payment", "balance"]
        medical_indicators = ["patient", "diagnosis", "treatment", "symptom", "medical"]
        business_indicators = ["company", "business", "market", "customer", "product"]
        
        financial_score = sum(text_lower.count(indicator) for indicator in financial_indicators)
        medical_score = sum(text_lower.count(indicator) for indicator in medical_indicators)
        business_score = sum(text_lower.count(indicator) for indicator in business_indicators)
        
        if financial_score > medical_score and financial_score > business_score:
            return "financial"
        elif medical_score > financial_score and medical_score > business_score:
            return "medical"
        elif business_score > financial_score and business_score > medical_score:
            return "business"
        else:
            return "general"
    
    def _generate_financial_text(self, patterns: Dict[str, Any], 
                                privacy_level: float,
                                preserve_structure: bool) -> str:
        """Generate synthetic financial text."""
        
        # Generate synthetic financial content
        synthetic_lines = []
        
        # Header
        synthetic_lines.append("Financial Statement")
        synthetic_lines.append("=" * 20)
        
        # Account information (synthetic)
        synthetic_lines.append(f"Account: {self._generate_synthetic_account()}")
        synthetic_lines.append(f"Balance: {self._generate_synthetic_amount()}")
        synthetic_lines.append("")
        
        # Transactions
        synthetic_lines.append("Recent Transactions:")
        num_transactions = random.randint(3, 8)
        
        for i in range(num_transactions):
            merchant = random.choice(self.financial_patterns["merchants"])
            category = random.choice(self.financial_patterns["categories"])
            amount = self._generate_synthetic_amount()
            synthetic_lines.append(f"- {merchant}: {amount} ({category})")
        
        return "\n".join(synthetic_lines)
    
    def _generate_medical_text(self, patterns: Dict[str, Any], 
                              privacy_level: float,
                              preserve_structure: bool) -> str:
        """Generate synthetic medical text."""
        
        synthetic_lines = []
        
        # Header
        synthetic_lines.append("Medical Record")
        synthetic_lines.append("=" * 15)
        
        # Patient information (synthetic)
        synthetic_lines.append(f"Patient ID: {self._generate_synthetic_id()}")
        synthetic_lines.append(f"Date: {self._generate_synthetic_date()}")
        synthetic_lines.append("")
        
        # Symptoms
        synthetic_lines.append("Symptoms:")
        num_symptoms = random.randint(2, 5)
        symptoms = random.sample(self.medical_patterns["symptoms"], num_symptoms)
        for symptom in symptoms:
            synthetic_lines.append(f"- {symptom}")
        
        synthetic_lines.append("")
        
        # Treatment
        synthetic_lines.append("Treatment:")
        treatment = random.choice(self.medical_patterns["treatments"])
        synthetic_lines.append(f"- {treatment}")
        
        return "\n".join(synthetic_lines)
    
    def _generate_business_text(self, patterns: Dict[str, Any], 
                               privacy_level: float,
                               preserve_structure: bool) -> str:
        """Generate synthetic business text."""
        
        synthetic_lines = []
        
        # Header
        synthetic_lines.append("Business Report")
        synthetic_lines.append("=" * 15)
        
        # Company information (synthetic)
        industry = random.choice(self.business_patterns["industries"])
        size = random.choice(self.business_patterns["company_sizes"])
        synthetic_lines.append(f"Industry: {industry}")
        synthetic_lines.append(f"Company Size: {size}")
        synthetic_lines.append("")
        
        # Business metrics
        synthetic_lines.append("Key Metrics:")
        synthetic_lines.append(f"- Revenue: {self._generate_synthetic_revenue()}")
        synthetic_lines.append(f"- Employees: {self._generate_synthetic_employee_count()}")
        synthetic_lines.append(f"- Market Share: {self._generate_synthetic_percentage()}")
        
        return "\n".join(synthetic_lines)
    
    def _generate_general_text(self, patterns: Dict[str, Any], 
                              privacy_level: float,
                              preserve_structure: bool) -> str:
        """Generate synthetic general text."""
        
        # Generate text based on patterns
        target_length = int(patterns["length_stats"]["mean"])
        target_sentences = int(patterns["sentence_patterns"]["sentence_count"])
        
        synthetic_lines = []
        
        for i in range(target_sentences):
            sentence_length = int(patterns["sentence_patterns"]["avg_sentence_length"])
            sentence = self._generate_synthetic_sentence(sentence_length)
            synthetic_lines.append(sentence)
        
        return " ".join(synthetic_lines)
    
    def _generate_synthetic_account(self) -> str:
        """Generate synthetic account number."""
        return f"ACC-{random.randint(100000, 999999)}"
    
    def _generate_synthetic_amount(self) -> str:
        """Generate synthetic monetary amount."""
        amount = random.randint(50, 5000)
        return f"${amount}"
    
    def _generate_synthetic_id(self) -> str:
        """Generate synthetic ID."""
        return f"ID-{random.randint(10000, 99999)}"
    
    def _generate_synthetic_date(self) -> str:
        """Generate synthetic date."""
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        year = random.randint(2020, 2024)
        return f"{month:02d}/{day:02d}/{year}"
    
    def _generate_synthetic_revenue(self) -> str:
        """Generate synthetic revenue figure."""
        revenue = random.randint(100000, 10000000)
        if revenue >= 1000000:
            return f"${revenue/1000000:.1f}M"
        else:
            return f"${revenue/1000:.0f}K"
    
    def _generate_synthetic_employee_count(self) -> str:
        """Generate synthetic employee count."""
        count = random.randint(10, 1000)
        if count >= 100:
            return f"{count//100*100}+"
        else:
            return str(count)
    
    def _generate_synthetic_percentage(self) -> str:
        """Generate synthetic percentage."""
        percentage = random.randint(5, 25)
        return f"{percentage}%"
    
    def _generate_synthetic_sentence(self, target_length: int) -> str:
        """Generate synthetic sentence with target length."""
        words = []
        current_length = 0
        
        while current_length < target_length:
            word = random.choice(self.common_words)
            words.append(word)
            current_length += len(word) + 1  # +1 for space
        
        # Capitalize first word and add period
        if words:
            words[0] = words[0].capitalize()
            return " ".join(words) + "."
        
        return "Sample text."
    
    def _analyze_feature_patterns(self, features: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze patterns in feature data for synthetic generation."""
        
        patterns = {}
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                patterns[key] = {
                    "type": "numeric",
                    "value": value,
                    "range": (value * 0.8, value * 1.2)
                }
            elif isinstance(value, str):
                patterns[key] = {
                    "type": "string",
                    "value": value,
                    "length": len(value),
                    "pattern": self._extract_string_pattern(value)
                }
            elif isinstance(value, bool):
                patterns[key] = {
                    "type": "boolean",
                    "value": value
                }
            elif isinstance(value, list):
                patterns[key] = {
                    "type": "list",
                    "length": len(value),
                    "item_patterns": [self._analyze_feature_patterns({"item": item})["item"] for item in value]
                }
        
        return patterns
    
    def _extract_string_pattern(self, text: str) -> str:
        """Extract pattern from string (e.g., email, phone, etc.)."""
        if re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            return "email"
        elif re.match(r'\b\d{3}-\d{3}-\d{4}\b', text):
            return "phone"
        elif re.match(r'\$\d+', text):
            return "currency"
        else:
            return "text"
    
    def _generate_synthetic_feature_value(self, original_value: Any, 
                                        pattern: Dict[str, Any],
                                        privacy_level: float) -> Any:
        """Generate synthetic value for a single feature."""
        
        if pattern["type"] == "numeric":
            # Add noise to numeric values
            noise_factor = 1.0 / privacy_level
            noise = random.uniform(-noise_factor, noise_factor) * original_value * 0.1
            return original_value + noise
        
        elif pattern["type"] == "string":
            if pattern["pattern"] == "email":
                return self._generate_synthetic_email()
            elif pattern["pattern"] == "phone":
                return self._generate_synthetic_phone()
            elif pattern["pattern"] == "currency":
                return self._generate_synthetic_amount()
            else:
                return self._generate_synthetic_text_string(pattern["length"])
        
        elif pattern["type"] == "boolean":
            # Sometimes flip boolean for privacy
            if random.random() < (1.0 / privacy_level):
                return not original_value
            return original_value
        
        elif pattern["type"] == "list":
            # Generate synthetic list
            synthetic_items = []
            for item_pattern in pattern["item_patterns"]:
                synthetic_item = self._generate_synthetic_feature_value(
                    item_pattern["value"], item_pattern, privacy_level
                )
                synthetic_items.append(synthetic_item)
            return synthetic_items
        
        return original_value
    
    def _generate_synthetic_email(self) -> str:
        """Generate synthetic email address."""
        domains = ["example.com", "test.org", "demo.net", "sample.io"]
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def _generate_synthetic_phone(self) -> str:
        """Generate synthetic phone number."""
        area_code = random.randint(200, 999)
        prefix = random.randint(200, 999)
        line = random.randint(1000, 9999)
        return f"{area_code}-{prefix}-{line}"
    
    def _generate_synthetic_text_string(self, target_length: int) -> str:
        """Generate synthetic text string with target length."""
        words = []
        current_length = 0
        
        while current_length < target_length:
            word = random.choice(self.common_words)
            words.append(word)
            current_length += len(word) + 1
        
        return " ".join(words)[:target_length]
    
    def _calculate_text_quality_metrics(self, original_texts: List[str], 
                                      synthetic_texts: List[str]) -> Dict[str, float]:
        """Calculate quality metrics for synthetic text generation."""
        
        metrics = {}
        
        # Length preservation
        original_lengths = [len(text) for text in original_texts]
        synthetic_lengths = [len(text) for text in synthetic_texts]
        
        metrics["length_correlation"] = np.corrcoef(original_lengths, synthetic_lengths)[0, 1] if len(original_lengths) > 1 else 1.0
        
        # Word count preservation
        original_word_counts = [len(text.split()) for text in original_texts]
        synthetic_word_counts = [len(text.split()) for text in synthetic_texts]
        
        metrics["word_count_correlation"] = np.corrcoef(original_word_counts, synthetic_word_counts)[0, 1] if len(original_word_counts) > 1 else 1.0
        
        # Structure preservation
        original_sentence_counts = [len(re.split(r'[.!?]+', text)) for text in original_texts]
        synthetic_sentence_counts = [len(re.split(r'[.!?]+', text)) for text in synthetic_texts]
        
        metrics["sentence_count_correlation"] = np.corrcoef(original_sentence_counts, synthetic_sentence_counts)[0, 1] if len(original_sentence_counts) > 1 else 1.0
        
        # Overall quality score
        metrics["overall_quality"] = np.mean([
            metrics["length_correlation"],
            metrics["word_count_correlation"],
            metrics["sentence_count_correlation"]
        ])
        
        return metrics
    
    def _calculate_text_privacy_metrics(self, original_texts: List[str], 
                                      synthetic_texts: List[str]) -> Dict[str, float]:
        """Calculate privacy metrics for synthetic text generation."""
        
        metrics = {}
        
        # Exact match detection
        exact_matches = 0
        total_comparisons = 0
        
        for orig_text in original_texts:
            for synth_text in synthetic_texts:
                total_comparisons += 1
                if orig_text in synth_text or synth_text in orig_text:
                    exact_matches += 1
        
        metrics["exact_match_rate"] = exact_matches / total_comparisons if total_comparisons > 0 else 0
        
        # Word overlap analysis
        all_original_words = set()
        all_synthetic_words = set()
        
        for text in original_texts:
            words = set(re.findall(r'\b\w+\b', text.lower()))
            all_original_words.update(words)
        
        for text in synthetic_texts:
            words = set(re.findall(r'\b\w+\b', text.lower()))
            all_synthetic_words.update(words)
        
        if all_original_words:
            word_overlap = len(all_original_words & all_synthetic_words) / len(all_original_words)
            metrics["word_overlap_rate"] = word_overlap
        else:
            metrics["word_overlap_rate"] = 0
        
        # Privacy score (inverse of overlap)
        metrics["privacy_score"] = 1.0 - metrics["word_overlap_rate"]
        
        return metrics
    
    def _calculate_feature_quality_metrics(self, original_features: Dict[str, Any], 
                                         synthetic_features: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality metrics for synthetic feature generation."""
        
        metrics = {}
        
        # Value preservation
        value_correlations = []
        for key in original_features:
            if key in synthetic_features:
                if isinstance(original_features[key], (int, float)) and isinstance(synthetic_features[key], (int, float)):
                    # For numeric values, calculate relative difference
                    if original_features[key] != 0:
                        relative_diff = abs(synthetic_features[key] - original_features[key]) / abs(original_features[key])
                        value_correlations.append(1.0 - relative_diff)
                    else:
                        value_correlations.append(1.0)
                else:
                    # For non-numeric, check if type is preserved
                    if type(original_features[key]) == type(synthetic_features[key]):
                        value_correlations.append(1.0)
                    else:
                        value_correlations.append(0.0)
        
        metrics["value_preservation"] = np.mean(value_correlations) if value_correlations else 0
        
        # Structure preservation
        structure_score = 0
        if len(original_features) == len(synthetic_features):
            structure_score += 0.5
        if set(original_features.keys()) == set(synthetic_features.keys()):
            structure_score += 0.5
        
        metrics["structure_preservation"] = structure_score
        
        # Overall quality
        metrics["overall_quality"] = (metrics["value_preservation"] + metrics["structure_preservation"]) / 2
        
        return metrics
    
    def _calculate_feature_privacy_metrics(self, original_features: Dict[str, Any], 
                                         synthetic_features: Dict[str, Any]) -> Dict[str, float]:
        """Calculate privacy metrics for synthetic feature generation."""
        
        metrics = {}
        
        # Exact value overlap
        exact_overlaps = 0
        total_features = len(original_features)
        
        for key in original_features:
            if key in synthetic_features:
                if original_features[key] == synthetic_features[key]:
                    exact_overlaps += 1
        
        metrics["exact_value_overlap"] = exact_overlaps / total_features if total_features > 0 else 0
        
        # Type preservation (good for utility, but we want some variation)
        type_preservation = 0
        for key in original_features:
            if key in synthetic_features:
                if type(original_features[key]) == type(synthetic_features[key]):
                    type_preservation += 1
        
        metrics["type_preservation"] = type_preservation / total_features if total_features > 0 else 0
        
        # Privacy score (inverse of exact overlap)
        metrics["privacy_score"] = 1.0 - metrics["exact_value_overlap"]
        
        return metrics

# Global instance
synthetic_generator = SyntheticDataGenerator()

# Convenience functions
def generate_synthetic_text(texts: List[str], privacy_level: float = 1.0) -> SyntheticDataResult:
    """Generate synthetic text with default privacy settings."""
    return synthetic_generator.generate_synthetic_text(texts, privacy_level=privacy_level)

def generate_synthetic_features(features: Dict[str, Any], privacy_level: float = 1.0) -> SyntheticDataResult:
    """Generate synthetic features with default privacy settings."""
    return synthetic_generator.generate_synthetic_features(features, privacy_level=privacy_level)
