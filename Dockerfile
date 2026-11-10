# Ctrl+A11y as one container: the web app plus a real Chromium for checking pages.
# Works on Hugging Face Spaces (Docker SDK, port 7860), Render, Railway or any Docker host.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app
COPY requirements.txt package-lock.json fetch_axe.py ./
# No Node.js needed: only axe-core's one script file, fetched as package-lock.json pins it (checksum verified).
RUN python -m pip install --no-cache-dir -r requirements.txt && python fetch_axe.py
COPY . .

# Hugging Face Spaces runs containers as user 1000.
RUN useradd -m -u 1000 app 2>/dev/null || true; chown -R 1000:1000 /app
USER 1000
ENV PORT=7860 CTRL_A11Y_MAX_RUNS=2
EXPOSE 7860
CMD ["sh", "-c", "python -m uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
