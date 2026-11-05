FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend /app/backend
COPY data /app/data
COPY scripts /app/scripts
RUN useradd --uid 10001 --create-home pharmagraph && mkdir -p /app/runtime && chown -R pharmagraph:pharmagraph /app/runtime
ENV PYTHONPATH=/app/backend STORAGE_PATH=/app/runtime PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python","/app/scripts/container_start.py"]
