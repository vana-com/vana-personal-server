from fastapi import APIRouter, HTTPException
from models import CreateOperationRequest, CreateOperationResponse, GetOperationResponse
from services.operations import OperationsService
from compute.replicate import ReplicateCompute, ReplicatePredictionResponse
from onchain.chain import MOKSHA

router = APIRouter()
operations_service = OperationsService(ReplicateCompute(), MOKSHA)

@router.post("/operations", status_code=202)
async def create_operation(request: CreateOperationRequest) -> CreateOperationResponse:
    try:
        prediction: ReplicatePredictionResponse = operations_service.create(
            signature=request.app_signature,
            operation_request_json=request.operation_request_json,
        )

        response = CreateOperationResponse(
            id=prediction.id, created_at=prediction.created_at
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations/{operation_id}")
async def get_operation(operation_id: str) -> GetOperationResponse:
    try:
        prediction: ReplicatePredictionResponse = operations_service.get(
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

    except Exception:
        raise HTTPException(status_code=404, detail="Operation not found")


@router.post("/operations/cancel", status_code=204)
async def cancel_operation(operation_id: str):
    try:
        success = operations_service.cancel(operation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Operation not found")
    except Exception:
        raise HTTPException(status_code=404, detail="Operation not found")
