"""
Complete Privacy Pipeline for End-to-End Privacy-Preserving AI.
This system orchestrates all privacy components to provide a seamless
privacy-preserving AI experience.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import uuid

from utils.privacy_classifier import PrivacyAwareClassifier, DocumentType, DocumentFeatures
from utils.feature_extractor import PrivacyAwareFeatureExtractor, ExtractedFeatures
from utils.embedding_generator import LocalEmbeddingGenerator, EmbeddingResult
from utils.synthetic_generator import SyntheticDataGenerator, SyntheticDataResult
from utils.privacy_budget import PrivacyBudgetManager, PrivacyLevel, get_privacy_budget
from utils.differential_privacy import add_differential_privacy
from utils.secure_memory import track_for_cleanup, cleanup_all_tracked
from compute.privacy_preserving_inference import PrivacyPreservingInference, ExternalModelResponse

logger = logging.getLogger(__name__)

@dataclass
class PrivacyPipelineResult:
    """Complete result of privacy pipeline processing."""
    pipeline_id: str
    user_id: str
    document_features: DocumentFeatures
    extracted_features: ExtractedFeatures
    embeddings: Optional[EmbeddingResult]
    synthetic_data: Optional[SyntheticDataResult]
    external_response: Optional[ExternalModelResponse]
    privacy_metrics: Dict[str, float]
    processing_metadata: Dict[str, Any]

class PrivacyPipeline:
    """Orchestrates the complete privacy-preserving AI pipeline."""
    
    def __init__(self):
        """Initialize the privacy pipeline with all components."""
        
        # Initialize all privacy components
        self.classifier = PrivacyAwareClassifier()
        self.feature_extractor = PrivacyAwareFeatureExtractor()
        self.embedding_generator = LocalEmbeddingGenerator()
        self.synthetic_generator = SyntheticDataGenerator()
        self.privacy_budget_manager = PrivacyBudgetManager()
        self.external_inference = PrivacyPreservingInference()
        
        logger.info("Privacy pipeline initialized with all components")
    
    def process_documents(self, 
                         user_id: str,
                         documents: List[str],
                         privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM,
                         use_embeddings: bool = True,
                         use_synthetic_data: bool = False,
                         use_external_ai: bool = True,
                         external_model_provider: str = "replicate") -> PrivacyPipelineResult:
        """
        Process documents through the complete privacy pipeline.
        
        Args:
            user_id: User identifier for privacy budget tracking
            documents: List of document texts to process
            privacy_level: Required privacy level
            use_embeddings: Whether to generate semantic embeddings
            use_synthetic_data: Whether to generate synthetic data
            use_external_ai: Whether to use external AI models
            external_model_provider: External AI provider to use
            
        Returns:
            PrivacyPipelineResult with complete processing results
        """
        
        pipeline_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Starting privacy pipeline {pipeline_id} for user {user_id}")
        
        try:
            # Track all sensitive objects for cleanup
            sensitive_objects = []
            
            # Step 1: Document Classification
            logger.info("Step 1: Document Classification")
            document_features = self._classify_documents(documents)
            sensitive_objects.append(document_features)
            
            # Step 2: Feature Extraction
            logger.info("Step 2: Feature Extraction")
            extracted_features = self._extract_features(documents, document_features)
            sensitive_objects.append(extracted_features)
            
            # Step 3: Embedding Generation (Optional)
            embeddings = None
            if use_embeddings:
                logger.info("Step 3: Embedding Generation")
                embeddings = self._generate_embeddings(documents, privacy_level)
                sensitive_objects.append(embeddings)
            
            # Step 4: Synthetic Data Generation (Optional)
            synthetic_data = None
            if use_synthetic_data:
                logger.info("Step 4: Synthetic Data Generation")
                synthetic_data = self._generate_synthetic_data(documents, privacy_level)
                sensitive_objects.append(synthetic_data)
            
            # Step 5: External AI Processing (Optional)
            external_response = None
            if use_external_ai:
                logger.info("Step 5: External AI Processing")
                external_response = self._process_with_external_ai(
                    user_id, document_features, extracted_features, 
                    embeddings, synthetic_data, privacy_level, external_model_provider
                )
                sensitive_objects.append(external_response)
            
            # Step 6: Calculate Privacy Metrics
            logger.info("Step 6: Privacy Metrics Calculation")
            privacy_metrics = self._calculate_privacy_metrics(
                document_features, extracted_features, embeddings, synthetic_data, external_response
            )
            
            # Step 7: Create Processing Metadata
            processing_metadata = self._create_processing_metadata(
                pipeline_id, start_time, documents, privacy_level,
                use_embeddings, use_synthetic_data, use_external_ai
            )
            
            # Create result
            result = PrivacyPipelineResult(
                pipeline_id=pipeline_id,
                user_id=user_id,
                document_features=document_features,
                extracted_features=extracted_features,
                embeddings=embeddings,
                synthetic_data=synthetic_data,
                external_response=external_response,
                privacy_metrics=privacy_metrics,
                processing_metadata=processing_metadata
            )
            
            logger.info(f"Privacy pipeline {pipeline_id} completed successfully")
            
            # Secure cleanup
            self._secure_cleanup(sensitive_objects)
            
            return result
            
        except Exception as e:
            logger.error(f"Privacy pipeline {pipeline_id} failed: {e}")
            # Clean up on failure
            self._secure_cleanup([])
            raise
    
    def _classify_documents(self, documents: List[str]) -> DocumentFeatures:
        """Classify documents and determine privacy requirements."""
        
        if not documents:
            raise ValueError("Documents list cannot be empty")
        
        # Classify the first document (assuming similar documents in batch)
        # In production, you'd classify each document individually
        primary_document = documents[0]
        document_features = self.classifier.classify_document(primary_document)
        
        logger.info(f"Document classified as {document_features.document_type.value} with risk level {document_features.risk_level}")
        
        return document_features
    
    def _extract_features(self, documents: List[str], 
                         document_features: DocumentFeatures) -> ExtractedFeatures:
        """Extract safe features from documents."""
        
        # Extract features from the primary document
        primary_document = documents[0]
        extracted_features = self.feature_extractor.extract_features(
            primary_document, document_features
        )
        
        logger.info(f"Extracted {len(extracted_features.statistical_features)} statistical features")
        logger.info(f"Privacy score: {extracted_features.privacy_score:.2f}")
        
        return extracted_features
    
    def _generate_embeddings(self, documents: List[str], 
                            privacy_level: PrivacyLevel) -> EmbeddingResult:
        """Generate semantic embeddings with privacy protection."""
        
        embeddings = self.embedding_generator.generate_embeddings(
            documents, privacy_level=privacy_level.value
        )
        
        logger.info(f"Generated embeddings: {embeddings.embeddings.shape}")
        logger.info(f"Semantic coherence: {embeddings.semantic_coherence:.3f}")
        logger.info(f"Privacy score: {embeddings.privacy_score:.2f}")
        
        return embeddings
    
    def _generate_synthetic_data(self, documents: List[str], 
                               privacy_level: PrivacyLevel) -> SyntheticDataResult:
        """Generate synthetic data preserving statistical properties."""
        
        synthetic_data = self.synthetic_generator.generate_synthetic_text(
            documents, privacy_level=privacy_level.value
        )
        
        logger.info(f"Generated synthetic data for {len(documents)} documents")
        logger.info(f"Quality score: {synthetic_data.quality_metrics.get('overall_quality', 0.0):.2f}")
        logger.info(f"Privacy score: {synthetic_data.privacy_metrics.get('privacy_score', 0.0):.2f}")
        
        return synthetic_data
    
    def _process_with_external_ai(self, user_id: str, 
                                 document_features: DocumentFeatures,
                                 extracted_features: ExtractedFeatures,
                                 embeddings: Optional[EmbeddingResult],
                                 synthetic_data: Optional[SyntheticDataResult],
                                 privacy_level: PrivacyLevel,
                                 model_provider: str) -> ExternalModelResponse:
        """Process data with external AI model using privacy-preserving techniques."""
        
        external_response = self.external_inference.process_with_external_model(
            user_id=user_id,
            document_features=document_features,
            extracted_features=extracted_features,
            embeddings=embeddings,
            synthetic_data=synthetic_data,
            privacy_level=privacy_level,
            model_provider=model_provider
        )
        
        logger.info(f"External AI processing completed with {model_provider}")
        logger.info(f"Response length: {len(external_response.processed_response)}")
        
        return external_response
    
    def _calculate_privacy_metrics(self, 
                                 document_features: DocumentFeatures,
                                 extracted_features: ExtractedFeatures,
                                 embeddings: Optional[EmbeddingResult],
                                 synthetic_data: Optional[SyntheticDataResult],
                                 external_response: Optional[ExternalModelResponse]) -> Dict[str, float]:
        """Calculate comprehensive privacy metrics."""
        
        metrics = {
            "overall_privacy_score": 0.0,
            "document_classification_confidence": document_features.confidence_score,
            "feature_extraction_privacy": extracted_features.privacy_score,
            "risk_level_score": self._risk_level_to_score(document_features.risk_level),
            "total_components": 0,
            "privacy_component_scores": {}
        }
        
        # Feature extraction privacy
        metrics["privacy_component_scores"]["feature_extraction"] = extracted_features.privacy_score
        metrics["total_components"] += 1
        
        # Embedding privacy
        if embeddings:
            metrics["privacy_component_scores"]["embeddings"] = embeddings.privacy_score
            metrics["total_components"] += 1
        
        # Synthetic data privacy
        if synthetic_data:
            metrics["privacy_component_scores"]["synthetic_data"] = synthetic_data.privacy_metrics.get("privacy_score", 0.0)
            metrics["total_components"] += 1
        
        # External AI privacy
        if external_response:
            metrics["privacy_component_scores"]["external_ai"] = external_response.privacy_score
            metrics["total_components"] += 1
        
        # Calculate overall privacy score
        if metrics["total_components"] > 0:
            component_scores = list(metrics["privacy_component_scores"].values())
            metrics["overall_privacy_score"] = sum(component_scores) / len(component_scores)
        
        return metrics
    
    def _risk_level_to_score(self, risk_level: str) -> float:
        """Convert risk level to numerical score."""
        
        risk_scores = {
            "critical": 0.2,  # Low score for high risk
            "high": 0.4,
            "medium": 0.6,
            "low": 0.8
        }
        
        return risk_scores.get(risk_level, 0.5)
    
    def _create_processing_metadata(self, pipeline_id: str, start_time: float,
                                  documents: List[str], privacy_level: PrivacyLevel,
                                  use_embeddings: bool, use_synthetic_data: bool,
                                  use_external_ai: bool) -> Dict[str, Any]:
        """Create comprehensive processing metadata."""
        
        end_time = time.time()
        
        return {
            "pipeline_id": pipeline_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_processing_time": end_time - start_time,
            "document_count": len(documents),
            "privacy_level": privacy_level.value,
            "components_used": {
                "document_classification": True,
                "feature_extraction": True,
                "embeddings": use_embeddings,
                "synthetic_data": use_synthetic_data,
                "external_ai": use_external_ai
            },
            "timestamp": time.time()
        }
    
    def _secure_cleanup(self, sensitive_objects: List[Any]) -> None:
        """Securely clean up sensitive data."""
        
        try:
            # Track objects for cleanup
            for obj in sensitive_objects:
                if obj:
                    track_for_cleanup(obj, f"pipeline_cleanup_{id(obj)}")
            
            # Perform cleanup
            cleanup_all_tracked()
            
        except Exception as e:
            logger.warning(f"Secure cleanup failed: {e}")
    
    def get_pipeline_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of privacy pipeline operations."""
        
        # Get privacy budget summary
        if user_id:
            budget_summary = self.privacy_budget_manager.get_budget_summary(user_id)
        else:
            budget_summary = self.privacy_budget_manager.get_global_statistics()
        
        # Get external AI audit summary
        audit_summary = self.external_inference.get_audit_summary(user_id)
        
        return {
            "privacy_budget": budget_summary,
            "external_ai_audit": audit_summary,
            "pipeline_status": "active",
            "components": {
                "classifier": "active",
                "feature_extractor": "active",
                "embedding_generator": "active",
                "synthetic_generator": "active",
                "external_inference": "active"
            }
        }
    
    def validate_privacy_guarantees(self, result: PrivacyPipelineResult) -> Tuple[bool, List[str]]:
        """Validate that privacy guarantees are maintained."""
        
        violations = []
        
        # Check overall privacy score
        if result.privacy_metrics["overall_privacy_score"] < 0.7:
            violations.append("Overall privacy score below threshold (0.7)")
        
        # Check feature extraction privacy
        if result.extracted_features.privacy_score < 0.8:
            violations.append("Feature extraction privacy below threshold (0.8)")
        
        # Check embeddings privacy if used
        if result.embeddings and result.embeddings.privacy_score < 0.7:
            violations.append("Embedding privacy below threshold (0.7)")
        
        # Check synthetic data privacy if used
        if result.synthetic_data:
            synth_privacy = result.synthetic_data.privacy_metrics.get("privacy_score", 0.0)
            if synth_privacy < 0.8:
                violations.append("Synthetic data privacy below threshold (0.8)")
        
        # Check external AI privacy if used
        if result.external_response and result.external_response.privacy_score < 0.6:
            violations.append("External AI privacy below threshold (0.6)")
        
        is_valid = len(violations) == 0
        return is_valid, violations

# Global instance
privacy_pipeline = PrivacyPipeline()

# Convenience functions
def process_documents_privacy(user_id: str, documents: List[str], **kwargs) -> PrivacyPipelineResult:
    """Process documents through the complete privacy pipeline."""
    return privacy_pipeline.process_documents(user_id, documents, **kwargs)

def get_pipeline_summary(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get summary of privacy pipeline operations."""
    return privacy_pipeline.get_pipeline_summary(user_id)

def validate_privacy_guarantees(result: PrivacyPipelineResult) -> Tuple[bool, List[str]]:
    """Validate that privacy guarantees are maintained."""
    return privacy_pipeline.validate_privacy_guarantees(result)
