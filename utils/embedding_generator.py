"""
Local Embedding Generation System for Privacy-Preserving AI.
This system converts sensitive textual data into mathematical vector representations
that preserve semantic meaning while obscuring specific content.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import time
import hashlib
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pickle
import os

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result of embedding generation with privacy metadata."""
    embeddings: np.ndarray
    original_dimensions: int
    reduced_dimensions: int
    semantic_coherence: float
    privacy_score: float
    generation_metadata: Dict[str, Any]

class LocalEmbeddingGenerator:
    """Generates semantic embeddings locally while preserving privacy."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", max_dimensions: int = 384):
        """
        Initialize local embedding generator.
        
        Args:
            model_name: Sentence transformer model to use
            max_dimensions: Maximum dimensions for privacy (reduces from 768 to this)
        """
        self.model_name = model_name
        self.max_dimensions = max_dimensions
        self.model = None
        self.pca_reducer = None
        self.embedding_cache = {}
        
        # Initialize the model
        self._load_model()
        
        # Initialize PCA for dimension reduction
        self._initialize_pca()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            # Fallback to a simpler model
            try:
                self.model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
                logger.info("Loaded fallback model: paraphrase-MiniLM-L3-v2")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                raise RuntimeError("No embedding models available")
    
    def _initialize_pca(self):
        """Initialize PCA for dimension reduction."""
        try:
            self.pca_reducer = PCA(n_components=self.max_dimensions, random_state=42)
            logger.info(f"PCA initialized for {self.max_dimensions} dimensions")
        except Exception as e:
            logger.error(f"Failed to initialize PCA: {e}")
            self.pca_reducer = None
    
    def generate_embeddings(self, texts: List[str], 
                           apply_privacy: bool = True,
                           privacy_level: float = 1.0) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts with privacy protection.
        
        Args:
            texts: List of text strings to embed
            apply_privacy: Whether to apply privacy-preserving transformations
            privacy_level: Privacy level (0.1 = max privacy, 5.0 = min privacy)
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        logger.info(f"Generating embeddings for {len(texts)} texts with privacy level {privacy_level}")
        
        # Generate base embeddings
        start_time = time.time()
        base_embeddings = self.model.encode(texts, convert_to_numpy=True)
        generation_time = time.time() - start_time
        
        original_dimensions = base_embeddings.shape[1]
        
        # Apply privacy-preserving transformations
        if apply_privacy:
            embeddings = self._apply_privacy_transformations(
                base_embeddings, privacy_level
            )
        else:
            embeddings = base_embeddings
        
        # Calculate semantic coherence
        semantic_coherence = self._calculate_semantic_coherence(embeddings)
        
        # Calculate privacy score
        privacy_score = self._calculate_privacy_score(
            base_embeddings, embeddings, privacy_level
        )
        
        # Create metadata
        generation_metadata = {
            "model_name": self.model_name,
            "original_dimensions": original_dimensions,
            "final_dimensions": embeddings.shape[1],
            "generation_time": generation_time,
            "privacy_level": privacy_level,
            "texts_count": len(texts),
            "timestamp": time.time()
        }
        
        return EmbeddingResult(
            embeddings=embeddings,
            original_dimensions=original_dimensions,
            reduced_dimensions=embeddings.shape[1],
            semantic_coherence=semantic_coherence,
            privacy_score=privacy_score,
            generation_metadata=generation_metadata
        )
    
    def _apply_privacy_transformations(self, embeddings: np.ndarray, 
                                    privacy_level: float) -> np.ndarray:
        """Apply privacy-preserving transformations to embeddings."""
        
        transformed_embeddings = embeddings.copy()
        
        # 1. Dimension reduction for privacy
        if self.pca_reducer and embeddings.shape[1] > self.max_dimensions:
            transformed_embeddings = self._reduce_dimensions(transformed_embeddings)
        
        # 2. Add calibrated noise based on privacy level
        transformed_embeddings = self._add_privacy_noise(
            transformed_embeddings, privacy_level
        )
        
        # 3. Apply vector rotation for additional privacy
        transformed_embeddings = self._apply_vector_rotation(
            transformed_embeddings, privacy_level
        )
        
        # 4. Normalize vectors to prevent magnitude-based attacks
        transformed_embeddings = self._normalize_vectors(transformed_embeddings)
        
        return transformed_embeddings
    
    def _reduce_dimensions(self, embeddings: np.ndarray) -> np.ndarray:
        """Reduce embedding dimensions using PCA."""
        try:
            # Fit PCA on the embeddings
            self.pca_reducer.fit(embeddings)
            
            # Transform to reduced dimensions
            reduced_embeddings = self.pca_reducer.transform(embeddings)
            
            # Calculate explained variance ratio
            explained_variance = np.sum(self.pca_reducer.explained_variance_ratio_)
            logger.info(f"PCA reduction: {embeddings.shape[1]} -> {reduced_embeddings.shape[1]} dimensions")
            logger.info(f"Explained variance preserved: {explained_variance:.3f}")
            
            return reduced_embeddings
            
        except Exception as e:
            logger.warning(f"PCA reduction failed: {e}, using original dimensions")
            return embeddings
    
    def _add_privacy_noise(self, embeddings: np.ndarray, privacy_level: float) -> np.ndarray:
        """Add calibrated noise to embeddings based on privacy level."""
        
        # Noise scale inversely proportional to privacy level
        # Lower privacy_level = higher noise = more privacy
        noise_scale = 1.0 / privacy_level
        
        # Calculate noise magnitude based on embedding statistics
        embedding_std = np.std(embeddings)
        noise_magnitude = embedding_std * noise_scale * 0.1  # 10% of std
        
        # Generate Gaussian noise
        noise = np.random.normal(0, noise_magnitude, embeddings.shape)
        
        # Add noise
        noisy_embeddings = embeddings + noise
        
        logger.info(f"Added noise with magnitude {noise_magnitude:.6f} for privacy level {privacy_level}")
        
        return noisy_embeddings
    
    def _apply_vector_rotation(self, embeddings: np.ndarray, privacy_level: float) -> np.ndarray:
        """Apply random rotation to embedding vectors for privacy."""
        
        # Rotation angle based on privacy level
        # Lower privacy_level = larger rotation = more privacy
        max_rotation = np.pi / (privacy_level * 2)  # Max rotation in radians
        
        # Generate random rotation matrix
        n_dimensions = embeddings.shape[1]
        rotation_matrix = self._generate_rotation_matrix(n_dimensions, max_rotation)
        
        # Apply rotation
        rotated_embeddings = np.dot(embeddings, rotation_matrix)
        
        logger.info(f"Applied vector rotation with max angle {max_rotation:.3f} radians")
        
        return rotated_embeddings
    
    def _generate_rotation_matrix(self, dimensions: int, max_angle: float) -> np.ndarray:
        """Generate a random rotation matrix for given dimensions."""
        
        # Start with identity matrix
        rotation_matrix = np.eye(dimensions)
        
        # Apply random rotations in 2D subspaces
        for i in range(dimensions - 1):
            for j in range(i + 1, dimensions):
                # Random rotation angle
                angle = np.random.uniform(-max_angle, max_angle)
                
                # 2D rotation matrix
                cos_a, sin_a = np.cos(angle), np.sin(angle)
                
                # Apply rotation to the 2D subspace
                rotation_matrix[i, i] = cos_a
                rotation_matrix[i, j] = -sin_a
                rotation_matrix[j, i] = sin_a
                rotation_matrix[j, j] = cos_a
        
        return rotation_matrix
    
    def _normalize_vectors(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embedding vectors to unit length."""
        
        # Calculate L2 norm for each vector
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        
        # Normalize
        normalized_embeddings = embeddings / norms
        
        logger.info("Applied L2 normalization to embedding vectors")
        
        return normalized_embeddings
    
    def _calculate_semantic_coherence(self, embeddings: np.ndarray) -> float:
        """Calculate semantic coherence of embeddings."""
        
        if embeddings.shape[0] < 2:
            return 1.0
        
        # Calculate cosine similarities between all pairs
        similarities = []
        for i in range(embeddings.shape[0]):
            for j in range(i + 1, embeddings.shape[0]):
                # Cosine similarity
                dot_product = np.dot(embeddings[i], embeddings[j])
                norm_i = np.linalg.norm(embeddings[i])
                norm_j = np.linalg.norm(embeddings[j])
                
                if norm_i > 0 and norm_j > 0:
                    similarity = dot_product / (norm_i * norm_j)
                    similarities.append(similarity)
        
        if not similarities:
            return 0.0
        
        # Return average similarity as coherence measure
        coherence = np.mean(similarities)
        return float(coherence)
    
    def _calculate_privacy_score(self, original_embeddings: np.ndarray, 
                               transformed_embeddings: np.ndarray, 
                               privacy_level: float) -> float:
        """Calculate privacy score based on transformation effectiveness."""
        
        # Calculate reconstruction error
        if original_embeddings.shape == transformed_embeddings.shape:
            # Same dimensions, calculate MSE
            mse = np.mean((original_embeddings - transformed_embeddings) ** 2)
            reconstruction_error = mse / np.var(original_embeddings) if np.var(original_embeddings) > 0 else 0
        else:
            # Different dimensions, use a different metric
            reconstruction_error = 1.0 - (transformed_embeddings.shape[1] / original_embeddings.shape[1])
        
        # Privacy score based on reconstruction error and privacy level
        # Higher reconstruction error = better privacy
        privacy_score = min(1.0, reconstruction_error * privacy_level)
        
        return privacy_score
    
    def validate_embeddings(self, embeddings: np.ndarray, 
                          original_texts: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that embeddings maintain semantic meaning while preserving privacy.
        
        Args:
            embeddings: Generated embeddings
            original_texts: Original text content
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        
        issues = []
        
        # Check embedding dimensions
        if embeddings.shape[0] != len(original_texts):
            issues.append(f"Embedding count mismatch: {embeddings.shape[0]} vs {len(original_texts)} texts")
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embeddings)) or np.any(np.isinf(embeddings)):
            issues.append("Embeddings contain NaN or infinite values")
        
        # Check embedding magnitudes (should be normalized)
        magnitudes = np.linalg.norm(embeddings, axis=1)
        if not np.allclose(magnitudes, 1.0, atol=1e-6):
            issues.append("Embeddings are not properly normalized")
        
        # Check semantic coherence
        coherence = self._calculate_semantic_coherence(embeddings)
        if coherence < 0.1:  # Very low coherence might indicate privacy over-destruction
            issues.append(f"Semantic coherence too low: {coherence:.3f}")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def get_embedding_statistics(self, embeddings: np.ndarray) -> Dict[str, Any]:
        """Get statistical information about embeddings."""
        
        return {
            "shape": embeddings.shape,
            "mean": float(np.mean(embeddings)),
            "std": float(np.std(embeddings)),
            "min": float(np.min(embeddings)),
            "max": float(np.max(embeddings)),
            "magnitude_mean": float(np.mean(np.linalg.norm(embeddings, axis=1))),
            "magnitude_std": float(np.std(np.linalg.norm(embeddings, axis=1))),
            "semantic_coherence": float(self._calculate_semantic_coherence(embeddings))
        }
    
    def save_embeddings(self, embeddings: np.ndarray, filepath: str) -> bool:
        """Save embeddings to file."""
        try:
            np.save(filepath, embeddings)
            logger.info(f"Embeddings saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            return False
    
    def load_embeddings(self, filepath: str) -> Optional[np.ndarray]:
        """Load embeddings from file."""
        try:
            embeddings = np.load(filepath)
            logger.info(f"Embeddings loaded from {filepath}")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return None

# Global instance
embedding_generator = LocalEmbeddingGenerator()

# Convenience functions
def generate_embeddings(texts: List[str], privacy_level: float = 1.0) -> EmbeddingResult:
    """Generate embeddings with default privacy settings."""
    return embedding_generator.generate_embeddings(texts, privacy_level=privacy_level)

def validate_embeddings(embeddings: np.ndarray, original_texts: List[str]) -> Tuple[bool, List[str]]:
    """Validate embeddings for semantic coherence and privacy."""
    return embedding_generator.validate_embeddings(embeddings, original_texts)
