from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from services import ReplicateService, IdentityService
from entities import ExecuteRequest, OperationCreated
import os

router = APIRouter()

replicate_service = ReplicateService(os.getenv('REPLICATE_API_TOKEN'))
identity_service = IdentityService()

@router.post('/operations', status_code=202)
async def create_operation(request: ExecuteRequest):
    try:
        prediction = replicate_service.create_prediction(request)
        
        op_id = prediction['id']
        created_at = datetime.utcnow().isoformat() + 'Z'
        
        response = OperationCreated(
            id=op_id,
            created_at=created_at,
            links={
                'self': f'/operations/{op_id}',
                'cancel': f'/operations/{op_id}',
                'stream': f'/operations/{op_id}/stream'
            }
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/operations/{op_id}')
async def get_operation(op_id: str):
    try:
        prediction = replicate_service.get_prediction(op_id)
        
        status_map = {
            'starting': 'pending',
            'processing': 'running',
            'succeeded': 'succeeded',
            'failed': 'failed',
            'canceled': 'cancelled'
        }
        
        response = {
            'id': prediction['id'],
            'status': status_map.get(prediction['status'], 'pending'),
            'started_at': prediction.get('started_at'),
            'finished_at': prediction.get('completed_at'),
            'result': prediction.get('output'),
            'prediction_id': prediction['id']
        }
        
        return response
    
    except Exception:
        raise HTTPException(status_code=404, detail='Operation not found')

@router.delete('/operations/{op_id}', status_code=204)
async def cancel_operation(op_id: str):
    try:
        success = replicate_service.cancel_prediction(op_id)
        if not success:
            raise HTTPException(status_code=404, detail='Operation not found')
    except Exception:
        raise HTTPException(status_code=404, detail='Operation not found')

@router.get('/identity')
async def get_identity(address: str = Query(...)):
    try:
        identity = identity_service.get_identity(address)
        return identity
    
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid address')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))