FROM python:3.12-slim-bullseye

WORKDIR /app

# Install diagnostic tools and required system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    strace \
    gdb \
    ldd \
    file \
    procps \
    libssl-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python debugging tools
RUN pip install --no-cache-dir py-spy

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Check linked libraries for critical Python modules
RUN echo "[DOCKER BUILD] Checking linked libraries for Python modules..." && \
    python -c "import _ssl; print(f'_ssl module: {_ssl.__file__}')" && \
    ldd $(python -c "import _ssl; print(_ssl.__file__)") || true && \
    python -c "import _hashlib; print(f'_hashlib module: {_hashlib.__file__}')" && \
    ldd $(python -c "import _hashlib; print(_hashlib.__file__)") || true && \
    echo "[DOCKER BUILD] Checking web3 dependencies..." && \
    python -c "import web3; print(f'web3 version: {web3.__version__}')" && \
    python -c "import coincurve; print(f'coincurve loaded from: {coincurve.__file__}')" || echo "coincurve not found" && \
    python -c "import cytoolz; print(f'cytoolz loaded from: {cytoolz.__file__}')" || echo "cytoolz not found"

COPY . .

# Create a wrapper script for strace
RUN echo '#!/bin/bash\necho "[STRACE] Starting application with strace..."\nstrace -f -e trace=all -o /tmp/strace.log python -m uvicorn app:app --host 0.0.0.0 --port 8080 &\nSTRACE_PID=$!\necho "[STRACE] Strace PID: $STRACE_PID"\n# Monitor the strace log file\ntail -f /tmp/strace.log &\nTAIL_PID=$!\n# Wait for the strace process\nwait $STRACE_PID\nSTATUS=$?\necho "[STRACE] Application exited with status: $STATUS"\necho "[STRACE] Last 100 lines of strace log:"\ntail -n 100 /tmp/strace.log\nexit $STATUS' > /app/start-with-strace.sh && \
    chmod +x /app/start-with-strace.sh

# Keep root user for now to ensure strace works properly
# We'll switch back to appuser once we've debugged the issue
# RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
# USER appuser

EXPOSE 8080

# Use strace to trace system calls - this will show us exactly what happens before the crash
CMD ["/app/start-with-strace.sh"]