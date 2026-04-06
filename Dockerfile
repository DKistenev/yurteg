FROM python:3.12-slim

WORKDIR /app

# System deps for python-docx, pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV WEB_MODE=1
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "app/main.py"]
