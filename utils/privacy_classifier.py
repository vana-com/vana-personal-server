"""
Document Classification System for Privacy-Preserving Feature Extraction.
This system identifies document types and determines which features are safe to extract.
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
import os

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Supported document types for privacy-aware processing."""
    FINANCIAL = "financial"
    MEDICAL = "medical"
    PERSONAL = "personal"
    BUSINESS = "business"
    LEGAL = "legal"
    TECHNICAL = "technical"
    GENERAL = "general"

@dataclass
class DocumentFeatures:
    """Safe features that can be extracted from documents."""
    document_type: DocumentType
    confidence_score: float
    word_count: int
    sentence_count: int
    language: str
    complexity_score: float
    topic_distribution: Dict[str, float]
    sentiment_polarity: float
    reading_level: str
    safe_categories: List[str]
    risk_level: str

@dataclass
class ExtractionRules:
    """Rules for safe feature extraction based on document type."""
    allowed_features: List[str]
    forbidden_patterns: List[str]
    privacy_level: str
    max_precision: int
    anonymization_required: bool

class PrivacyAwareClassifier:
    """Document classifier that determines safe feature extraction strategies."""
    
    def __init__(self):
        self.classifier = None
        self.vectorizer = None
        self.feature_rules = self._initialize_feature_rules()
        self.sensitive_patterns = self._initialize_sensitive_patterns()
        
    def _initialize_feature_rules(self) -> Dict[DocumentType, ExtractionRules]:
        """Initialize feature extraction rules for each document type."""
        
        return {
            DocumentType.FINANCIAL: ExtractionRules(
                allowed_features=[
                    "transaction_count", "spending_categories", "account_types",
                    "temporal_patterns", "amount_ranges", "merchant_categories"
                ],
                forbidden_patterns=[
                    r'\$\d+\.\d{2}',  # Exact dollar amounts
                    r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card numbers
                    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                    r'account\s+#?\d+',  # Account numbers
                ],
                privacy_level="high",
                max_precision=0,  # No decimal precision for amounts
                anonymization_required=True
            ),
            
            DocumentType.MEDICAL: ExtractionRules(
                allowed_features=[
                    "symptom_categories", "treatment_types", "medication_classes",
                    "diagnosis_categories", "visit_frequency", "specialist_types"
                ],
                forbidden_patterns=[
                    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                    r'\b[A-Z]{2}\d{6}\b',  # Medical record numbers
                    r'patient\s+name',  # Patient identifiers
                    r'date\s+of\s+birth',  # DOB
                ],
                privacy_level="critical",
                max_precision=0,
                anonymization_required=True
            ),
            
            DocumentType.PERSONAL: ExtractionRules(
                allowed_features=[
                    "communication_patterns", "relationship_types", "interest_categories",
                    "activity_patterns", "preference_categories", "temporal_rhythms"
                ],
                forbidden_patterns=[
                    r'\b[A-Za-z]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
                    r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
                    r'address',  # Addresses
                    r'birthday',  # Birth dates
                ],
                privacy_level="high",
                max_precision=0,
                anonymization_required=True
            ),
            
            DocumentType.BUSINESS: ExtractionRules(
                allowed_features=[
                    "industry_categories", "company_size_ranges", "revenue_ranges",
                    "employee_count_ranges", "market_segments", "business_models"
                ],
                forbidden_patterns=[
                    r'revenue\s*:\s*\$\d+',  # Exact revenue figures
                    r'employees\s*:\s*\d+',  # Exact employee counts
                    r'customer\s+names',  # Customer identifiers
                    r'contract\s+values',  # Contract amounts
                ],
                privacy_level="medium",
                max_precision=1,
                anonymization_required=False
            ),
            
            DocumentType.LEGAL: ExtractionRules(
                allowed_features=[
                    "case_types", "legal_areas", "document_categories",
                    "procedural_elements", "jurisdiction_types", "outcome_categories"
                ],
                forbidden_patterns=[
                    r'case\s+number',  # Case identifiers
                    r'client\s+name',  # Client names
                    r'court\s+details',  # Specific court information
                    r'confidential',  # Confidentiality markers
                ],
                privacy_level="high",
                max_precision=0,
                anonymization_required=True
            ),
            
            DocumentType.TECHNICAL: ExtractionRules(
                allowed_features=[
                    "technology_categories", "complexity_levels", "domain_areas",
                    "implementation_patterns", "architecture_types", "performance_metrics"
                ],
                forbidden_patterns=[
                    r'api\s+keys',  # API credentials
                    r'passwords',  # Passwords
                    r'ip\s+addresses',  # IP addresses
                    r'hostnames',  # Server names
                ],
                privacy_level="medium",
                max_precision=2,
                anonymization_required=False
            ),
            
            DocumentType.GENERAL: ExtractionRules(
                allowed_features=[
                    "content_categories", "writing_style", "complexity_metrics",
                    "language_features", "structural_elements", "thematic_content"
                ],
                forbidden_patterns=[
                    r'personal\s+identifiers',  # Any personal info
                    r'confidential\s+information',  # Confidential markers
                    r'sensitive\s+data',  # Sensitivity indicators
                ],
                privacy_level="low",
                max_precision=3,
                anonymization_required=False
            )
        }
    
    def _initialize_sensitive_patterns(self) -> List[Tuple[str, str]]:
        """Initialize patterns for detecting sensitive information."""
        
        return [
            # Financial patterns
            (r'\$\d+\.\d{2}', 'exact_amount'),
            (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'credit_card'),
            (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
            (r'account\s+#?\d+', 'account_number'),
            
            # Personal identifiers
            (r'\b[A-Za-z]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
            (r'\b\d{3}-\d{3}-\d{4}\b', 'phone'),
            (r'address\s*:', 'address'),
            (r'birthday\s*:', 'birth_date'),
            
            # Medical patterns
            (r'\b[A-Z]{2}\d{6}\b', 'medical_record'),
            (r'patient\s+name', 'patient_id'),
            (r'diagnosis\s*:', 'diagnosis'),
            
            # Technical patterns
            (r'api\s+key', 'api_credential'),
            (r'password', 'credential'),
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'ip_address'),
        ]
    
    def classify_document(self, text: str) -> DocumentFeatures:
        """
        Classify a document and determine safe feature extraction strategy.
        
        Args:
            text: Document text to classify
            
        Returns:
            DocumentFeatures with classification and safe extraction rules
        """
        
        # Basic text analysis
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))
        language = self._detect_language(text)
        complexity_score = self._calculate_complexity(text)
        reading_level = self._determine_reading_level(complexity_score)
        
        # Document type classification
        doc_type, confidence = self._classify_document_type(text)
        
        # Topic analysis
        topic_distribution = self._extract_topic_distribution(text)
        
        # Sentiment analysis
        sentiment_polarity = self._analyze_sentiment(text)
        
        # Risk assessment
        risk_level = self._assess_risk_level(text, doc_type)
        
        # Safe categories based on document type
        safe_categories = self._get_safe_categories(doc_type, text)
        
        return DocumentFeatures(
            document_type=doc_type,
            confidence_score=confidence,
            word_count=word_count,
            sentence_count=sentence_count,
            language=language,
            complexity_score=complexity_score,
            topic_distribution=topic_distribution,
            sentiment_polarity=sentiment_polarity,
            reading_level=reading_level,
            safe_categories=safe_categories,
            risk_level=risk_level
        )
    
    def _classify_document_type(self, text: str) -> Tuple[DocumentType, float]:
        """Classify document type using keyword analysis and ML."""
        
        # Simple keyword-based classification first
        text_lower = text.lower()
        
        # Financial indicators
        financial_score = sum([
            text_lower.count('bank'), text_lower.count('account'),
            text_lower.count('transaction'), text_lower.count('balance'),
            text_lower.count('payment'), text_lower.count('credit'),
            text_lower.count('debit'), text_lower.count('statement')
        ])
        
        # Medical indicators
        medical_score = sum([
            text_lower.count('patient'), text_lower.count('diagnosis'),
            text_lower.count('treatment'), text_lower.count('symptom'),
            text_lower.count('medication'), text_lower.count('doctor'),
            text_lower.count('hospital'), text_lower.count('medical')
        ])
        
        # Personal indicators
        personal_score = sum([
            text_lower.count('family'), text_lower.count('friend'),
            text_lower.count('relationship'), text_lower.count('personal'),
            text_lower.count('private'), text_lower.count('confidential')
        ])
        
        # Business indicators
        business_score = sum([
            text_lower.count('company'), text_lower.count('business'),
            text_lower.count('corporate'), text_lower.count('revenue'),
            text_lower.count('profit'), text_lower.count('market'),
            text_lower.count('customer'), text_lower.count('product')
        ])
        
        # Legal indicators
        legal_score = sum([
            text_lower.count('legal'), text_lower.count('court'),
            text_lower.count('case'), text_lower.count('law'),
            text_lower.count('attorney'), text_lower.count('judge'),
            text_lower.count('contract'), text_lower.count('agreement')
        ])
        
        # Technical indicators
        technical_score = sum([
            text_lower.count('technology'), text_lower.count('software'),
            text_lower.count('code'), text_lower.count('system'),
            text_lower.count('database'), text_lower.count('api'),
            text_lower.count('server'), text_lower.count('network')
        ])
        
        # Determine highest scoring type
        scores = {
            DocumentType.FINANCIAL: financial_score,
            DocumentType.MEDICAL: medical_score,
            DocumentType.PERSONAL: personal_score,
            DocumentType.BUSINESS: business_score,
            DocumentType.LEGAL: legal_score,
            DocumentType.TECHNICAL: technical_score
        }
        
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        # Calculate confidence based on score dominance
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.0
        
        # Default to general if no clear classification
        if confidence < 0.3:
            return DocumentType.GENERAL, confidence
        
        return max_type, confidence
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        # Basic English detection
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(re.findall(r'[a-zA-Z0-9]', text))
        
        if total_chars == 0:
            return "unknown"
        
        english_ratio = english_chars / total_chars
        return "en" if english_ratio > 0.7 else "unknown"
    
    def _calculate_complexity(self, text: str) -> float:
        """Calculate text complexity score."""
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        long_words = len([w for w in words if len(w) > 6])
        long_word_ratio = long_words / len(words) if words else 0
        
        # Complexity score: 0-1, higher = more complex
        complexity = (avg_sentence_length / 20.0 + long_word_ratio) / 2.0
        return min(1.0, max(0.0, complexity))
    
    def _determine_reading_level(self, complexity: float) -> str:
        """Determine reading level based on complexity score."""
        if complexity < 0.3:
            return "elementary"
        elif complexity < 0.5:
            return "middle_school"
        elif complexity < 0.7:
            return "high_school"
        elif complexity < 0.9:
            return "college"
        else:
            return "academic"
    
    def _extract_topic_distribution(self, text: str) -> Dict[str, float]:
        """Extract topic distribution using keyword analysis."""
        text_lower = text.lower()
        
        topics = {
            "finance": ["money", "bank", "account", "transaction", "payment"],
            "health": ["health", "medical", "doctor", "patient", "treatment"],
            "technology": ["computer", "software", "system", "data", "network"],
            "business": ["company", "business", "market", "customer", "product"],
            "legal": ["law", "legal", "court", "case", "contract"],
            "personal": ["family", "friend", "relationship", "personal", "private"]
        }
        
        topic_scores = {}
        for topic, keywords in topics.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            topic_scores[topic] = score
        
        # Normalize scores
        total_score = sum(topic_scores.values())
        if total_score > 0:
            topic_scores = {k: v/total_score for k, v in topic_scores.items()}
        
        return topic_scores
    
    def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis."""
        positive_words = ["good", "great", "excellent", "positive", "happy", "success"]
        negative_words = ["bad", "terrible", "awful", "negative", "sad", "failure"]
        
        text_lower = text.lower()
        positive_count = sum(text_lower.count(word) for word in positive_words)
        negative_count = sum(text_lower.count(word) for word in negative_words)
        
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        # Sentiment score: -1 to 1, negative to positive
        sentiment = (positive_count - negative_count) / total_words
        return max(-1.0, min(1.0, sentiment))
    
    def _assess_risk_level(self, text: str, doc_type: DocumentType) -> str:
        """Assess privacy risk level of the document."""
        
        # Count sensitive patterns
        sensitive_count = 0
        for pattern, pattern_type in self.sensitive_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            sensitive_count += matches
        
        # Base risk on document type and sensitive content
        base_risk = {
            DocumentType.MEDICAL: "critical",
            DocumentType.FINANCIAL: "high",
            DocumentType.PERSONAL: "high",
            DocumentType.LEGAL: "high",
            DocumentType.BUSINESS: "medium",
            DocumentType.TECHNICAL: "medium",
            DocumentType.GENERAL: "low"
        }
        
        base_risk_level = base_risk.get(doc_type, "medium")
        
        # Escalate risk if sensitive patterns found
        if sensitive_count > 5:
            if base_risk_level == "low":
                return "medium"
            elif base_risk_level == "medium":
                return "high"
            else:
                return "critical"
        
        return base_risk_level
    
    def _get_safe_categories(self, doc_type: DocumentType, text: str) -> List[str]:
        """Get safe categories that can be extracted based on document type."""
        rules = self.feature_rules.get(doc_type)
        if not rules:
            return []
        
        # Filter out forbidden patterns
        safe_categories = []
        for category in rules.allowed_features:
            # Check if category is safe to extract
            if not self._contains_forbidden_patterns(text, category, rules):
                safe_categories.append(category)
        
        return safe_categories
    
    def _contains_forbidden_patterns(self, text: str, category: str, rules: ExtractionRules) -> bool:
        """Check if text contains forbidden patterns for a category."""
        for pattern in rules.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def get_extraction_rules(self, doc_type: DocumentType) -> ExtractionRules:
        """Get extraction rules for a document type."""
        return self.feature_rules.get(doc_type, self.feature_rules[DocumentType.GENERAL])
    
    def validate_extraction_safety(self, text: str, features: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that extracted features are safe and don't reveal sensitive information.
        
        Args:
            text: Original text
            features: Extracted features to validate
            
        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        violations = []
        
        # Check for exact matches that could reveal original content
        for feature_name, feature_value in features.items():
            if isinstance(feature_value, str):
                # Check if feature value appears in original text
                if feature_value in text:
                    violations.append(f"Feature '{feature_name}' contains exact text from original")
                
                # Check for sensitive patterns in feature values
                for pattern, pattern_type in self.sensitive_patterns:
                    if re.search(pattern, str(feature_value), re.IGNORECASE):
                        violations.append(f"Feature '{feature_name}' contains {pattern_type} pattern")
        
        is_safe = len(violations) == 0
        return is_safe, violations
