import logging
import traceback
import time
from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Request, Header, status, Path
from api.schemas import CreateOperationRequest, CreateOperationResponse, GetOperationResponse, ErrorResponse
from domain.exceptions import VanaAPIError
from compute.base import ExecuteResponse, GetResponse
from dependencies import OperationsServiceDep
from utils.rate_limit import check_rate_limit_sync

router = APIRouter(tags=["operations"])
logger = logging.getLogger(__name__)

@router.post(
    "/operations",
    summary="Create a new operation",
    description=(
        "Submit a new operation for asynchronous processing. "
        "Operations are validated against blockchain permissions before execution. "
        "The operation type (LLM inference, vector search, etc.) and parameters "
        "are determined by the grant file referenced in the blockchain permission."
    ),
    response_model=CreateOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Operation accepted and queued for processing",
            "model": CreateOperationResponse,
            "content": {
                "application/json": {
                    "example": {
                        "kind": "OperationCreated",
                        "id": "cm4xp9qkw0001qj0g8xqg8xqg",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request format or malformed JSON in operation_request_json"
        },
        401: {
            "model": ErrorResponse,
            "description": "Signature verification failed or invalid authentication"
        },
        403: {
            "model": ErrorResponse,
            "description": "No valid blockchain permission for requested operation"
        },
        404: {
            "model": ErrorResponse,
            "description": "Referenced permission or grant file not found"
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded - retry with exponential backoff"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error or backend service unavailable"
        }
    }
)
async def create_operation(
    request: CreateOperationRequest,
    operations_service: OperationsServiceDep,
    http_request: Request,
    x_request_id: Annotated[Optional[str], Header()] = None
) -> CreateOperationResponse:
    """
    Create and queue a new operation for asynchronous processing.
    
    This endpoint:
    1. Validates the app signature against the operation request
    2. Verifies blockchain permissions for the requested operation
    3. Fetches and decrypts user data based on permissions
    4. Submits the operation to the appropriate compute backend (Replicate for LLM)
    
    Args:
        request: Operation creation request with signature and parameters
        operations_service: Injected operations service dependency
        http_request: Raw HTTP request for rate limiting
        x_request_id: Optional client-provided request ID for tracing
        
    Returns:
        CreateOperationResponse with operation ID for status polling
        
    Raises:
        HTTPException(400): Malformed request or invalid JSON
        HTTPException(401): Signature verification failed
        HTTPException(403): No valid permission for operation
        HTTPException(404): Permission or grant file not found
        HTTPException(429): Rate limit exceeded
        HTTPException(500): Backend service unavailable
        
    Note:
        Operations are processed asynchronously. Use the returned operation_id
        with GET /operations/{operation_id} to poll for results.
        Average processing time: 2-10 seconds for LLM inference.
    """
    # Generate unique request ID for tracking
    request_id = f"req_{int(time.time() * 1000)}_{id(request)}"
    start_time = time.time()
    
    # Log detailed request information
    logger.info(f"[API] POST /operations - Starting create operation request [RequestID: {request_id}]")
    logger.info(f"[API] Client IP: {http_request.client.host if http_request.client else 'unknown'} [RequestID: {request_id}]")
    logger.info(f"[API] User-Agent: {http_request.headers.get('user-agent', 'unknown')} [RequestID: {request_id}]")
    logger.info(f"[API] Request signature: {request.app_signature[:20]}... (length: {len(request.app_signature)}) [RequestID: {request_id}]")
    logger.info(f"[API] Request JSON length: {len(request.operation_request_json)} chars [RequestID: {request_id}]")
    logger.info(f"[API] Full request JSON: {request.operation_request_json} [RequestID: {request_id}]")

    # Check rate limit
    check_rate_limit_sync(http_request, "operations", request.app_signature)

    try:
        logger.info(f"[API] Calling operations_service.create() [RequestID: {request_id}]")
        operation: ExecuteResponse = await operations_service.create(
            request_json=request.operation_request_json,
            signature=request.app_signature,
            request_id=request_id
        )

        processing_time = time.time() - start_time
        logger.info(f"[API] Operation created successfully: {operation.id} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        
        response = CreateOperationResponse(
            id=operation.id, created_at=operation.created_at
        )
        
        logger.info(f"[API] Returning response: id={response.id}, created_at={response.created_at} [RequestID: {request_id}]")
        return response

    except VanaAPIError as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] VanaAPIError in create_operation: {e.message} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code} [RequestID: {request_id}]")
        logger.error(f"[API] Request signature (first 20 chars): {request.app_signature[:20]}... [RequestID: {request_id}]")
        if hasattr(e, 'field'):
            logger.error(f"[API] Field: {e.field} [RequestID: {request_id}]")
        logger.error(f"[API] Full exception details: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.model_dump())
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] Unexpected exception in create_operation: {str(e)} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Exception type: {type(e).__name__} [RequestID: {request_id}]")
        logger.error(f"[API] Request signature (first 20 chars): {request.app_signature[:20]}... [RequestID: {request_id}]")
        logger.error(f"[API] Request JSON length: {len(request.operation_request_json)} chars [RequestID: {request_id}]")
        logger.error(f"[API] Full traceback: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())


@router.get(
    "/operations/{operation_id}",
    summary="Get operation status",
    description=(
        "Retrieve the current status and result of an operation. "
        "Poll this endpoint to track operation progress from 'starting' through 'processing' "
        "to terminal states ('succeeded', 'failed', 'canceled')."
    ),
    response_model=GetOperationResponse,
    responses={
        200: {
            "description": "Operation status retrieved successfully",
            "model": GetOperationResponse,
            "content": {
                "application/json": {
                    "example": {
                        "kind": "OperationStatus",
                        "id": "cm4xp9qkw0001qj0g8xqg8xqg",
                        "status": "succeeded",
                        "started_at": "2024-01-01T00:00:01Z",
                        "finished_at": "2024-01-01T00:00:05Z",
                        "result": "The analysis indicates positive trends..."
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Operation not found - ID may be invalid or expired"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error retrieving operation status"
        }
    }
)
async def get_operation(
    operation_id: Annotated[str, Path(description="Unique operation identifier from create operation")],
    operations_service: OperationsServiceDep,
    http_request: Request
) -> GetOperationResponse:
    """
    Retrieve operation status and results.
    
    Poll this endpoint to monitor operation progress. Results are available
    once status transitions to 'succeeded'. Operations expire after 24 hours.
    
    Args:
        operation_id: Unique operation identifier from create operation response
        operations_service: Injected operations service dependency
        http_request: Raw HTTP request for logging
        
    Returns:
        GetOperationResponse with current status and results if completed
        
    Raises:
        HTTPException(404): Operation not found or expired
        HTTPException(500): Backend service error
        
    Note:
        Recommended polling interval: 1 second for first 10 seconds,
        then exponential backoff to max 5 seconds.
        Results may be large (up to 5MB for LLM responses).
    """
    request_id = f"get_req_{int(time.time() * 1000)}_{id(operation_id)}"
    start_time = time.time()
    
    logger.info(f"[API] GET /operations/{operation_id} - Starting get operation request [RequestID: {request_id}]")
    logger.info(f"[API] Client IP: {http_request.client.host if http_request.client else 'unknown'} [RequestID: {request_id}]")
    
    try:
        logger.info(f"[API] Calling operations_service.get({operation_id}) [RequestID: {request_id}]")
        operation: GetResponse = await operations_service.get(
            operation_id
        )

        processing_time = time.time() - start_time
        logger.info(f"[API] Operation retrieved successfully: {operation.id}, status: {operation.status} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        
        response = GetOperationResponse(
            id=operation.id,
            status=operation.status,
            started_at=operation.started_at,
            finished_at=operation.finished_at,
            result=operation.result,
        )
        
        logger.info(f"[API] Returning response for operation {operation_id}: status={response.status}, has_result={response.result is not None} [RequestID: {request_id}]")
        return response

    except VanaAPIError as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] VanaAPIError in get_operation({operation_id}): {e.message} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code} [RequestID: {request_id}]")
        logger.error(f"[API] Full exception details: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.model_dump())
    except ValueError as e:
        # Handle "Operation not found" errors
        if "not found" in str(e).lower():
            processing_time = time.time() - start_time
            logger.warning(f"[API] Operation {operation_id} not found [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
            error_response = ErrorResponse(
                detail=f"Operation {operation_id} not found",
                error_code="NOT_FOUND_ERROR"
            )
            raise HTTPException(status_code=404, detail=error_response.model_dump())
        # Re-raise if it's a different ValueError
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] Unexpected exception in get_operation({operation_id}): {str(e)} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Exception type: {type(e).__name__} [RequestID: {request_id}]")
        logger.error(f"[API] Full traceback: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())


@router.post(
    "/operations/{operation_id}/cancel",
    summary="Cancel an operation",
    description=(
        "Cancel a running operation. Only operations in 'starting' or 'processing' "
        "states can be canceled. Completed operations cannot be canceled."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Operation canceled successfully"
        },
        404: {
            "model": ErrorResponse,
            "description": "Operation not found or already completed"
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded for cancellation requests"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error during cancellation"
        }
    }
)
async def cancel_operation(
    operation_id: Annotated[str, Path(description="Unique operation identifier to cancel")],
    operations_service: OperationsServiceDep,
    http_request: Request
) -> None:
    """
    Cancel a running operation.
    
    Attempts to cancel an operation in progress. Only operations in
    'starting' or 'processing' states can be canceled. No effect on
    completed operations.
    
    Args:
        operation_id: Unique operation identifier to cancel
        operations_service: Injected operations service dependency
        http_request: Raw HTTP request for rate limiting
        
    Returns:
        None (204 No Content on success)
        
    Raises:
        HTTPException(404): Operation not found or already completed
        HTTPException(429): Rate limit exceeded
        HTTPException(500): Backend cancellation failed
        
    Note:
        Cancellation is best-effort. Some operations may complete
        before cancellation takes effect. Check status after canceling.
    """
    request_id = f"cancel_req_{int(time.time() * 1000)}_{id(operation_id)}"
    start_time = time.time()
    
    logger.info(f"[API] POST /operations/{operation_id}/cancel - Starting cancel operation request [RequestID: {request_id}]")
    logger.info(f"[API] Client IP: {http_request.client.host if http_request.client else 'unknown'} [RequestID: {request_id}]")

    # Check rate limit
    check_rate_limit_sync(http_request, "default")

    try:
        logger.info(f"[API] Calling operations_service.cancel({operation_id}) [RequestID: {request_id}]")
        success = operations_service.cancel(operation_id)
        
        processing_time = time.time() - start_time
        
        if not success:
            logger.warning(f"[API] Operation {operation_id} not found for cancellation [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
            error_response = ErrorResponse(
                detail="Operation not found",
                error_code="NOT_FOUND_ERROR"
            )
            raise HTTPException(status_code=404, detail=error_response.model_dump())
        
        logger.info(f"[API] Operation {operation_id} cancelled successfully [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        
    except VanaAPIError as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] VanaAPIError in cancel_operation({operation_id}): {e.message} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code} [RequestID: {request_id}]")
        logger.error(f"[API] Full exception details: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.model_dump())
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[API] Unexpected exception in cancel_operation({operation_id}): {str(e)} [RequestID: {request_id}] [ProcessingTime: {processing_time:.3f}s]")
        logger.error(f"[API] Exception type: {type(e).__name__} [RequestID: {request_id}]")
        logger.error(f"[API] Full traceback: {traceback.format_exc()} [RequestID: {request_id}]")
        
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())
