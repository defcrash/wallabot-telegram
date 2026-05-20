FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
COPY wallabot.py .
RUN pip install --no-cache-dir python-telegram-bot[ext] requests python-dotenv
CMD ["python", "wallabot.py"]
