import os
import json
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, storage

# Intentamos importar tu configuración existente
try:
    from src.config import DIAS_GUARDADO
except ImportError:
    DIAS_GUARDADO = 30

def _initialize_firebase():
    """Inicializa Firebase usando ADC (Cloud Run) o archivo local (desarrollo)."""
    if firebase_admin._apps:
        return
    
    # 1. Intentar con Application Default Credentials (Cloud Run)
    try:
        firebase_admin.initialize_app()
        print("✅ Firebase inicializado con Application Default Credentials (Cloud Run)")
        return
    except Exception as e:
        print(f"⚠️ No se pudo inicializar con ADC: {e}")
    
    # 2. Fallback: buscar credentials.json local (desarrollo)
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
        os.path.join(os.getcwd(), "credentials.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            cred = credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase inicializado con archivo local: {path}")
            return
    
    raise RuntimeError(
        "❌ No se pudo inicializar Firebase. "
        "En Cloud Run, verifica que la cuenta de servicio tenga permisos. "
        "En desarrollo local, coloca credentials.json en la raíz del proyecto."
    )

# Inicializar Firebase y obtener bucket
_initialize_firebase()
bucket = storage.bucket(os.environ.get("GCP_BUCKET_NAME", "viste-inteligente-bucket"))

def guardar_prenda_nube(user_id: str, nombre_archivo: str, datos_imagen: bytes, metadatos: dict):
    """Guarda la imagen y sus metadatos en el bucket de GCP."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ruta de la imagen
    img_blob_name = f"users/{user_id}/images/{timestamp}_{nombre_archivo}"
    img_blob = bucket.blob(img_blob_name)
    img_blob.upload_from_string(datos_imagen, content_type="image/jpeg")
    
    # Preparar metadatos
    metadatos["imagen_blob_name"] = img_blob_name
    metadatos["fecha_guardado"] = datetime.now().isoformat()
    metadatos["vence_en"] = (datetime.now() + timedelta(days=DIAS_GUARDADO)).isoformat()
    
    # Ruta de los metadatos
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
            try:
                data = json.loads(blob.download_as_text())
                vence_en = datetime.fromisoformat(data["vence_en"])
                
                if vence_en > ahora:
                    dias_restantes = (vence_en - ahora).days
                    data["vence_en"] = data["vence_en"][:10]
                    data["dias_restantes"] = dias_restantes
                    
                    # Descargar imagen
                    img_blob = bucket.blob(data["imagen_blob_name"])
                    imagen_bytes = img_blob.download_as_bytes()
                    
                    # Extraer nombre original
                    nombre_archivo = data["imagen_blob_name"].split("/")[-1]
                    partes = nombre_archivo.split("_", 2)
                    nombre_original = partes[2] if len(partes) >= 3 else nombre_archivo
                    
                    prendas.append({
                        "id": blob.name.split("/")[-1].replace(".json", ""),
                        "nombre": nombre_original,
                        "imagen": imagen_bytes,
                        "datos": data
                    })
            except Exception as e:
                print(f"⚠️ Error al procesar {blob.name}: {e}")
                continue
                
    return prendas

def borrar_prenda_nube(user_id: str, prenda_id: str):
    """Borra la imagen y los metadatos de una prenda específica."""
    meta_blob = bucket.blob(f"users/{user_id}/metadata/{prenda_id}.json")
    if meta_blob.exists():
        data = json.loads(meta_blob.download_as_text())
        img_blob = bucket.blob(data["imagen_blob_name"])
        img_blob.delete()
    meta_blob.delete()

def limpiar_vencidas_nube(user_id: str):
    """Limpieza automática de prendas vencidas."""
    prefix = f"users/{user_id}/metadata/"
    blobs = bucket.list_blobs(prefix=prefix)
    ahora = datetime.now()
    count = 0
    
    for blob in blobs:
        if blob.name.endswith(".json"):
            try:
                data = json.loads(blob.download_as_text())
                if datetime.fromisoformat(data["vence_en"]) <= ahora:
                    img_blob = bucket.blob(data["imagen_blob_name"])
                    if img_blob.exists():
                        img_blob.delete()
                    blob.delete()
                    count += 1
            except Exception as e:
                print(f"⚠️ Error al limpiar {blob.name}: {e}")
                continue
    return count