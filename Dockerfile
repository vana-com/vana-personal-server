FROM python:3.12-slim-bullseye

WORKDIR /app

# Install required system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

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

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]