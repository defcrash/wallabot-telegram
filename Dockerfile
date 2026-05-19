# 1. Usa a imagem oficial leve do Python
FROM python:3.10-slim

# 2. Instala dependências básicas do sistema necessárias para o Chrome funcionar
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libgbm1 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# 3. Descarrega e instala diretamente o pacote oficial do Google Chrome Estável
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm -rf google-chrome-stable_current_amd64.deb /var/lib/apt/lists/*

# 4. Define a pasta de trabalho interna
WORKDIR /app

# 5. Copia os seus ficheiros do repositório
COPY requirements.txt .
COPY wallabot.py .

# 6. Instala as bibliotecas Python
RUN pip install --no-cache-dir python-telegram-bot[ext] selenium python-dotenv webdriver-manager

# 7. Inicia o monitor automaticamente
CMD ["python", "wallabot.py"]
