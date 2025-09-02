"""
Artifact storage service using Cloudflare R2.

Provides secure, encrypted storage for agent-generated artifacts
with proper access control and lifecycle management.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from cryptography.fernet import Fernet

from settings import get_settings
from services.identity import IdentityService
from utils.files.encrypt import encrypt_symmetric_key_for_server, decrypt_symmetric_key_with_server

logger = logging.getLogger(__name__)


class ArtifactMetadata:
    """Metadata for a stored artifact."""
    
    def __init__(self, name: str, size: int, content_type: str, checksum: str, created_at: str):
        self.name = name
        self.size = size
        self.content_type = content_type
        self.checksum = checksum
        self.created_at = created_at
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "size": self.size,
            "content_type": self.content_type,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "download_url": f"/api/v1/operations/artifacts/{self.name}"
        }


class ArtifactStorageService:
    """Manages artifact storage using Cloudflare R2."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bucket_name = self.settings.r2_bucket_name
        self.identity_service = IdentityService()
        
        # Initialize R2 client (S3-compatible)
        try:
            self.r2_client = boto3.client(
                's3',
                endpoint_url=f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=self.settings.r2_access_key_id,
                aws_secret_access_key=self.settings.r2_secret_access_key,
                region_name='auto'  # R2 uses 'auto' region
            )
            logger.info("R2 client initialized successfully")
        except NoCredentialsError:
            logger.warning("R2 credentials not found, using local storage fallback")
            self.r2_client = None
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            self.r2_client = None
    
    def _generate_encryption_key(self) -> bytes:
        """Generate a new encryption key for artifacts."""
        return Fernet.generate_key()
    
    def _encrypt_content(self, content: bytes, key: bytes) -> bytes:
        """Encrypt artifact content."""
        f = Fernet(key)
        return f.encrypt(content)
    
    def _decrypt_content(self, encrypted_content: bytes, key: bytes) -> bytes:
        """Decrypt artifact content."""
        f = Fernet(key)
        return f.decrypt(encrypted_content)
    
    def _encrypt_key_for_grantee(self, symmetric_key: bytes, grantee_address: str) -> str:
        """
        Encrypt symmetric key using eccrypto-compatible format with server's public key.
        Uses derived server keys and existing encryption utilities for consistency.
        """
        try:
            # Derive server identity for this grantee
            server_identity = self.identity_service.derive_server_identity(grantee_address)
            
            # Get server's public key
            server_public_key = server_identity.personal_server.public_key
            
            # Encrypt symmetric key using existing utilities
            encrypted_key_hex = encrypt_symmetric_key_for_server(symmetric_key, server_public_key)
            
            return encrypted_key_hex
            
        except Exception as e:
            logger.error(f"Failed to encrypt key for grantee {grantee_address}: {e}")
            raise ValueError(f"Key encryption failed: {e}")
    
    def _decrypt_key_for_grantee(self, encrypted_key_hex: str, grantee_address: str) -> bytes:
        """
        Decrypt symmetric key using eccrypto-compatible format with server's private key.
        Uses derived server keys and existing decryption utilities for consistency.
        """
        try:
            # Derive server identity for this grantee  
            server_identity = self.identity_service.derive_server_identity(grantee_address)
            
            # Get server's private key
            server_private_key = server_identity.personal_server.private_key
            
            # Decrypt symmetric key using existing utilities
            symmetric_key = decrypt_symmetric_key_with_server(encrypted_key_hex, server_private_key)
            
            return symmetric_key
            
        except Exception as e:
            logger.error(f"Failed to decrypt key for grantee {grantee_address}: {e}")
            raise ValueError(f"Key decryption failed: {e}")
    
    def _get_object_key(self, operation_id: str, filename: str) -> str:
        """Generate R2 object key for an artifact."""
        return f"operations/{operation_id}/artifacts/{filename}"
    
    def _get_metadata_key(self, operation_id: str) -> str:
        """Generate R2 object key for operation metadata."""
        return f"operations/{operation_id}/metadata.json"
    
    async def store_artifacts(
        self,
        operation_id: str,
        artifacts: List[Dict],
        grantee_address: str,
        expires_at: Optional[datetime] = None
    ) -> Dict:
        """
        Store artifacts with encryption and metadata.
        
        Args:
            operation_id: Unique operation identifier
            artifacts: List of artifacts with 'name' and 'content' keys
            grantee_address: Address of the grantee (for access control)
            expires_at: When artifacts should expire
        
        Returns:
            Dictionary with artifact metadata
        """
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Generate encryption key for this operation
        encryption_key = self._generate_encryption_key()
        
        stored_artifacts = []
        total_size = 0
        
        for artifact in artifacts:
            try:
                artifact_name = artifact["name"]
                artifact_content = artifact["content"]
                
                if isinstance(artifact_content, str):
                    artifact_content = artifact_content.encode('utf-8')
                
                # Encrypt the artifact
                encrypted_content = self._encrypt_content(artifact_content, encryption_key)
                
                # Determine content type
                content_type = self._guess_content_type(artifact_name)
                
                # Calculate checksum of original content
                import hashlib
                checksum = hashlib.sha256(artifact_content).hexdigest()
                
                # Store in R2 (or local fallback)
                object_key = self._get_object_key(operation_id, artifact_name)
                
                if self.r2_client:
                    await self._upload_to_r2(object_key, encrypted_content)
                else:
                    await self._store_locally(object_key, encrypted_content)
                
                # Create artifact metadata
                artifact_metadata = ArtifactMetadata(
                    name=artifact_name,
                    size=len(artifact_content),  # Original size
                    content_type=content_type,
                    checksum=checksum,
                    created_at=datetime.utcnow().isoformat()
                )
                
                stored_artifacts.append(artifact_metadata.to_dict())
                total_size += len(artifact_content)
                
                logger.info(f"Stored artifact: {artifact_name} ({len(artifact_content)} bytes)")
                
            except Exception as e:
                logger.error(f"Failed to store artifact {artifact.get('name', 'unknown')}: {e}")
                # Continue with other artifacts
        
        # Encrypt the symmetric key using ECIES with server's public key
        encrypted_symmetric_key = self._encrypt_key_for_grantee(encryption_key, grantee_address)
        
        # Store operation metadata
        operation_metadata = {
            "operation_id": operation_id,
            "grantee_address": grantee_address,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "encrypted_key": encrypted_symmetric_key,  # ECIES-encrypted, not plaintext!
            "total_size": total_size,
            "artifact_count": len(stored_artifacts),
            "artifacts": stored_artifacts
        }
        
        # Store metadata
        metadata_key = self._get_metadata_key(operation_id)
        metadata_json = json.dumps(operation_metadata).encode('utf-8')
        
        if self.r2_client:
            await self._upload_to_r2(metadata_key, metadata_json)
        else:
            await self._store_locally(metadata_key, metadata_json)
        
        logger.info(f"Stored {len(stored_artifacts)} artifacts for operation {operation_id}")
        
        return {
            "count": len(stored_artifacts),
            "total_size": total_size,
            "artifacts": stored_artifacts
        }
    
    async def get_artifact_metadata(self, operation_id: str) -> Optional[Dict]:
        """Get metadata for all artifacts in an operation."""
        try:
            metadata_key = self._get_metadata_key(operation_id)
            
            if self.r2_client:
                metadata_content = await self._download_from_r2(metadata_key)
            else:
                metadata_content = await self._load_locally(metadata_key)
            
            if metadata_content:
                return json.loads(metadata_content.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Failed to get metadata for operation {operation_id}: {e}")
        
        return None
    
    async def get_metadata(self, operation_id: str) -> Optional[Dict]:
        """Alias for get_artifact_metadata for consistency."""
        return await self.get_artifact_metadata(operation_id)
    
    async def get_artifact(self, operation_id: str, artifact_path: str) -> Optional[bytes]:
        """Get and decrypt a single artifact."""
        try:
            # Get operation metadata to retrieve encryption key
            metadata = await self.get_metadata(operation_id)
            if not metadata:
                logger.error(f"No metadata found for operation {operation_id}")
                return None
            
            # Decrypt the symmetric key using ECIES
            grantee_address = metadata["grantee_address"]
            encrypted_key_hex = metadata.get("encrypted_key") or metadata.get("encryption_key", "")
            
            # Handle legacy format (base64) during transition
            if "encrypted_key" in metadata:
                # New secure format - decrypt with ECIES
                logger.info(f"Attempting ECIES decryption for operation {operation_id}")
                try:
                    encryption_key = self._decrypt_key_for_grantee(encrypted_key_hex, grantee_address)
                    logger.info(f"ECIES decryption successful, key length: {len(encryption_key)}")
                except Exception as e:
                    logger.error(f"ECIES decryption failed: {e}", exc_info=True)
                    raise
            else:
                # Legacy format - base64 decoding (will be removed)
                logger.warning(f"Using legacy encryption format for operation {operation_id}")
                encryption_key = base64.b64decode(encrypted_key_hex)
            
            # Download encrypted artifact
            object_key = self._get_object_key(operation_id, artifact_path)
            
            if self.r2_client:
                encrypted_content = await self._download_from_r2(object_key)
            else:
                encrypted_content = await self._load_locally(object_key)
            
            if not encrypted_content:
                logger.warning(f"Artifact not found: {operation_id}/{artifact_path}")
                return None
            
            # Decrypt and return content
            decrypted_content = self._decrypt_content(encrypted_content, encryption_key)
            logger.info(f"Successfully decrypted artifact: {len(decrypted_content)} bytes")
            return decrypted_content
            
        except Exception as e:
            logger.error(f"Failed to get artifact {operation_id}/{artifact_path}: {e}", exc_info=True)
            raise  # Re-raise the exception so we can see it in the API response
    
    async def store_artifact(
        self,
        operation_id: str,
        artifact_path: str,
        content: bytes,
        grantee_address: str
    ) -> Dict:
        """
        Store a single artifact (wrapper around store_artifacts).
        
        Args:
            operation_id: Operation identifier
            artifact_path: Path/name of the artifact
            content: Artifact content as bytes
            grantee_address: Address of the grantee
            
        Returns:
            Dictionary with storage result
        """
        artifact = {
            "name": artifact_path,
            "content": content
        }
        
        result = await self.store_artifacts(
            operation_id=operation_id,
            artifacts=[artifact],
            grantee_address=grantee_address
        )
        
        return result
    
    async def list_artifacts(self, operation_id: str) -> List[Dict]:
        """List all artifacts for an operation."""
        try:
            metadata = await self.get_metadata(operation_id)
            if not metadata:
                return []
            
            return metadata.get("artifacts", [])
            
        except Exception as e:
            logger.error(f"Failed to list artifacts for {operation_id}: {e}")
            return []
    
    async def download_artifact(
        self,
        operation_id: str,
        artifact_name: str,
        requesting_address: str
    ) -> Optional[bytes]:
        """
        Download and decrypt an artifact.
        
        Args:
            operation_id: Operation identifier
            artifact_name: Name of the artifact to download
            requesting_address: Address making the request (for access control)
        
        Returns:
            Decrypted artifact content or None if not found/unauthorized
        """
        # Get operation metadata for access control
        metadata = await self.get_artifact_metadata(operation_id)
        if not metadata:
            logger.warning(f"No metadata found for operation {operation_id}")
            return None
        
        # Check access control
        if metadata["grantee_address"].lower() != requesting_address.lower():
            logger.warning(f"Access denied: {requesting_address} tried to access {operation_id}")
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning(f"Artifacts expired for operation {operation_id}")
            return None
        
        # Find the artifact
        artifact_info = None
        for artifact in metadata["artifacts"]:
            if artifact["name"] == artifact_name:
                artifact_info = artifact
                break
        
        if not artifact_info:
            logger.warning(f"Artifact {artifact_name} not found in operation {operation_id}")
            return None
        
        try:
            # Download encrypted content
            object_key = self._get_object_key(operation_id, artifact_name)
            
            if self.r2_client:
                encrypted_content = await self._download_from_r2(object_key)
            else:
                encrypted_content = await self._load_locally(object_key)
            
            if not encrypted_content:
                return None
            
            # Decrypt content
            encryption_key = base64.b64decode(metadata["encryption_key"])
            decrypted_content = self._decrypt_content(encrypted_content, encryption_key)
            
            logger.info(f"Downloaded artifact: {artifact_name} for operation {operation_id}")
            return decrypted_content
            
        except Exception as e:
            logger.error(f"Failed to download artifact {artifact_name}: {e}")
            return None
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename."""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.json': 'application/json',
            '.html': 'text/html',
            '.css': 'text/css',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        return content_types.get(ext, 'application/octet-stream')
    
    async def _upload_to_r2(self, object_key: str, content: bytes):
        """Upload content to Cloudflare R2."""
        try:
            # Run in thread pool since boto3 is synchronous
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.r2_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=content
                )
            )
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
            raise
    
    async def _download_from_r2(self, object_key: str) -> Optional[bytes]:
        """Download content from Cloudflare R2."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.r2_client.get_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.error(f"Failed to download from R2: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to download from R2: {e}")
            return None
    
    async def _store_locally(self, object_key: str, content: bytes):
        """Store content locally (fallback when R2 not available)."""
        local_path = Path(f"/tmp/artifacts/{object_key}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
    
    async def _load_locally(self, object_key: str) -> Optional[bytes]:
        """Load content from local storage."""
        local_path = Path(f"/tmp/artifacts/{object_key}")
        if local_path.exists():
            return local_path.read_bytes()
        return None