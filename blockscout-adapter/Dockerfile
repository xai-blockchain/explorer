FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Environment defaults
ENV XAI_PRIMARY_URL=http://127.0.0.1:12570
ENV XAI_FALLBACK_URL=http://127.0.0.1:12571
ENV XAI_CHAIN_ID=1337
ENV CORS_ORIGINS=*

EXPOSE 8545

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8545/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8545"]
