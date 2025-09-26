FROM python:3.12-slim-bullseye

# Set the working directory early
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

# --- Optimized User and Permission Setup ---
# 1. Create the user and group first
RUN adduser --system --disabled-password --gecos '' --group appuser

# 2. Copy only the necessary package definition files
COPY package.json ./
COPY pyproject.toml poetry.lock* ./

# 3. Install dependencies as root (creates node_modules with correct permissions)
RUN npm install --only=production
# Install only dependencies first (not the project itself with --no-root)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# 4. Copy the rest of the application source code with proper ownership
# Cache invalidation: This ARG changes with each commit, ensuring fresh code
ARG COMMIT_SHA=unknown
RUN echo "Building commit: ${COMMIT_SHA}"

# This is FAST because .dockerignore excludes node_modules, .git, etc.
# Using --chown flag to set ownership during copy (no separate chown needed!)
COPY --chown=appuser:appuser . .

# 5. Install the project itself now that we have fresh source code
# This ensures our Python package uses the latest code, not cached versions
RUN poetry install --only main --no-interaction --no-ansi

# 6. Build-time sanity check: Verify SUPPORTED_OPERATIONS contains agent operations
RUN python -c "from grants.validate import SUPPORTED_OPERATIONS; expected = {'prompt_gemini_agent', 'prompt_qwen_agent'}; assert expected.issubset(SUPPORTED_OPERATIONS), f'Missing operations: {expected - SUPPORTED_OPERATIONS}'; print(f'✓ SUPPORTED_OPERATIONS verified: {SUPPORTED_OPERATIONS}')"

# 7. Set PATH to include node_modules/.bin for agent CLIs
ENV PATH="/app/node_modules/.bin:${PATH}"

# 8. Switch to the non-root user for running the application
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]