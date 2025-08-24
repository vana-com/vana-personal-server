FROM python:3.12-slim-bullseye

WORKDIR /app

# Install system dependencies and Node.js for agent CLIs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for Python dependencies
RUN pip install --no-cache-dir poetry

# Install agent CLI tools globally
RUN npm install -g @google/gemini-cli @qwen-code/qwen-code@latest

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry lock \
    && poetry install --only main --no-interaction --no-ansi

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"] 
