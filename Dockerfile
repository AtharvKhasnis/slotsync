FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG GIT_SHA=local
ENV GIT_SHA=$GIT_SHA \
    PORT=5000 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 app:app
