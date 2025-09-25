FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY storage ./storage
COPY scripts ./scripts
COPY data ./data
COPY Makefile ./Makefile

RUN pip install --no-cache-dir .

EXPOSE 8000 8501

CMD ["python", "-m", "option_flow.launcher.cli", "--demo"]
