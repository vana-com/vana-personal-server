from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.operations import router as operations_router
from api.identity import router as identity_router
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Vana Personal-Server API",
    version="0.1.0",
    description="A user-scoped compute service that executes permissioned operations on private data."
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "traceback": traceback.format_exc()}
    )

app.include_router(operations_router, prefix="/api/v1")
app.include_router(identity_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)