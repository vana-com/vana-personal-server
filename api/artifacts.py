import logging
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import Response
from typing import Optional
from services.artifact_storage import ArtifactStorageService
from domain.exceptions import VanaAPIError, AuthenticationError
from utils.auth import signature_auth, mock_mode_auth
from api.schemas import ArtifactDownloadRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/artifacts/download")
async def download_artifact(
    download_request: ArtifactDownloadRequest,
    request: Request
):
    """
    Download an artifact from storage with grantee authentication.
    
    Requires signature authentication - the same pattern as operations API.
    Request data should be signed by the grantee address.
    """
    try:
        operation_id = download_request.operation_id
        artifact_path = download_request.artifact_path
        
        logger.info(f"[ARTIFACTS] Download request: {operation_id}/{artifact_path}")
        
        # Create request data for signature verification
        request_data = f'{{"operation_id":"{operation_id}","artifact_path":"{artifact_path}"}}'
        
        # Verify signature and recover grantee address (with mock mode support)
        try:
            recovered_address = mock_mode_auth.verify_signature_with_mock(
                request_data, download_request.signature
            )
        except (AuthenticationError, ValueError) as e:
            logger.error(f"[ARTIFACTS] Authentication failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        # Get operation metadata to verify grantee access
        storage_service = ArtifactStorageService()
        metadata = await storage_service.get_metadata(operation_id)
        
        if not metadata:
            logger.warning(f"[ARTIFACTS] Operation not found: {operation_id}")
            raise HTTPException(status_code=404, detail="Operation not found")
        
        # Verify the recovered address matches the original grantee
        expected_grantee = metadata.get("grantee_address")
        if not signature_auth.verify_grantee_access(recovered_address, expected_grantee):
            raise HTTPException(status_code=403, detail="Access denied - not the authorized grantee")
        
        # Download and decrypt the artifact
        artifact_data = await storage_service.get_artifact(operation_id, artifact_path)
        
        if not artifact_data:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        # Determine content type based on file extension
        content_type = "text/plain"
        if artifact_path.endswith('.json'):
            content_type = "application/json"
        elif artifact_path.endswith('.md'):
            content_type = "text/markdown"
        elif artifact_path.endswith('.html'):
            content_type = "text/html"
        elif artifact_path.endswith('.csv'):
            content_type = "text/csv"
        
        logger.info(f"[ARTIFACTS] Serving artifact: {len(artifact_data)} bytes, type: {content_type}")
        
        return Response(
            content=artifact_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{artifact_path.split('/')[-1]}\"",
                "Cache-Control": "private, max-age=3600"  # Cache for 1 hour
            }
        )
        
    except VanaAPIError as e:
        logger.error(f"[ARTIFACTS] VanaAPIError downloading {operation_id}/{artifact_path}: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except FileNotFoundError:
        logger.warning(f"[ARTIFACTS] Artifact not found: {operation_id}/{artifact_path}")
        raise HTTPException(status_code=404, detail="Artifact not found")
    except Exception as e:
        logger.error(f"[ARTIFACTS] Unexpected error downloading {operation_id}/{artifact_path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/artifacts/{operation_id}/list")
async def list_artifacts(
    operation_id: str,
    list_request: ArtifactDownloadRequest,
    request: Request
):
    """
    List all artifacts for an operation (requires authentication).
    
    Uses the same authentication pattern as download for consistency.
    """
    try:
        logger.info(f"[ARTIFACTS] List request: {operation_id}")
        
        # Create request data for signature verification  
        request_data = f'{{"operation_id":"{operation_id}","action":"list"}}'
        
        # Verify signature and recover grantee address (with mock mode support)
        try:
            recovered_address = mock_mode_auth.verify_signature_with_mock(
                request_data, list_request.signature
            )
        except (AuthenticationError, ValueError) as e:
            logger.error(f"[ARTIFACTS] Authentication failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        # Get operation metadata to verify grantee access
        storage_service = ArtifactStorageService()
        metadata = await storage_service.get_metadata(operation_id)
        
        if not metadata:
            logger.warning(f"[ARTIFACTS] Operation not found: {operation_id}")
            raise HTTPException(status_code=404, detail="Operation not found")
        
        # Verify the recovered address matches the original grantee
        expected_grantee = metadata.get("grantee_address")
        if not signature_auth.verify_grantee_access(recovered_address, expected_grantee):
            raise HTTPException(status_code=403, detail="Access denied - not the authorized grantee")
        
        artifacts = await storage_service.list_artifacts(operation_id)
        
        return {
            "operation_id": operation_id,
            "artifacts": artifacts
        }
        
    except VanaAPIError as e:
        logger.error(f"[ARTIFACTS] VanaAPIError listing {operation_id}: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"[ARTIFACTS] Error listing artifacts for {operation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Removed unauthenticated simple download endpoint for security
# All artifact access must go through authenticated POST /artifacts/download