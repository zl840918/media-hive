FROM python:3.11-slim

WORKDIR /app

# 系统依赖（sqlite 原生、时区）
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

# 离线可装，避免每次构建拉新版
RUN pip install --no-cache-dir .

EXPOSE 8890

ENV MH_DATABASE_URL=sqlite:////data/media_hive.db \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8890"]
