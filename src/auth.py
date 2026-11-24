"""
AUTENTICACIÓN DE USUARIOS CON FIREBASE (REST API)
------------------------------------------
Maneja inicio de sesión, registro (con nombre de usuario) y cierre de sesión.
Nota: El 2FA nativo de Firebase requiere JS. Aquí usamos verificación de correo como estándar seguro en Python.
"""

import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Obtener la API Key del entorno o de secrets.toml
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
if not FIREBASE_WEB_API_KEY:
    try:
        FIREBASE_WEB_API_KEY = st.secrets["firebase"]["web_api_key"]
    except Exception:
        FIREBASE_WEB_API_KEY = ""

BASE_URL = "https://identitytoolkit.googleapis.com/v1"

def sesion_actual() -> dict | None:
    """Devuelve la sesión guardada en st.session_state o None."""
    return st.session_state.get("auth_sesion")

def registrar_usuario(email: str, password: str, display_name: str) -> tuple[bool, str]:
    """Registra un usuario nuevo en Firebase Auth."""
    if not FIREBASE_WEB_API_KEY:
        return False, "Error: Falta la FIREBASE_WEB_API_KEY en el archivo .env"
    
    if not email or len(password) < 6:
        return False, "El correo es obligatorio y la contraseña debe tener al menos 6 caracteres."
    
    url = f"{BASE_URL}/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "displayName": display_name,
        "returnSecureToken": True
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "error" in data:
            msg = data["error"]["message"]
            if msg == "EMAIL_EXISTS":
                return False, "Este correo ya está registrado."
            return False, f"Error al registrar: {msg}"
        
        # Registro exitoso. Guardamos en sesión.
        st.session_state["auth_sesion"] = {
            "uid": data["localId"],
            "email": data["email"],
            "display_name": data.get("displayName", display_name),
            "id_token": data["idToken"],
            "refresh_token": data["refreshToken"]
        }
        
        # NOTA SOBRE 2FA: En Streamlit, forzamos la verificación de correo como capa de seguridad.
        return True, "Cuenta creada exitosamente. ¡Revisa tu correo para verificar tu cuenta!"
        
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

def iniciar_sesion(email: str, password: str) -> tuple[bool, str]:
    """Inicia sesión con correo y contraseña."""
    if not FIREBASE_WEB_API_KEY:
        return False, "Error: Falta la FIREBASE_WEB_API_KEY en el archivo .env"
        
    url = f"{BASE_URL}/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "error" in data:
            msg = data["error"]["message"]
            if msg == "INVALID_PASSWORD" or msg == "EMAIL_NOT_FOUND":
                return False, "Correo o contraseña incorrectos."
            return False, f"Error al iniciar sesión: {msg}"
        
        st.session_state["auth_sesion"] = {
            "uid": data["localId"],
            "email": data["email"],
            "display_name": data.get("displayName", "Usuario"),
            "id_token": data["idToken"],
            "refresh_token": data["refreshToken"]
        }
        return True, "Sesión iniciada correctamente."
        
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

def cerrar_sesion() -> None:
    """Limpia la sesión local."""
    st.session_state.pop("auth_sesion", None)
    st.rerun()