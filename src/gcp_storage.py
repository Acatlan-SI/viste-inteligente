"""
Módulo para gestionar el almacenamiento de imágenes en Google Cloud Storage.
Funciones compatibles con app.py:
- guardar_prenda_nube
- obtener_prendas_nube
- borrar_prenda_nube
- limpiar_vencidas_nube
"""

import os
import json
from datetime import datetime
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------
BUCKET_NAME = os.environ.get("GCP_BUCKET_NAME", "viste-inteligente-bucket")
LOCAL_CREDENTIALS = Path(__file__).resolve().parent.parent / "credentials.json"

_storage_client = None
_bucket = None


def _get_bucket():
    """
    Obtiene el bucket de Cloud Storage (inicialización diferida).
    - En desarrollo local: usa credentials.json de la raíz.
    - En Cloud Run: usa Application Default Credentials (ADC).
    """
    global _storage_client, _bucket
    if _bucket is not None:
        return _bucket

    if LOCAL_CREDENTIALS.exists():
        credentials = service_account.Credentials.from_service_account_file(
            str(LOCAL_CREDENTIALS)
        )
        _storage_client = storage.Client(
            credentials=credentials, project=credentials.project_id
        )
    else:
        _storage_client = storage.Client()

    _bucket = _storage_client.bucket(BUCKET_NAME)
    return _bucket


# -----------------------------------------------------------------------------
# Funciones públicas (nombres esperados por app.py)
# -----------------------------------------------------------------------------
def guardar_prenda_nube(user_id: str, nombre_archivo: str, imagen_bytes: bytes, metadata: dict):
    """Guarda una prenda (imagen + metadatos JSON) en Cloud Storage sin caducidad."""
    bucket = _get_bucket()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    image_blob_name = f"users/{user_id}/images/{timestamp}_{nombre_archivo}"
    image_blob = bucket.blob(image_blob_name)
    image_blob.upload_from_string(imagen_bytes, content_type="image/jpeg")

    metadata["imagen_blob_name"] = image_blob_name
    metadata["fecha_guardado"] = datetime.now().isoformat()

    metadata_blob_name = f"users/{user_id}/metadata/{timestamp}_{nombre_archivo}.json"
    metadata_blob = bucket.blob(metadata_blob_name)
    metadata_blob.upload_from_string(
        json.dumps(metadata),
        content_type="application/json"
    )

    return {
        "id": timestamp,
        "imagen_blob": image_blob_name,
        "metadata_blob": metadata_blob_name,
        "datos": metadata
    }


def obtener_prendas_nube(user_id: str):
    """Obtiene todas las prendas guardadas de un usuario."""
    bucket = _get_bucket()
    prefix = f"users/{user_id}/metadata/"
    blobs = bucket.list_blobs(prefix=prefix)

    prendas = []

    for blob in blobs:
        if blob.name.endswith(".json"):
            try:
                data = json.loads(blob.download_as_text())

                image_blob = bucket.blob(data["imagen_blob_name"])
                imagen_bytes = image_blob.download_as_bytes()

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
                print(f"⚠️ Error procesando {blob.name}: {e}")
                continue

    return prendas


def borrar_prenda_nube(user_id: str, prenda_id: str) -> bool:
    """Borra una prenda (imagen + metadatos)."""
    bucket = _get_bucket()
    prefix = f"users/{user_id}/metadata/"
    blobs = bucket.list_blobs(prefix=prefix)

    for blob in blobs:
        if blob.name.endswith(f"{prenda_id}.json"):
            try:
                data = json.loads(blob.download_as_text())

                if "imagen_blob_name" in data:
                    image_blob = bucket.blob(data["imagen_blob_name"])
                    if image_blob.exists():
                        image_blob.delete()

                blob.delete()
                return True
            except Exception as e:
                print(f"⚠️ Error borrando {blob.name}: {e}")
                return False

    return False


def limpiar_vencidas_nube(user_id: str) -> int:
    """No elimina prendas por antigüedad; se conserva por compatibilidad con app.py."""
    return 0