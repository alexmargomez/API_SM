FROM python:3.10-slim

# Evitar que Python escriba archivos .pyc y forzar stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalar dependencias del sistema requeridas por mysqlclient
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Usaremos un script de inicio o CMD directo
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]
