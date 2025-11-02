import sys
import traceback
import logging
import argparse
import threading
import os
import uvicorn

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


def setup_mcp(mode: str, mcp_port: int = 3000):
    """
    Setup MCP server based on mode.

    Args:
        mode: Either 'stdio' or 'http' (both in a background thread)
            - stdio: For locally running MCP server
            - http: For cloud deployments (streamable http)
        mcp_port: Port for HTTP mode MCP server (default 3000)
    """
    from mcp_server.server import run_stdio, run_http

    if mode == "stdio":
        logging.info("Starting MCP server in stdio mode")
        mcp_thread = threading.Thread(target=run_stdio, daemon=True, name="MCP-stdio")
        mcp_thread.start()

    elif mode == "http":
        logging.info(f"Starting MCP server in HTTP mode on port {mcp_port}")
        mcp_thread = threading.Thread(
            target=lambda: run_http(port=mcp_port),
            daemon=True,
            name="MCP-http"
        )
        mcp_thread.start()

    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'stdio' or 'http'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vana Personal Server")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["stdio", "http"],
        default=None,
        help="MCP server mode: 'stdio' (local) or 'http' (cloud deployments)"
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=3000,
        help="Port for MCP HTTP server (default: 3000)"
    )
    args = parser.parse_args()

    # Auto-detect mode if not specified
    mode = args.mode
    if mode is None:
        # Google Cloud Run injects K_SERVICE environment variable
        if os.getenv("K_SERVICE"):
            mode = "http"
        else:
            mode = "stdio"

    # Start MCP and REST API server
    setup_mcp(mode, mcp_port=args.mcp_port)
    uvicorn.run(app, host="0.0.0.0", port=8000)
