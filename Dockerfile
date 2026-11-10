# Ctrl+A11y as one container: the web app plus a real Chromium for checking pages.
# Works on Hugging Face Spaces (Docker SDK, port 7860), Render, Railway or any Docker host.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt package.json package-lock.json ./
RUN python -m pip install --no-cache-dir -r requirements.txt && npm ci --omit=dev
COPY . .

# Hugging Face Spaces runs containers as user 1000.
RUN useradd -m -u 1000 app 2>/dev/null || true; chown -R 1000:1000 /app
USER 1000
ENV PORT=7860 CTRL_A11Y_MAX_RUNS=2
EXPOSE 7860
CMD ["sh", "-c", "python -m uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
