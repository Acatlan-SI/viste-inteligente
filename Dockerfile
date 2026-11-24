# Usamos una imagen base de Python ligera
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para algunas librerías
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero el archivo de dependencias (para aprovechar el caché de Docker)
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la aplicación
COPY . .

# Streamlit usa el puerto 8080 por defecto en Cloud Run
ENV PORT=8080

# Exponemos el puerto
EXPOSE 8080

# Comando para ejecutar la aplicación
# --server.port: puerto que usa Cloud Run
# --server.address: 0.0.0.0 para aceptar conexiones externas
# --server.headless: true para que no abra navegador
# --server.enableCORS: false porque Cloud Run maneja esto
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false