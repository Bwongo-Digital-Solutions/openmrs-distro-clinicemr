FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS test
COPY app.py workflow.py fhir_client.py ./
COPY tests ./tests
RUN python -m unittest discover -s tests -v

FROM base AS runtime
COPY app.py workflow.py fhir_client.py ./
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
