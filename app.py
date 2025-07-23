import sys
import faulthandler
import signal
import os
import traceback
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.operations import router as operations_router
from api.identity import router as identity_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable faulthandler to trace segfaults and crashes
faulthandler.enable()

# Also enable faulthandler with a timeout to detect hangs
faulthandler.dump_traceback_later(30, repeat=True)

# Register faulthandler for SIGTERM signal
if hasattr(faulthandler, 'register'):
    faulthandler.register(signal.SIGTERM)

# Startup log - this should be the FIRST thing we see
print(f"[STARTUP] Process started with PID: {os.getpid()}", flush=True)
print(f"[STARTUP] Python version: {sys.version}", flush=True)
print(f"[STARTUP] Python executable: {sys.executable}", flush=True)

# Set up sys.excepthook for uncaught exceptions
def custom_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print(f"[EXCEPTHOOK] Uncaught exception detected!", flush=True)
    print(f"[EXCEPTHOOK] Type: {exc_type}", flush=True)
    print(f"[EXCEPTHOOK] Value: {exc_value}", flush=True)
    print(f"[EXCEPTHOOK] Traceback:", flush=True)
    traceback.print_tb(exc_traceback)
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = custom_excepthook

print("[STARTUP] Importing FastAPI and creating app instance...", flush=True)

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

print("[STARTUP] Including routers...", flush=True)
app.include_router(operations_router, prefix="/api/v1")
app.include_router(identity_router, prefix="/api/v1")

print("[STARTUP] Application initialization complete", flush=True)

@app.on_event("startup")
async def startup_event():
    print("[STARTUP EVENT] FastAPI startup event triggered", flush=True)

@app.on_event("shutdown")
async def shutdown_event():
    print("[SHUTDOWN EVENT] FastAPI shutdown event triggered", flush=True)

if __name__ == "__main__":
    import uvicorn
    print("[STARTUP] Running with uvicorn...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)