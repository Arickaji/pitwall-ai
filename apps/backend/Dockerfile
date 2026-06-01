FROM python:3.10-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM dependencies AS final

COPY . .

RUN mkdir -p /app/data/cache /app/data/ml/models

# Copy schedule JSON files — tiny (12KB each), avoids GitHub API calls
COPY data/schedules/ /app/data/schedules/

EXPOSE 8000

CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
