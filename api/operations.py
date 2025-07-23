import logging
import traceback
from fastapi import APIRouter, HTTPException
from api.schemas import CreateOperationRequest, CreateOperationResponse, GetOperationResponse, ErrorResponse
from services.operations import OperationsService
from domain.exceptions import VanaAPIError
from compute.base import ExecuteResponse, GetResponse
from dependencies import OperationsServiceDep

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/operations", status_code=202, responses={
    400: {"model": ErrorResponse, "description": "Validation error"},
    401: {"model": ErrorResponse, "description": "Authentication error"},
    403: {"model": ErrorResponse, "description": "Authorization error"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def create_operation(
    request: CreateOperationRequest,
    operations_service: OperationsServiceDep
) -> CreateOperationResponse:
    logger.info(f"[API] POST /operations - Starting create operation request")
    logger.info(f"[API] Request signature: {request.app_signature[:20]}...")
    logger.info(f"[API] Request JSON: {request.operation_request_json}")
    
    try:
        logger.info(f"[API] Calling operations_service.create() with await")
        operation: ExecuteResponse = await operations_service.create(
            request_json=request.operation_request_json,
            signature=request.app_signature,
        )

        logger.info(f"[API] Operation created successfully: {operation.id}")
        response = CreateOperationResponse(
            id=operation.id, created_at=operation.created_at
        )
        logger.info(f"[API] Returning response: {response}")
        return response

    except VanaAPIError as e:
        logger.error(f"[API] VanaAPIError in create_operation: {e.message}")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code}")
        if hasattr(e, 'field'):
            logger.error(f"[API] Field: {e.field}")
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
        logger.error(f"[API] Unexpected exception in create_operation: {str(e)}")
        logger.error(f"[API] Exception type: {type(e).__name__}")
        logger.error(f"[API] Traceback: {traceback.format_exc()}")
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.dict())


@router.get("/operations/{operation_id}", responses={
    404: {"model": ErrorResponse, "description": "Operation not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def get_operation(
    operation_id: str,
    operations_service: OperationsServiceDep
) -> GetOperationResponse:
    logger.info(f"[API] GET /operations/{operation_id} - Starting get operation request")
    
    try:
        logger.info(f"[API] Calling operations_service.get({operation_id})")
        operation: GetResponse = operations_service.get(
            operation_id
        )

        logger.info(f"[API] Operation retrieved successfully: {operation.id}, status: {operation.status}")
        response = GetOperationResponse(
            id=operation.id,
            status=operation.status,
            started_at=operation.started_at,
            finished_at=operation.finished_at,
            result=operation.result,
        )
        logger.info(f"[API] Returning response for operation {operation_id}")
        return response

    except VanaAPIError as e:
        logger.error(f"[API] VanaAPIError in get_operation({operation_id}): {e.message}")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code}")
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
        logger.error(f"[API] Unexpected exception in get_operation({operation_id}): {str(e)}")
        logger.error(f"[API] Exception type: {type(e).__name__}")
        logger.error(f"[API] Traceback: {traceback.format_exc()}")
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.dict())


@router.post("/operations/{operation_id}/cancel", status_code=204, responses={
    404: {"model": ErrorResponse, "description": "Operation not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def cancel_operation(
    operation_id: str,
    operations_service: OperationsServiceDep
):
    logger.info(f"[API] POST /operations/{operation_id}/cancel - Starting cancel operation request")
    
    try:
        logger.info(f"[API] Calling operations_service.cancel({operation_id})")
        success = operations_service.cancel(operation_id)
        
        if not success:
            logger.warning(f"[API] Operation {operation_id} not found for cancellation")
            error_response = ErrorResponse(
                detail="Operation not found",
                error_code="NOT_FOUND_ERROR"
            )
            raise HTTPException(status_code=404, detail=error_response.dict())
        
        logger.info(f"[API] Operation {operation_id} cancelled successfully")
        
    except VanaAPIError as e:
        logger.error(f"[API] VanaAPIError in cancel_operation({operation_id}): {e.message}")
        logger.error(f"[API] Error code: {e.error_code}, Status: {e.status_code}")
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
        logger.error(f"[API] Unexpected exception in cancel_operation({operation_id}): {str(e)}")
        logger.error(f"[API] Exception type: {type(e).__name__}")
        logger.error(f"[API] Traceback: {traceback.format_exc()}")
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.dict())
