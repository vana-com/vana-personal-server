import sys
import traceback
import logging
from contextlib import asynccontextmanager

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.operations import router as operations_router
from api.identity import router as identity_router
from api.artifacts import router as artifacts_router
from mcp_server.server import mcp
from mcp_server.resources import get_resource_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

mcp_app = mcp.http_app(path='/')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Custom lifespan that wraps MCP lifespan and starts schema cache prepopulation.
    """
    # Startup: Start schema cache prepopulation
    logger.info("Starting schema cache prepopulation...")
    resource_handler = get_resource_handler()
    await resource_handler.schema_cache.ensure_prepopulate_started()
    
    # Use MCP lifespan for the rest
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(
    title="Vana Personal-Server API",
    version="0.1.0",
    description="A user-scoped compute service that executes permissioned operations on private data.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(artifacts_router, prefix="/api/v1")

app.mount("/mcp", mcp_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
