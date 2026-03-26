# ==========================================
# PolyBot - Dockerfile corregido para Railway
# ==========================================
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias sin actualizar pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear carpetas necesarias para persistencia y logs
RUN mkdir -p data logs data/trades

# Exponer el puerto que usa la app
EXPOSE ${PORT}

# Health check para Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:${PORT}/ || exit 1

# Comando de inicio
CMD ["python", "run.py"]
