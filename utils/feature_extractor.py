"""
Content Feature Extractor for Privacy-Preserving AI Processing.
This system extracts safe, statistical features from user data without revealing sensitive content.
"""

import re
import logging
from typing import Dict, List, Any, Union, Tuple
from dataclasses import dataclass
import numpy as np
from collections import Counter, defaultdict
from utils.privacy_classifier import DocumentType, ExtractionRules, DocumentFeatures

logger = logging.getLogger(__name__)

@dataclass
class ExtractedFeatures:
    """Safe features extracted from user data."""
    document_features: DocumentFeatures
    statistical_features: Dict[str, Any]
    categorical_features: Dict[str, Any]
    temporal_features: Dict[str, Any]
    semantic_features: Dict[str, Any]
    privacy_score: float
    extraction_metadata: Dict[str, Any]

class PrivacyAwareFeatureExtractor:
    """Extracts safe features from user data while preserving privacy."""
    
    def __init__(self):
        self.feature_cache = {}
        
    def extract_features(self, text: str, document_features: DocumentFeatures) -> ExtractedFeatures:
        """
        Extract safe features from text based on document classification.
        
        Args:
            text: Original text content
            document_features: Document classification results
            
        Returns:
            ExtractedFeatures with safe, privacy-preserving features
        """
        
        logger.info(f"Extracting features for {document_features.document_type.value} document")
        
        # Extract statistical features
        statistical_features = self._extract_statistical_features(text, document_features)
        
        # Extract categorical features
        categorical_features = self._extract_categorical_features(text, document_features)
        
        # Extract temporal features
        temporal_features = self._extract_temporal_features(text, document_features)
        
        # Extract semantic features
        semantic_features = self._extract_semantic_features(text, document_features)
        
        # Calculate privacy score
        privacy_score = self._calculate_privacy_score(
            text, statistical_features, categorical_features, temporal_features, semantic_features
        )
        
        # Create extraction metadata
        extraction_metadata = {
            "extraction_timestamp": np.datetime64('now'),
            "document_type": document_features.document_type.value,
            "risk_level": document_features.risk_level,
            "confidence_score": document_features.confidence_score,
            "feature_count": len(statistical_features) + len(categorical_features) + 
                           len(temporal_features) + len(semantic_features)
        }
        
        return ExtractedFeatures(
            document_features=document_features,
            statistical_features=statistical_features,
            categorical_features=categorical_features,
            temporal_features=temporal_features,
            semantic_features=semantic_features,
            privacy_score=privacy_score,
            extraction_metadata=extraction_metadata
        )
    
    def _extract_statistical_features(self, text: str, doc_features: DocumentFeatures) -> Dict[str, Any]:
        """Extract statistical features that don't reveal specific content."""
        
        features = {}
        
        # Basic text statistics
        features["text_length"] = len(text)
        features["word_count"] = doc_features.word_count
        features["sentence_count"] = doc_features.sentence_count
        features["avg_word_length"] = np.mean([len(word) for word in text.split()]) if text.split() else 0
        features["avg_sentence_length"] = doc_features.word_count / doc_features.sentence_count if doc_features.sentence_count > 0 else 0
        
        # Character distribution
        char_counts = Counter(text.lower())
        features["alphabetical_ratio"] = sum(char_counts[c] for c in char_counts if c.isalpha()) / len(text) if text else 0
        features["numeric_ratio"] = sum(char_counts[c] for c in char_counts if c.isdigit()) / len(text) if text else 0
        features["punctuation_ratio"] = sum(char_counts[c] for c in char_counts if c in '.,!?;:') / len(text) if text else 0
        
        # Word frequency analysis (safe statistics only)
        words = text.lower().split()
        if words:
            word_freq = Counter(words)
            features["unique_word_ratio"] = len(word_freq) / len(words)
            features["most_common_word_freq"] = word_freq.most_common(1)[0][1] if word_freq else 0
            features["vocabulary_richness"] = len(word_freq) / np.sqrt(len(words)) if len(words) > 0 else 0
        
        # Apply privacy constraints based on document type
        features = self._apply_privacy_constraints(features, doc_features.document_type)
        
        return features
    
    def _extract_categorical_features(self, text: str, doc_features: DocumentFeatures) -> Dict[str, Any]:
        """Extract categorical features based on document type."""
        
        features = {}
        text_lower = text.lower()
        
        if doc_features.document_type == DocumentType.FINANCIAL:
            features.update(self._extract_financial_categories(text_lower))
        elif doc_features.document_type == DocumentType.MEDICAL:
            features.update(self._extract_medical_categories(text_lower))
        elif doc_features.document_type == DocumentType.BUSINESS:
            features.update(self._extract_business_categories(text_lower))
        elif doc_features.document_type == DocumentType.LEGAL:
            features.update(self._extract_legal_categories(text_lower))
        elif doc_features.document_type == DocumentType.TECHNICAL:
            features.update(self._extract_technical_categories(text_lower))
        else:
            features.update(self._extract_general_categories(text_lower))
        
        # Apply privacy constraints
        features = self._apply_privacy_constraints(features, doc_features.document_type)
        
        return features
    
    def _extract_financial_categories(self, text: str) -> Dict[str, Any]:
        """Extract financial categories without revealing specific amounts."""
        
        features = {}
        
        # Transaction categories
        transaction_keywords = {
            "groceries": ["grocery", "food", "supermarket", "market"],
            "transportation": ["gas", "fuel", "uber", "lyft", "taxi", "bus", "train"],
            "entertainment": ["movie", "restaurant", "bar", "concert", "show"],
            "utilities": ["electric", "water", "gas", "internet", "phone"],
            "shopping": ["amazon", "walmart", "target", "store", "shop"],
            "healthcare": ["medical", "doctor", "pharmacy", "hospital", "clinic"]
        }
        
        for category, keywords in transaction_keywords.items():
            count = sum(text.count(keyword) for keyword in keywords)
            if count > 0:
                features[f"transaction_{category}"] = count
        
        # Account types (without specific account numbers)
        account_types = {
            "checking": ["checking", "debit"],
            "savings": ["savings", "deposit"],
            "credit": ["credit", "loan"],
            "investment": ["investment", "stock", "bond", "fund"]
        }
        
        for acc_type, keywords in account_types.items():
            if any(keyword in text for keyword in keywords):
                features[f"account_type_{acc_type}"] = True
        
        # Amount ranges (binned for privacy)
        amount_patterns = re.findall(r'\$\d+', text)
        if amount_patterns:
            amounts = [int(re.search(r'\d+', amt).group()) for amt in amount_patterns]
            if amounts:
                max_amount = max(amounts)
                features["max_amount_range"] = self._bin_amount(max_amount)
                features["transaction_count"] = len(amounts)
        
        return features
    
    def _extract_medical_categories(self, text: str) -> Dict[str, Any]:
        """Extract medical categories without revealing specific patient information."""
        
        features = {}
        
        # Symptom categories
        symptom_keywords = {
            "pain": ["pain", "ache", "sore", "hurt"],
            "fever": ["fever", "temperature", "hot"],
            "fatigue": ["tired", "fatigue", "exhausted", "weak"],
            "digestive": ["nausea", "vomiting", "diarrhea", "stomach"],
            "respiratory": ["cough", "breathing", "chest", "throat"],
            "neurological": ["headache", "dizzy", "confusion", "memory"]
        }
        
        for symptom, keywords in symptom_keywords.items():
            count = sum(text.count(keyword) for keyword in keywords)
            if count > 0:
                features[f"symptom_{symptom}"] = count
        
        # Treatment types
        treatment_keywords = {
            "medication": ["medication", "medicine", "pill", "prescription"],
            "therapy": ["therapy", "counseling", "psychotherapy"],
            "surgery": ["surgery", "operation", "procedure"],
            "lifestyle": ["diet", "exercise", "rest", "sleep"]
        }
        
        for treatment, keywords in treatment_keywords.items():
            if any(keyword in text for keyword in keywords):
                features[f"treatment_{treatment}"] = True
        
        # Specialist types
        specialist_keywords = {
            "cardiologist": ["heart", "cardiac"],
            "dermatologist": ["skin", "dermatology"],
            "neurologist": ["brain", "nervous", "neurology"],
            "orthopedist": ["bone", "joint", "orthopedic"],
            "psychiatrist": ["mental", "psychiatric", "psychology"]
        }
        
        for specialist, keywords in specialist_keywords.items():
            if any(keyword in text for keyword in keywords):
                features[f"specialist_{specialist}"] = True
        
        return features
    
    def _extract_business_categories(self, text: str) -> Dict[str, Any]:
        """Extract business categories without revealing specific company information."""
        
        features = {}
        
        # Industry categories
        industry_keywords = {
            "technology": ["software", "tech", "digital", "computer"],
            "healthcare": ["medical", "health", "pharmaceutical"],
            "finance": ["banking", "financial", "investment"],
            "retail": ["retail", "ecommerce", "consumer"],
            "manufacturing": ["manufacturing", "production", "factory"],
            "services": ["consulting", "service", "professional"]
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in text for keyword in keywords):
                features[f"industry_{industry}"] = True
        
        # Company size indicators (ranges only)
        size_indicators = {
            "startup": ["startup", "small", "new company"],
            "medium": ["medium", "growing", "established"],
            "large": ["large", "enterprise", "corporation", "multinational"]
        }
        
        for size, keywords in size_indicators.items():
            if any(keyword in text for keyword in keywords):
                features[f"company_size_{size}"] = True
        
        # Business model indicators
        model_keywords = {
            "b2b": ["b2b", "business to business", "enterprise"],
            "b2c": ["b2c", "business to consumer", "retail"],
            "subscription": ["subscription", "recurring", "monthly"],
            "marketplace": ["marketplace", "platform", "network"]
        }
        
        for model, keywords in model_keywords.items():
            if any(keyword in text for keyword in keywords):
                features[f"business_model_{model}"] = True
        
        return features
    
    def _extract_legal_categories(self, text: str) -> Dict[str, Any]:
        """Extract legal categories without revealing specific case information."""
        
        features = {}
        
        # Legal areas
        legal_areas = {
            "criminal": ["criminal", "crime", "prosecution", "defense"],
            "civil": ["civil", "lawsuit", "litigation", "dispute"],
            "family": ["family", "divorce", "custody", "marriage"],
            "corporate": ["corporate", "business", "contract", "employment"],
            "real_estate": ["real estate", "property", "land", "housing"],
            "intellectual_property": ["patent", "copyright", "trademark", "ip"]
        }
        
        for area, keywords in legal_areas.items():
            if any(keyword in text for keyword in keywords):
                features[f"legal_area_{area}"] = True
        
        # Document types
        doc_types = {
            "contract": ["contract", "agreement", "terms"],
            "brief": ["brief", "motion", "pleading"],
            "opinion": ["opinion", "decision", "ruling"],
            "filing": ["filing", "petition", "complaint"]
        }
        
        for doc_type, keywords in doc_types.items():
            if any(keyword in text for keyword in keywords):
                features[f"document_type_{doc_type}"] = True
        
        return features
    
    def _extract_technical_categories(self, text: str) -> Dict[str, Any]:
        """Extract technical categories without revealing specific implementation details."""
        
        features = {}
        
        # Technology domains
        tech_domains = {
            "web": ["web", "website", "frontend", "backend"],
            "mobile": ["mobile", "app", "ios", "android"],
            "data": ["data", "database", "analytics", "ml"],
            "cloud": ["cloud", "aws", "azure", "gcp"],
            "security": ["security", "encryption", "authentication"],
            "devops": ["devops", "ci/cd", "deployment", "infrastructure"]
        }
        
        for domain, keywords in tech_domains.items():
            if any(keyword in text for keyword in keywords):
                features[f"tech_domain_{domain}"] = True
        
        # Complexity levels
        complexity_indicators = {
            "simple": ["simple", "basic", "straightforward"],
            "moderate": ["moderate", "standard", "typical"],
            "complex": ["complex", "advanced", "sophisticated"],
            "enterprise": ["enterprise", "large-scale", "distributed"]
        }
        
        for level, keywords in complexity_indicators.items():
            if any(keyword in text for keyword in keywords):
                features[f"complexity_{level}"] = True
        
        return features
    
    def _extract_general_categories(self, text: str) -> Dict[str, Any]:
        """Extract general categories for unspecified document types."""
        
        features = {}
        
        # Content categories
        content_categories = {
            "informational": ["information", "details", "facts", "data"],
            "instructional": ["instructions", "steps", "guide", "how to"],
            "narrative": ["story", "narrative", "experience", "event"],
            "analytical": ["analysis", "review", "evaluation", "assessment"]
        }
        
        for category, keywords in content_categories.items():
            if any(keyword in text for keyword in keywords):
                features[f"content_{category}"] = True
        
        # Writing style indicators
        style_indicators = {
            "formal": ["formal", "professional", "official"],
            "casual": ["casual", "informal", "conversational"],
            "technical": ["technical", "specialized", "expert"],
            "creative": ["creative", "artistic", "imaginative"]
        }
        
        for style, keywords in style_indicators.items():
            if any(keyword in text for keyword in keywords):
                features[f"writing_style_{style}"] = True
        
        return features
    
    def _extract_temporal_features(self, text: str, doc_features: DocumentFeatures) -> Dict[str, Any]:
        """Extract temporal features without revealing specific dates."""
        
        features = {}
        
        # Time period indicators
        time_periods = {
            "past": ["yesterday", "last week", "last month", "last year", "previously"],
            "present": ["today", "now", "currently", "at present"],
            "future": ["tomorrow", "next week", "next month", "next year", "upcoming"]
        }
        
        for period, keywords in time_periods.items():
            count = sum(text.lower().count(keyword) for keyword in keywords)
            if count > 0:
                features[f"time_period_{period}"] = count
        
        # Frequency indicators
        frequency_indicators = {
            "daily": ["daily", "every day", "each day"],
            "weekly": ["weekly", "every week", "each week"],
            "monthly": ["monthly", "every month", "each month"],
            "yearly": ["yearly", "annually", "every year"]
        }
        
        for freq, keywords in frequency_indicators.items():
            if any(keyword in text.lower() for keyword in keywords):
                features[f"frequency_{freq}"] = True
        
        # Duration indicators
        duration_indicators = {
            "short_term": ["brief", "short", "quick", "temporary"],
            "medium_term": ["ongoing", "current", "active"],
            "long_term": ["long-term", "permanent", "lasting", "sustained"]
        }
        
        for duration, keywords in duration_indicators.items():
            if any(keyword in text.lower() for keyword in keywords):
                features[f"duration_{duration}"] = True
        
        return features
    
    def _extract_semantic_features(self, text: str, doc_features: DocumentFeatures) -> Dict[str, Any]:
        """Extract semantic features that preserve meaning without revealing content."""
        
        features = {}
        
        # Topic coherence (how focused the document is)
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 1:
            # Simple topic coherence based on word overlap between sentences
            word_sets = [set(sentence.lower().split()) for sentence in sentences if sentence.strip()]
            if len(word_sets) > 1:
                overlaps = []
                for i in range(len(word_sets) - 1):
                    if word_sets[i] and word_sets[i + 1]:
                        overlap = len(word_sets[i] & word_sets[i + 1]) / len(word_sets[i] | word_sets[i + 1])
                        overlaps.append(overlap)
                
                if overlaps:
                    features["topic_coherence"] = np.mean(overlaps)
        
        # Emotional content indicators
        emotional_indicators = {
            "positive_emotion": ["happy", "joy", "excitement", "satisfaction", "pleasure"],
            "negative_emotion": ["sad", "anger", "fear", "disappointment", "frustration"],
            "neutral_emotion": ["calm", "neutral", "balanced", "stable", "steady"]
        }
        
        for emotion, keywords in emotional_indicators.items():
            count = sum(text.lower().count(keyword) for keyword in keywords)
            if count > 0:
                features[f"emotion_{emotion}"] = count
        
        # Formality indicators
        formality_indicators = {
            "formal": ["therefore", "consequently", "furthermore", "moreover", "thus"],
            "informal": ["hey", "cool", "awesome", "great", "nice"],
            "technical": ["algorithm", "protocol", "framework", "architecture", "implementation"]
        }
        
        for formality, keywords in formality_indicators.items():
            count = sum(text.lower().count(keyword) for keyword in keywords)
            if count > 0:
                features[f"formality_{formality}"] = count
        
        return features
    
    def _bin_amount(self, amount: int) -> str:
        """Bin monetary amounts for privacy."""
        if amount < 100:
            return "0-100"
        elif amount < 500:
            return "100-500"
        elif amount < 1000:
            return "500-1000"
        elif amount < 5000:
            return "1000-5000"
        else:
            return "5000+"
    
    def _apply_privacy_constraints(self, features: Dict[str, Any], doc_type: DocumentType) -> Dict[str, Any]:
        """Apply privacy constraints based on document type."""
        
        # Round numerical values based on privacy level
        privacy_levels = {
            DocumentType.MEDICAL: 0,      # No decimal precision
            DocumentType.FINANCIAL: 0,    # No decimal precision
            DocumentType.PERSONAL: 0,     # No decimal precision
            DocumentType.LEGAL: 0,        # No decimal precision
            DocumentType.BUSINESS: 1,     # 1 decimal place
            DocumentType.TECHNICAL: 2,    # 2 decimal places
            DocumentType.GENERAL: 3       # 3 decimal places
        }
        
        max_precision = privacy_levels.get(doc_type, 3)
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                if max_precision == 0:
                    features[key] = int(round(value))
                else:
                    features[key] = round(value, max_precision)
        
        return features
    
    def _calculate_privacy_score(self, original_text: str, *feature_dicts) -> float:
        """Calculate privacy score based on feature extraction safety."""
        
        # Check for exact text matches in features
        exact_matches = 0
        total_features = 0
        
        for feature_dict in feature_dicts:
            for feature_name, feature_value in feature_dict.items():
                total_features += 1
                if isinstance(feature_value, str):
                    # Check if feature value contains exact text from original
                    if feature_value in original_text:
                        exact_matches += 1
        
        # Privacy score: 0-1, higher = more private
        if total_features == 0:
            return 1.0
        
        privacy_score = 1.0 - (exact_matches / total_features)
        return max(0.0, min(1.0, privacy_score))
    
    def validate_features(self, original_text: str, extracted_features: ExtractedFeatures) -> Tuple[bool, List[str]]:
        """
        Validate that extracted features are safe and don't reveal sensitive information.
        
        Args:
            original_text: Original text content
            extracted_features: Extracted features to validate
            
        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        
        violations = []
        
        # Check all feature dictionaries
        feature_dicts = [
            extracted_features.statistical_features,
            extracted_features.categorical_features,
            extracted_features.temporal_features,
            extracted_features.semantic_features
        ]
        
        for feature_dict in feature_dicts:
            for feature_name, feature_value in feature_dict.items():
                if isinstance(feature_value, str):
                    # Check for exact text matches
                    if feature_value in original_text:
                        violations.append(f"Feature '{feature_name}' contains exact text from original")
                    
                    # Check for sensitive patterns
                    sensitive_patterns = [
                        (r'\$\d+', 'monetary_amount'),
                        (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
                        (r'\b[A-Za-z]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
                        (r'\b\d{3}-\d{3}-\d{4}\b', 'phone')
                    ]
                    
                    for pattern, pattern_type in sensitive_patterns:
                        if re.search(pattern, str(feature_value), re.IGNORECASE):
                            violations.append(f"Feature '{feature_name}' contains {pattern_type}")
        
        is_safe = len(violations) == 0
        return is_safe, violations
