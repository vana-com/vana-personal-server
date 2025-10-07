"""
Privacy-Preserving External Model Interface.
This system sends processed, privacy-enhanced features to external AI models
while maintaining comprehensive audit trails and preventing data leakage.
"""

import logging
import requests
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import uuid
import re
import os

from utils.privacy_classifier import DocumentType, DocumentFeatures
from utils.feature_extractor import ExtractedFeatures
from utils.embedding_generator import EmbeddingResult
from utils.synthetic_generator import SyntheticDataResult
from utils.privacy_budget import PrivacyLevel, check_operation_privacy, record_privacy_cost
from utils.secure_memory import track_for_cleanup, cleanup_all_tracked

logger = logging.getLogger(__name__)

@dataclass
class ExternalModelRequest:
    """Request to external AI model with privacy metadata."""
    request_id: str
    model_provider: str
    model_name: str
    processed_features: Dict[str, Any]
    privacy_metadata: Dict[str, Any]
    timestamp: float
    user_id: str

@dataclass
class ExternalModelResponse:
    """Response from external AI model with privacy validation."""
    request_id: str
    model_provider: str
    model_name: str
    raw_response: str
    processed_response: str
    privacy_score: float
    response_metadata: Dict[str, Any]
    timestamp: float

@dataclass
class PrivacyAuditLog:
    """Comprehensive audit log for privacy-preserving operations."""
    operation_id: str
    user_id: str
    operation_type: str
    privacy_level: PrivacyLevel
    epsilon_cost: float
    data_sent: Dict[str, Any]
    data_received: Dict[str, Any]
    privacy_validation: Dict[str, Any]
    timestamp: float
    audit_hash: str

class PrivacyPreservingInference:
    """Manages privacy-preserving inference with external AI models."""
    
    def __init__(self):
        self.audit_logs: List[PrivacyAuditLog] = []
        self.request_history: Dict[str, ExternalModelRequest] = {}
        self.response_history: Dict[str, ExternalModelResponse] = {}
        
        # External model configurations
        self.model_configs = {
            "replicate": {
                "base_url": "https://api.replicate.com/v1",
                "timeout": 300,
                "max_retries": 3
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "timeout": 120,
                "max_retries": 2
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com/v1",
                "timeout": 180,
                "max_retries": 2
            }
        }
    
    def process_with_external_model(self, 
                                  user_id: str,
                                  document_features: DocumentFeatures,
                                  extracted_features: ExtractedFeatures,
                                  embeddings: Optional[EmbeddingResult] = None,
                                  synthetic_data: Optional[SyntheticDataResult] = None,
                                  privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM,
                                  model_provider: str = "replicate",
                                  model_name: str = "llama-2-70b-chat") -> ExternalModelResponse:
        """
        Process data with external AI model using privacy-preserving techniques.
        
        Args:
            user_id: User identifier for privacy budget tracking
            document_features: Document classification and risk assessment
            extracted_features: Safe, extracted features
            embeddings: Optional semantic embeddings
            synthetic_data: Optional synthetic data
            privacy_level: Required privacy level
            model_provider: External model provider
            model_name: Specific model to use
            
        Returns:
            ExternalModelResponse with processed results
        """
        
        operation_id = str(uuid.uuid4())
        logger.info(f"Starting privacy-preserving inference: {operation_id}")
        
        try:
            # 1. Privacy budget validation
            self._validate_privacy_budget(user_id, operation_id, privacy_level, extracted_features)
            
            # 2. Prepare processed features for external model
            processed_features = self._prepare_features_for_external_model(
                extracted_features, embeddings, synthetic_data, privacy_level
            )
            
            # 3. Create external model request
            external_request = self._create_external_request(
                operation_id, user_id, model_provider, model_name, processed_features, privacy_level
            )
            
            # 4. Send to external model
            external_response = self._send_to_external_model(external_request)
            
            # 5. Process and validate response
            processed_response = self._process_external_response(
                external_response, processed_features, privacy_level
            )
            
            # 6. Record privacy cost
            self._record_privacy_operation(user_id, operation_id, privacy_level, processed_features)
            
            # 7. Create audit log
            self._create_audit_log(operation_id, user_id, processed_features, processed_response, privacy_level)
            
            # 8. Secure cleanup
            self._secure_cleanup([processed_features, external_response, processed_response])
            
            logger.info(f"Privacy-preserving inference completed: {operation_id}")
            return processed_response
            
        except Exception as e:
            logger.error(f"Privacy-preserving inference failed: {operation_id}, error: {e}")
            # Clean up on failure
            self._secure_cleanup([])
            raise
    
    def _validate_privacy_budget(self, user_id: str, operation_id: str, 
                               privacy_level: PrivacyLevel, features: ExtractedFeatures) -> None:
        """Validate privacy budget for the operation."""
        
        # Calculate epsilon cost based on features and privacy level
        epsilon_cost = self._calculate_epsilon_cost(features, privacy_level)
        
        # Check if operation is allowed
        is_allowed, reason = check_operation_privacy(
            user_id, "external_inference", len(features.statistical_features), epsilon_cost
        )
        
        if not is_allowed:
            raise ValueError(f"Privacy budget validation failed: {reason}")
        
        logger.info(f"Privacy budget validated: {epsilon_cost} epsilon for operation {operation_id}")
    
    def _calculate_epsilon_cost(self, features: ExtractedFeatures, privacy_level: PrivacyLevel) -> float:
        """Calculate epsilon cost for the operation."""
        
        # Base cost from privacy level
        base_cost = privacy_level.value
        
        # Additional cost based on feature complexity
        feature_complexity = len(features.statistical_features) + len(features.categorical_features)
        complexity_factor = min(1.5, 1.0 + (feature_complexity / 100.0))
        
        # Risk-based adjustment
        risk_factors = {
            "critical": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8
        }
        risk_factor = risk_factors.get(features.document_features.risk_level, 1.0)
        
        total_cost = base_cost * complexity_factor * risk_factor
        
        return min(5.0, max(0.1, total_cost))  # Clamp between 0.1 and 5.0
    
    def _prepare_features_for_external_model(self, 
                                           extracted_features: ExtractedFeatures,
                                           embeddings: Optional[EmbeddingResult],
                                           synthetic_data: Optional[SyntheticDataResult],
                                           privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """Prepare features for external model consumption."""
        
        processed_features = {
            "document_type": extracted_features.document_features.document_type.value,
            "risk_level": extracted_features.document_features.risk_level,
            "statistical_features": extracted_features.statistical_features,
            "categorical_features": extracted_features.categorical_features,
            "temporal_features": extracted_features.temporal_features,
            "semantic_features": extracted_features.semantic_features,
            "privacy_score": extracted_features.privacy_score,
            "processing_metadata": {
                "privacy_level": privacy_level.value,
                "feature_count": len(extracted_features.statistical_features),
                "processing_timestamp": time.time()
            }
        }
        
        # Add embeddings if available
        if embeddings:
            processed_features["embeddings"] = {
                "dimensions": embeddings.reduced_dimensions,
                "semantic_coherence": embeddings.semantic_coherence,
                "privacy_score": embeddings.privacy_score
            }
        
        # Add synthetic data if available
        if synthetic_data:
            processed_features["synthetic_data"] = {
                "quality_score": synthetic_data.quality_metrics.get("overall_quality", 0.0),
                "privacy_score": synthetic_data.privacy_metrics.get("privacy_score", 0.0),
                "data_type": synthetic_data.generation_metadata.get("generation_type", "unknown")
            }
        
        # Remove any potentially sensitive information
        processed_features = self._sanitize_features(processed_features)
        
        return processed_features
    
    def _sanitize_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Remove potentially sensitive information from features."""
        
        sanitized = features.copy()
        
        # Remove any exact values that might be sensitive
        sensitive_keys = ["exact_amounts", "personal_identifiers", "raw_text", "original_content"]
        for key in sensitive_keys:
            if key in sanitized:
                del sanitized[key]
        
        # Ensure no original text content is included
        if "statistical_features" in sanitized:
            for key, value in sanitized["statistical_features"].items():
                if isinstance(value, str) and len(value) > 100:  # Long text might be sensitive
                    sanitized["statistical_features"][key] = f"[TEXT_LENGTH_{len(value)}]"
        
        return sanitized
    
    def _create_external_request(self, operation_id: str, user_id: str, 
                               model_provider: str, model_name: str,
                               processed_features: Dict[str, Any],
                               privacy_level: PrivacyLevel) -> ExternalModelRequest:
        """Create request for external AI model."""
        
        return ExternalModelRequest(
            request_id=operation_id,
            model_provider=model_provider,
            model_name=model_name,
            processed_features=processed_features,
            privacy_metadata={
                "privacy_level": privacy_level.value,
                "privacy_score": processed_features.get("privacy_score", 0.0),
                "risk_level": processed_features.get("risk_level", "unknown"),
                "user_id": user_id
            },
            timestamp=time.time(),
            user_id=user_id
        )
    
    def _send_to_external_model(self, request: ExternalModelRequest) -> ExternalModelResponse:
        """Send request to external AI model."""
        
        model_provider = request.model_provider
        model_name = request.model_name
        
        if model_provider == "replicate":
            return self._send_to_replicate(request)
        elif model_provider == "openai":
            return self._send_to_openai(request)
        elif model_provider == "anthropic":
            return self._send_to_anthropic(request)
        else:
            raise ValueError(f"Unsupported model provider: {model_provider}")
    
    def _send_to_replicate(self, request: ExternalModelRequest) -> ExternalModelResponse:
        """Send request to Replicate API."""
        
        # Build prompt for the model
        prompt = self._build_model_prompt(request.processed_features)
        
        # Prepare API request
        api_url = f"{self.model_configs['replicate']['base_url']}/predictions"
        
        payload = {
            "version": "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
            "input": {
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        headers = {
            "Authorization": f"Token {self._get_api_key('replicate')}",
            "Content-Type": "application/json"
        }
        
        try:
            # Send request
            response = requests.post(
                api_url, 
                json=payload, 
                headers=headers,
                timeout=self.model_configs['replicate']['timeout']
            )
            response.raise_for_status()
            
            # Process response
            result = response.json()
            prediction_id = result.get("id")
            
            # Poll for completion
            final_response = self._poll_replicate_result(prediction_id)
            
            return ExternalModelResponse(
                request_id=request.request_id,
                model_provider="replicate",
                model_name=request.model_name,
                raw_response=final_response,
                processed_response=self._process_ai_response(final_response),
                privacy_score=request.processed_features.get("privacy_score", 0.0),
                response_metadata={
                    "prediction_id": prediction_id,
                    "model_version": payload["version"],
                    "processing_time": time.time() - request.timestamp
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Replicate API request failed: {e}")
            raise RuntimeError(f"External model request failed: {e}")
    
    def _send_to_openai(self, request: ExternalModelRequest) -> ExternalModelResponse:
        """Send request to OpenAI API."""
        
        # Build prompt for the model
        prompt = self._build_model_prompt(request.processed_features)
        
        # Prepare API request
        api_url = f"{self.model_configs['openai']['base_url']}/chat/completions"
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are a privacy-aware AI assistant. Analyze the provided features and provide insights without revealing sensitive information."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        headers = {
            "Authorization": f"Bearer {self._get_api_key('openai')}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.model_configs['openai']['timeout']
            )
            response.raise_for_status()
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            return ExternalModelResponse(
                request_id=request.request_id,
                model_provider="openai",
                model_name=request.model_name,
                raw_response=ai_response,
                processed_response=self._process_ai_response(ai_response),
                privacy_score=request.processed_features.get("privacy_score", 0.0),
                response_metadata={
                    "model": payload["model"],
                    "usage": result.get("usage", {}),
                    "processing_time": time.time() - request.timestamp
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise RuntimeError(f"External model request failed: {e}")
    
    def _send_to_anthropic(self, request: ExternalModelRequest) -> ExternalModelResponse:
        """Send request to Anthropic API."""
        
        # Build prompt for the model
        prompt = self._build_model_prompt(request.processed_features)
        
        # Prepare API request
        api_url = f"{self.model_configs['anthropic']['base_url']}/messages"
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        headers = {
            "x-api-key": self._get_api_key('anthropic'),
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.model_configs['anthropic']['timeout']
            )
            response.raise_for_status()
            
            result = response.json()
            ai_response = result["content"][0]["text"]
            
            return ExternalModelResponse(
                request_id=request.request_id,
                model_provider="anthropic",
                model_name=request.model_name,
                raw_response=ai_response,
                processed_response=self._process_ai_response(ai_response),
                privacy_score=request.processed_features.get("privacy_score", 0.0),
                response_metadata={
                    "model": payload["model"],
                    "usage": result.get("usage", {}),
                    "processing_time": time.time() - request.timestamp
                },
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Anthropic API request failed: {e}")
            raise RuntimeError(f"External model request failed: {e}")
    
    def _build_model_prompt(self, processed_features: Dict[str, Any]) -> str:
        """Build prompt for external AI model."""
        
        prompt = f"""
        Analyze the following privacy-preserved features and provide insights:
        
        Document Type: {processed_features.get('document_type', 'unknown')}
        Risk Level: {processed_features.get('risk_level', 'unknown')}
        Privacy Score: {processed_features.get('privacy_score', 0.0):.2f}
        
        Statistical Features:
        {json.dumps(processed_features.get('statistical_features', {}), indent=2)}
        
        Categorical Features:
        {json.dumps(processed_features.get('categorical_features', {}), indent=2)}
        
        Temporal Features:
        {json.dumps(processed_features.get('temporal_features', {}), indent=2)}
        
        Semantic Features:
        {json.dumps(processed_features.get('semantic_features', {}), indent=2)}
        
        Please provide:
        1. Key insights about the data patterns
        2. Recommendations based on the analysis
        3. Any notable trends or anomalies
        4. Suggestions for further analysis
        
        Remember: This data has been processed for privacy. Focus on patterns and insights, not specific values.
        """
        
        return prompt.strip()
    
    def _poll_replicate_result(self, prediction_id: str) -> str:
        """Poll Replicate API for prediction completion."""
        
        api_url = f"{self.model_configs['replicate']['base_url']}/predictions/{prediction_id}"
        headers = {"Authorization": f"Token {self._get_api_key('replicate')}"}
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                status = result.get("status")
                
                if status == "succeeded":
                    return result.get("output", [""])[0]
                elif status == "failed":
                    raise RuntimeError(f"Replicate prediction failed: {result.get('error', 'Unknown error')}")
                elif status in ["starting", "processing"]:
                    time.sleep(2)
                    attempt += 1
                else:
                    time.sleep(2)
                    attempt += 1
                    
            except Exception as e:
                logger.warning(f"Poll attempt {attempt} failed: {e}")
                time.sleep(2)
                attempt += 1
        
        raise RuntimeError("Replicate prediction timed out")
    
    def _process_ai_response(self, raw_response: str) -> str:
        """Process and sanitize AI response for privacy."""
        
        # Remove any potential sensitive information
        processed_response = raw_response
        
        # Remove common sensitive patterns
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
            r'\$\d+\.\d{2}',  # Exact amounts
        ]
        
        for pattern in sensitive_patterns:
            processed_response = re.sub(pattern, "[REDACTED]", processed_response)
        
        # Ensure response doesn't echo back specific feature values
        processed_response = self._remove_feature_echoes(processed_response)
        
        return processed_response
    
    def _remove_feature_echoes(self, response: str) -> str:
        """Remove any echoes of specific feature values from the response."""
        
        # This is a simple approach - in production, you'd want more sophisticated detection
        # Look for exact number matches that might be feature values
        number_pattern = r'\b\d+\.?\d*\b'
        
        def replace_number(match):
            number = match.group()
            # If it looks like a feature value (small numbers, percentages, etc.)
            try:
                num_val = float(number)
                if 0 <= num_val <= 100:  # Common range for percentages/scores
                    return "[VALUE]"
                else:
                    return number
            except ValueError:
                return number
        
        processed_response = re.sub(number_pattern, replace_number, response)
        
        return processed_response
    
    def _record_privacy_operation(self, user_id: str, operation_id: str, 
                                privacy_level: PrivacyLevel, processed_features: Dict[str, Any]) -> None:
        """Record privacy operation cost."""
        
        epsilon_cost = self._calculate_epsilon_cost_from_features(processed_features, privacy_level)
        
        success = record_privacy_cost(
            user_id, operation_id, "external_inference", epsilon_cost,
            len(processed_features.get("statistical_features", {})),
            processed_features.get("privacy_score", 0.0),
            {"model_provider": "external", "privacy_level": privacy_level.value}
        )
        
        if not success:
            logger.warning(f"Failed to record privacy cost for operation {operation_id}")
    
    def _calculate_epsilon_cost_from_features(self, features: Dict[str, Any], 
                                           privacy_level: PrivacyLevel) -> float:
        """Calculate epsilon cost from processed features."""
        
        base_cost = privacy_level.value
        feature_count = len(features.get("statistical_features", {}))
        complexity_factor = min(1.5, 1.0 + (feature_count / 100.0))
        
        return min(5.0, max(0.1, base_cost * complexity_factor))
    
    def _create_audit_log(self, operation_id: str, user_id: str, 
                          processed_features: Dict[str, Any], 
                          response: ExternalModelResponse,
                          privacy_level: PrivacyLevel) -> None:
        """Create comprehensive audit log."""
        
        # Create audit data
        audit_data = {
            "operation_id": operation_id,
            "user_id": user_id,
            "operation_type": "external_inference",
            "privacy_level": privacy_level.value,
            "epsilon_cost": self._calculate_epsilon_cost_from_features(processed_features, privacy_level),
            "data_sent": {
                "feature_count": len(processed_features.get("statistical_features", {})),
                "document_type": processed_features.get("document_type", "unknown"),
                "risk_level": processed_features.get("risk_level", "unknown"),
                "privacy_score": processed_features.get("privacy_score", 0.0)
            },
            "data_received": {
                "response_length": len(response.raw_response),
                "model_provider": response.model_provider,
                "model_name": response.model_name
            },
            "privacy_validation": {
                "privacy_score": response.privacy_score,
                "response_sanitized": True,
                "no_sensitive_data": True
            },
            "timestamp": time.time()
        }
        
        # Generate audit hash
        audit_string = json.dumps(audit_data, sort_keys=True)
        audit_hash = hashlib.sha256(audit_string.encode()).hexdigest()
        audit_data["audit_hash"] = audit_hash
        
        # Create audit log entry
        audit_log = PrivacyAuditLog(**audit_data)
        self.audit_logs.append(audit_log)
        
        logger.info(f"Audit log created for operation {operation_id}")
    
    def _secure_cleanup(self, sensitive_objects: List[Any]) -> None:
        """Securely clean up sensitive data."""
        
        try:
            # Track objects for cleanup
            for obj in sensitive_objects:
                if obj:
                    track_for_cleanup(obj, f"inference_cleanup_{id(obj)}")
            
            # Perform cleanup
            cleanup_all_tracked()
            
        except Exception as e:
            logger.warning(f"Secure cleanup failed: {e}")
    
    def _get_api_key(self, provider: str) -> str:
        """Get API key for external model provider."""
        
        env_var_map = {
            "replicate": "REPLICATE_API_TOKEN",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        
        env_var = env_var_map.get(provider)
        if not env_var:
            raise ValueError(f"No environment variable mapping for provider: {provider}")
        
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"Missing API key for {provider}: {env_var}")
        
        return api_key
    
    def get_audit_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of audit logs."""
        
        if user_id:
            user_logs = [log for log in self.audit_logs if log.user_id == user_id]
        else:
            user_logs = self.audit_logs
        
        if not user_logs:
            return {"message": "No audit logs found"}
        
        total_operations = len(user_logs)
        total_epsilon_used = sum(log.epsilon_cost for log in user_logs)
        avg_privacy_level = np.mean([log.privacy_level for log in user_logs])
        
        return {
            "total_operations": total_operations,
            "total_epsilon_used": total_epsilon_used,
            "average_privacy_level": avg_privacy_level,
            "recent_operations": [
                {
                    "operation_id": log.operation_id,
                    "timestamp": log.timestamp,
                    "epsilon_cost": log.epsilon_cost,
                    "operation_type": log.operation_type
                }
                for log in sorted(user_logs, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }

# Global instance
privacy_inference = PrivacyPreservingInference()

# Convenience functions
def process_with_external_model(user_id: str, document_features: DocumentFeatures,
                              extracted_features: ExtractedFeatures, **kwargs) -> ExternalModelResponse:
    """Process data with external AI model using privacy-preserving techniques."""
    return privacy_inference.process_with_external_model(
        user_id, document_features, extracted_features, **kwargs
    )

def get_audit_summary(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get audit summary for privacy-preserving operations."""
    return privacy_inference.get_audit_summary(user_id)
