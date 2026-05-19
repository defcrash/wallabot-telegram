# 1. Usa a imagem oficial do Python
FROM python:3.10-slim

# 2. Instala apenas o básico para descarregar ficheiros
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Descarrega o Chrome e deixa o sistema instalar todas as dependências sozinho (-f)
RUN wget -q https://google.com \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb || apt-get install -f -y \
    && rm -rf google-chrome-stable_current_amd64.deb /var/lib/apt/lists/*

# 4. Define a pasta de trabalho
WORKDIR /app

# 5. Copia os ficheiros
COPY requirements.txt .
COPY wallabot.py .

# 6. Instala as bibliotecas de Python
RUN pip install --no-cache-dir python-telegram-bot[ext] selenium python-dotenv webdriver-manager

# 7. Inicia o monitor
CMD ["python", "wallabot.py"]
