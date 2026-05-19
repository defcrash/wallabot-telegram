# 1. Usa a imagem oficial e estável do Python 3.10
FROM python:3.10-slim

# 2. Instala as dependências do sistema necessárias para o Google Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Descarrega e instala a versão oficial e estável do Google Chrome para Linux
RUN wget -q -O - https://google.com | apt-key add - \
    && echo "deb [arch=amd64] http://google.com stable main" >> /etc/html/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 4. Define a pasta de trabalho no servidor
WORKDIR /app

# 5. Copia os ficheiros do seu repositório para o servidor
COPY requirements.txt .
COPY wallabot.py .

# 6. Instala as bibliotecas de Python necessárias
RUN pip install --no-cache-dir python-telegram-bot[ext] selenium python-dotenv

# 7. Executa o script do robô
CMD ["python", "wallabot.py"]
