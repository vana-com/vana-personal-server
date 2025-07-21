from fastapi import APIRouter, HTTPException
from api.schemas import CreateOperationRequest, CreateOperationResponse, GetOperationResponse, ErrorResponse
from services.operations import OperationsService
from domain.exceptions import VanaAPIError
from compute.base import ExecuteResponse, GetResponse
from dependencies import OperationsServiceDep

router = APIRouter()

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
    try:
        operation: ExecuteResponse = operations_service.create(
            request_json=request.operation_request_json,
            signature=request.app_signature,
            chain_id=request.chain_id,
        )

        response = CreateOperationResponse(
            id=operation.id, created_at=operation.created_at
        )

        return response

    except VanaAPIError as e:
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
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
    try:
        operation: GetResponse = operations_service.get(
            operation_id
        )

        response = GetOperationResponse(
            id=operation.id,
            status=operation.status,
            started_at=operation.started_at,
            finished_at=operation.finished_at,
            result=operation.result,
        )

        return response

    except VanaAPIError as e:
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
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
    try:
        success = operations_service.cancel(operation_id)
        if not success:
            error_response = ErrorResponse(
                detail="Operation not found",
                error_code="NOT_FOUND_ERROR"
            )
            raise HTTPException(status_code=404, detail=error_response.dict())
    except VanaAPIError as e:
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.dict())
