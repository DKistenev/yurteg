FROM python:3.12-slim

# System deps for python-docx, pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

# HF Spaces запускает контейнер под UID 1000 — создаём пользователя с домашней
# папкой, иначе Path.home()/.yurteg (БД, настройки) будет некуда писать.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/home/user/app \
    WEB_MODE=1 \
    DEMO_MODE=1 \
    PORT=8080

WORKDIR /home/user/app

# Только демо-зависимости (без torch/sentence-transformers)
COPY --chown=user requirements-demo.txt .
RUN pip install --no-cache-dir --user -r requirements-demo.txt

COPY --chown=user . .

EXPOSE 8080

CMD ["python", "app/main.py"]
