import os
from google.cloud import storage
from dotenv import load_dotenv
from fastapi import UploadFile
import uuid

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")

# Inicializa el cliente de Storage (usará tus credenciales locales de gcloud)
storage_client = storage.Client(project=PROJECT_ID)

async def upload_image_to_gcs(user_id: str, file: UploadFile) -> str:
    """Sube una imagen al bucket en la carpeta del usuario."""
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Generamos un nombre único para evitar sobrescribir archivos
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # Ruta dentro del bucket: users/{user_id}/images/{nombre_unico}
    blob_path = f"users/{user_id}/images/{unique_filename}"
    blob = bucket.blob(blob_path)
    
    # Leemos el contenido del archivo y lo subimos
    file_content = await file.read()
    blob.upload_from_string(file_content, content_type=file.content_type)
    
    # Hacemos el archivo público para que el frontend pueda mostrarlo (opcional, pero útil para empezar)
    # blob.make_public() 
    
    # Retornamos la ruta (o la URL pública si la hiciste pública)
    return f"gs://{BUCKET_NAME}/{blob_path}"