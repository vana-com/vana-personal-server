import logging
import traceback
import time
from fastapi import APIRouter, HTTPException, Request
from api.schemas import CreateOperationRequest, CreateOperationResponse, GetOperationResponse, ErrorResponse
from domain.exceptions import VanaAPIError
from compute.base import ExecuteResponse, GetResponse
from dependencies import OperationsServiceDep
from utils.rate_limit import check_rate_limit_sync
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/operations", status_code=202, responses={
    400: {"model": ErrorResponse, "description": "Validation error"},
    401: {"model": ErrorResponse, "description": "Authentication error"},
    403: {"model": ErrorResponse, "description": "Authorization error"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def create_operation(
    request: CreateOperationRequest,
    operations_service: OperationsServiceDep,
    http_request: Request
) -> CreateOperationResponse:
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


@router.get("/operations/{operation_id}", responses={
    404: {"model": ErrorResponse, "description": "Operation not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def get_operation(
    operation_id: str,
    operations_service: OperationsServiceDep,
    http_request: Request
) -> GetOperationResponse:
    request_id = f"get_req_{int(time.time() * 1000)}_{id(operation_id)}"
    start_time = time.time()
    
    logger.info(f"[API] GET /operations/{operation_id} - Starting get operation request [RequestID: {request_id}]")
    logger.info(f"[API] Client IP: {http_request.client.host if http_request.client else 'unknown'} [RequestID: {request_id}]")
    
    try:
        logger.info(f"[API] Calling operations_service.get({operation_id}) [RequestID: {request_id}]")
        operation: GetResponse = operations_service.get(
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


@router.post("/operations/{operation_id}/cancel", status_code=204, responses={
    404: {"model": ErrorResponse, "description": "Operation not found"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def cancel_operation(
    operation_id: str,
    operations_service: OperationsServiceDep,
    http_request: Request
):
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
