FROM joyzoursae/selenium-python-chrome:latest
WORKDIR /app
COPY requirements.txt .
COPY wallabot.py .
# Instalamos o python-telegram-bot com suporte a loop de comandos (ext)
RUN pip install --no-cache-dir python-telegram-bot[ext] selenium python-dotenv
CMD ["python", "wallabot.py"]
