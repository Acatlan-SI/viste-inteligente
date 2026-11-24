import os
import json
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, storage

# Intentamos importar tu configuración existente
try:
    from src.config import DIAS_GUARDADO
except ImportError:
    DIAS_GUARDADO = 30 # Valor por defecto si no encuentra el config

# 1. Inicializar Firebase con la clave descargada
# NOTA: En producción (Cloud Run), esto se hará con variables de entorno.
CRED_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")

if not firebase_admin._apps and os.path.exists(CRED_PATH):
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'viste-inteligente-bucket' # El nombre exacto de tu bucket
    })

bucket = storage.bucket()

def guardar_prenda_nube(user_id: str, nombre_archivo: str, datos_imagen: bytes, metadatos: dict):
    """Guarda la imagen y sus metadatos en el bucket de GCP."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ruta de la imagen: users/{user_id}/images/{timestamp}_{nombre}
    img_blob_name = f"users/{user_id}/images/{timestamp}_{nombre_archivo}"
    img_blob = bucket.blob(img_blob_name)
    img_blob.upload_from_string(datos_imagen, content_type="image/jpeg")
    
    # Preparar metadatos
    metadatos["imagen_blob_name"] = img_blob_name
    metadatos["fecha_guardado"] = datetime.now().isoformat()
    metadatos["vence_en"] = (datetime.now() + timedelta(days=DIAS_GUARDADO)).isoformat()
    
    # Ruta de los metadatos: users/{user_id}/metadata/{timestamp}_{nombre}.json
    meta_blob_name = f"users/{user_id}/metadata/{timestamp}_{nombre_archivo}.json"
    meta_blob = bucket.blob(meta_blob_name)
    meta_blob.upload_from_string(json.dumps(metadatos), content_type="application/json")
    
    return {"id": timestamp, "imagen_blob": img_blob_name, "datos": metadatos}

def obtener_prendas_nube(user_id: str):
    """Obtiene todas las prendas válidas (no vencidas) de un usuario."""
    prefix = f"users/{user_id}/metadata/"
    blobs = bucket.list_blobs(prefix=prefix)
    
    prendas = []
    ahora = datetime.now()
    
    for blob in blobs:
        if blob.name.endswith(".json"):
            data = json.loads(blob.download_as_text())
            vence_en = datetime.fromisoformat(data["vence_en"])
            
            if vence_en > ahora:
                dias_restantes = (vence_en - ahora).days
                data["vence_en"] = data["vence_en"][:10]  # Formato corto para la UI
                data["dias_restantes"] = dias_restantes
                
                # Descargamos la imagen en memoria para que Streamlit la muestre
                img_blob = bucket.blob(data["imagen_blob_name"])
                imagen_bytes = img_blob.download_as_bytes()
                
                # Extraemos el nombre original del archivo de la ruta
                nombre_archivo = data["imagen_blob_name"].split("/")[-1]
                # Quitamos el timestamp del principio (formato: 20250125_143022_nombre.jpg)
                partes = nombre_archivo.split("_", 2)
                if len(partes) >= 3:
                    nombre_original = partes[2]
                else:
                    nombre_original = nombre_archivo
                
                # Devolvemos la estructura que espera app.py
                prendas.append({
                    "id": blob.name.split("/")[-1].replace(".json", ""),
                    "nombre": nombre_original,
                    "imagen": imagen_bytes,
                    "datos": data
                })
                
    return prendas

def borrar_prenda_nube(user_id: str, prenda_id: str):
    """Borra la imagen y los metadatos de una prenda específica."""
    # Buscamos el metadata primero para saber el nombre de la imagen
    meta_blob = bucket.blob(f"users/{user_id}/metadata/{prenda_id}.json")
    if meta_blob.exists():
        data = json.loads(meta_blob.download_as_text())
        img_blob = bucket.blob(data["imagen_blob_name"])
        img_blob.delete()
    meta_blob.delete()

def limpiar_vencidas_nube(user_id: str):
    """Limpieza automática de prendas vencidas (para ejecutar al iniciar)."""
    prefix = f"users/{user_id}/metadata/"
    blobs = bucket.list_blobs(prefix=prefix)
    ahora = datetime.now()
    count = 0
    
    for blob in blobs:
        if blob.name.endswith(".json"):
            data = json.loads(blob.download_as_text())
            if datetime.fromisoformat(data["vence_en"]) <= ahora:
                img_blob = bucket.blob(data["imagen_blob_name"])
                if img_blob.exists():
                    img_blob.delete()
                blob.delete()
                count += 1
    return count