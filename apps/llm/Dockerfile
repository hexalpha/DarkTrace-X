FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 CMAKE_ARGS="-DGGML_NATIVE=OFF" CMAKE_BUILD_PARALLEL_LEVEL=2
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.32.1 pydantic-settings==2.7.0 llama-cpp-python==0.3.35
WORKDIR /worker
# Patch the HTTP runtime separately from the expensive compiled inference layer.
RUN pip install --no-cache-dir --upgrade pip==26.2.1 fastapi==0.141.1 starlette==1.6.0
COPY worker.py .
RUN useradd --uid 10001 --create-home worker
USER worker
CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8091", "--workers", "1"]
