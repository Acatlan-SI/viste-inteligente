# Usamos una imagen base de Python ligera pero compatible
FROM python:3.11-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# 1. Instalar dependencias del sistema necesarias para compilar paquetes de datos/ML
# (gcc, g++ para C++, libjpeg y zlib para Pillow/imágenes)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Actualizar pip (como sugiere el propio error de Cloud Build)
RUN pip install --upgrade pip

# 3. Copiar solo el archivo de dependencias primero (para aprovechar la caché de Docker)
COPY requirements.txt .

# 4. Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de la aplicación
COPY . .

# 6. Configurar variables de entorno para Streamlit en Cloud Run
ENV PORT=8080
EXPOSE 8080

# 7. Comando de inicio
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --browser.gatherUsageStats=false