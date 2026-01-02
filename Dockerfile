FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install-deps
RUN python -m playwright install chromium

COPY . .
CMD ["python", "main.py"]
