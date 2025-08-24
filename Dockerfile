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
COPY package.json package-lock.json ./
COPY pyproject.toml poetry.lock* ./

# 3. Install dependencies as root (creates node_modules with correct permissions)
RUN npm ci --only=production
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# 4. Copy the rest of the application source code
# This is FAST because .dockerignore excludes node_modules, .git, etc.
COPY . .

# 5. Change ownership of the entire app directory
# This is now MUCH faster because node_modules is not being chowned
RUN chown -R appuser:appuser /app

# 6. Switch to the non-root user for running the application
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]