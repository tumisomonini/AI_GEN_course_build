FROM python:3.11-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY Application/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "PYTHONPATH=/app uvicorn Application.API.Main:app --host 0.0.0.0 --port 8000"]
