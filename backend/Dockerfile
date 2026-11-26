FROM python:3.12-slim

WORKDIR /app

# Install uv for fast, reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy package definitions
COPY pyproject.toml uv.lock ./

# Install dependencies into system Python
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy backend code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
