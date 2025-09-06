FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Expose a porta para o health check
EXPOSE 8080

CMD ["python", "bot_torneio.py"]