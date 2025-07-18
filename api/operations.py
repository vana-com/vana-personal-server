from fastapi import APIRouter, HTTPException
from models import CreateOperationRequest, CreateOperationResponse, GetOperationResponse, ErrorResponse
from services.operations import OperationsService
from compute.replicate import ReplicateCompute, ReplicatePredictionResponse
from onchain.chain import MOKSHA
from exceptions import VanaAPIError

router = APIRouter()
operations_service = OperationsService(ReplicateCompute(), MOKSHA)

@router.post("/operations", status_code=202, responses={
    400: {"model": ErrorResponse, "description": "Validation error"},
    401: {"model": ErrorResponse, "description": "Authentication error"},
    403: {"model": ErrorResponse, "description": "Authorization error"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def create_operation(request: CreateOperationRequest) -> CreateOperationResponse:
    try:
        prediction: ReplicatePredictionResponse = operations_service.create(
            request_json=request.operation_request_json,
            signature=request.app_signature,
        )

        response = CreateOperationResponse(
            id=prediction.id, created_at=prediction.created_at
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
async def get_operation(operation_id: str) -> GetOperationResponse:
    try:
        prediction: ReplicatePredictionResponse = operations_service.get_prediction(
            operation_id
        )

        response = GetOperationResponse(
            id=prediction.id,
            status=prediction.status,
            started_at=prediction.started_at,
            finished_at=prediction.completed_at,
            result=prediction.output,
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


@router.post("/operations/cancel", status_code=204, responses={
    404: {"model": ErrorResponse, "description": "Operation not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def cancel_operation(operation_id: str):
    try:
        success = operations_service.cancel_prediction(operation_id)
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
