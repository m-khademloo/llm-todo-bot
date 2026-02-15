FROM python:3.11-slim

RUN groupadd -r botuser && useradd -r -g botuser -u 1000 botuser

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

USER botuser

CMD ["python", "-m", "src.main"]
