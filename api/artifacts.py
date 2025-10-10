import logging
from fastapi import APIRouter, HTTPException, Request, Header, status
from fastapi.responses import Response
from typing import Optional, Annotated
from services.artifact_storage import ArtifactStorageService
from domain.exceptions import VanaAPIError, AuthenticationError
from utils.auth import signature_auth, mock_mode_auth
from api.schemas import ArtifactDownloadRequest, ArtifactListResponse, ErrorResponse

router = APIRouter(tags=["artifacts"])
logger = logging.getLogger(__name__)


@router.post(
    "/artifacts/download",
    summary="Download operation artifact",
    description=(
        "Download an artifact file produced by an operation. "
        "Requires ECDSA signature authentication - the grantee (app) that created "
        "the operation must sign the download request."
    ),
    responses={
        200: {
            "description": "Artifact file content with appropriate content type",
            "content": {
                "application/json": {"example": {"result": "analysis data"}},
                "text/plain": {"example": "Text file content"},
                "text/markdown": {"example": "# Report\nContent here"}
            }
        },
        401: {
            "model": ErrorResponse,
            "description": "Signature verification failed or invalid authentication"
        },
        403: {
            "model": ErrorResponse,
            "description": "Access denied - not the authorized grantee for this operation"
        },
        404: {
            "model": ErrorResponse,
            "description": "Operation or artifact not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error retrieving artifact"
        }
    },
    status_code=status.HTTP_200_OK
)
async def download_artifact(
    download_request: ArtifactDownloadRequest,
    request: Request
):
    """
    Download an artifact file with grantee authentication.

    Validates that the requesting app (grantee) is the same entity that created
    the operation. Downloads and decrypts the artifact from storage.

    Args:
        download_request: Download request with operation_id, artifact_path, and signature
        request: Raw HTTP request for logging

    Returns:
        Response with artifact file content and appropriate content type

    Raises:
        HTTPException(401): Signature verification failed
        HTTPException(403): Requester is not the authorized grantee
        HTTPException(404): Operation or artifact not found
        HTTPException(500): Storage service error

    Note:
        Artifacts are cached for 1 hour. Content type is determined from file extension.
        Signature must be over JSON: {"operation_id":"...", "artifact_path":"..."}
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

        # Verify the recovered address matches either the grantor (user) or grantee (app)
        grantor_address = metadata.get("grantor_address")
        grantee_address = metadata.get("grantee_address")

        is_grantor = signature_auth.verify_grantee_access(recovered_address, grantor_address)
        is_grantee = signature_auth.verify_grantee_access(recovered_address, grantee_address)

        if not (is_grantor or is_grantee):
            raise HTTPException(status_code=403, detail="Access denied - not authorized grantor or grantee")

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


@router.post(
    "/artifacts/{operation_id}/list",
    summary="List operation artifacts",
    description=(
        "List all artifacts produced by an operation. "
        "Requires ECDSA signature authentication from the grantee (app) that created the operation."
    ),
    response_model=ArtifactListResponse,
    responses={
        200: {
            "description": "List of available artifacts retrieved successfully",
            "model": ArtifactListResponse
        },
        401: {
            "model": ErrorResponse,
            "description": "Signature verification failed or invalid authentication"
        },
        403: {
            "model": ErrorResponse,
            "description": "Access denied - not the authorized grantee for this operation"
        },
        404: {
            "model": ErrorResponse,
            "description": "Operation not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error retrieving artifact list"
        }
    },
    status_code=status.HTTP_200_OK
)
async def list_artifacts(
    operation_id: str,
    list_request: ArtifactDownloadRequest,
    request: Request
) -> ArtifactListResponse:
    """
    List all artifacts for an operation with grantee authentication.

    Returns metadata about all artifact files produced by the operation including
    paths, sizes, and content types.

    Args:
        operation_id: Unique operation identifier
        list_request: Authentication request with signature
        request: Raw HTTP request for logging

    Returns:
        ArtifactListResponse with list of artifact metadata

    Raises:
        HTTPException(401): Signature verification failed
        HTTPException(403): Requester is not the authorized grantee
        HTTPException(404): Operation not found
        HTTPException(500): Storage service error

    Note:
        Signature must be over JSON: {"operation_id":"...", "action":"list"}
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

        # Verify the recovered address matches either the grantor (user) or grantee (app)
        grantor_address = metadata.get("grantor_address")
        grantee_address = metadata.get("grantee_address")

        is_grantor = signature_auth.verify_grantee_access(recovered_address, grantor_address)
        is_grantee = signature_auth.verify_grantee_access(recovered_address, grantee_address)

        if not (is_grantor or is_grantee):
            raise HTTPException(status_code=403, detail="Access denied - not authorized grantor or grantee")

        artifacts = await storage_service.list_artifacts(operation_id)

        return ArtifactListResponse(
            operation_id=operation_id,
            artifacts=artifacts
        )
        
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