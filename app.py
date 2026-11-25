"""
WEB APP DEL RECOMENDADOR DE OUTFITS (Front limpio)
---------------------------------------------------
Este archivo NO contiene lógica de ML. Toda la inferencia (clasificación
de prendas, extracción de color, reglas de combinación) vive en un servicio
separado `ML_SERVICE_URL`.

Pestañas:
1. Recomendador : el usuario sube fotos, el servicio ML las clasifica,
                   y después pide outfits filtrados por ocasión/color.
2. Mi clóset    : prendas guardadas en la nube.
"""

import io
import os
import re

import requests
import streamlit as st
from PIL import Image, ImageOps

from src.auth import cerrar_sesion, iniciar_sesion, registrar_usuario, sesion_actual
from src.config import (
    CLASES, COLORES, ESTILO_CSS, NOMBRE_CLASE,
    NOMBRE_OCASION, OCASIONES, PATRONES,
)
from src import gcp_storage
from dotenv import load_dotenv
load_dotenv()
# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------
MAX_FOTOS_RECOMENDADAS = 30
ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "").rstrip("/")

# -----------------------------------------------------------------------------
# SVGs (sin cambios)
# -----------------------------------------------------------------------------
SVG_PERCHA = """<svg class="svg-icon" width="22" height="22" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M12 6a2 2 0 1 0-2-2"/><path d="M12 6v2.2"/><path d="M12 8.2 3.5 14.5a1.5 1.5 0 0 0 .9 2.7h15.2a1.5 1.5 0 0 0 .9-2.7L12 8.2z"/>
</svg>"""

SVG_ARMA_CLOSET = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<rect x="4" y="3" width="16" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="9" y1="10" x2="9" y2="13"/><line x1="15" y1="10" x2="15" y2="13"/>
</svg>"""

SVG_ETIQUETA = """<svg class="svg-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7" cy="7" r="1.5"/>
</svg>"""

SVG_ALERTA = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
</svg>"""

SVG_OCASION = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="3" x2="12" y2="5"/><line x1="19" y1="12" x2="21" y2="12"/>
</svg>"""

SVG_GUARDAR = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
</svg>"""

SVG_RAPIDO = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
</svg>"""

SVG_BOMBILLA = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>
</svg>"""

SVG_ESTRELLA = """<svg class="svg-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
</svg>"""

# -----------------------------------------------------------------------------
# Setup de Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Recomendador de outfits", page_icon="👕", layout="wide")
if ESTILO_CSS.exists():
    st.markdown(f"<style>{ESTILO_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def limpiar_razon(texto):
    """Quita valores numéricos entre paréntesis al final de cada razón (ej. (+3), (0.46))."""
    limpio = re.sub(r"\s*\([^)]*\)\s*$", "", str(texto)).strip()
    return limpio or str(texto).strip()


@st.cache_data(show_spinner=False)
def crear_miniatura(datos: bytes, lado_max: int = 320) -> bytes:
    """Miniatura JPEG ligera para mostrar en pantalla sin alentar la app."""
    img = Image.open(io.BytesIO(datos))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82, optimize=True)
    return buf.getvalue()


def _ml_disponible() -> bool:
    return bool(ML_SERVICE_URL)

def _get_auth_headers() -> dict:
    """Obtiene headers con token de Firebase para autenticación."""
    headers = {"Content-Type": "application/json"}
    
    if sesion and hasattr(sesion, 'id_token'):
        # Firebase Auth en Streamlit
        headers["Authorization"] = f"Bearer {sesion.id_token}"
    elif sesion and 'id_token' in sesion:
        # Si guardaste el token en la sesión
        headers["Authorization"] = f"Bearer {sesion['id_token']}"
    
    return headers


def clasificar_prenda(datos: bytes) -> dict | None:
    """Llama al servicio ML /classify con autenticación."""
    if not _ml_disponible():
        return None
    
    try:
        headers = {}
        if sesion and hasattr(sesion, 'id_token'):
            headers["Authorization"] = f"Bearer {sesion.id_token}"
        elif sesion and 'id_token' in sesion:
            headers["Authorization"] = f"Bearer {sesion['id_token']}"
        
        resp = requests.post(
            f"{ML_SERVICE_URL}/classify",
            files={"file": ("imagen.jpg", datos, "image/jpeg")},
            headers=headers,
            timeout=15,
        )
        
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.warning("⚠️ Sesión expirada. Por favor, inicia sesión nuevamente.")
        else:
            st.error(f"Error al clasificar: {resp.status_code} - {resp.text}")
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
    
    return None


def pedir_recomendaciones(payload: dict) -> dict | None:
    """Llama al servicio ML /recommend con autenticación."""
    if not _ml_disponible():
        return None
    
    try:
        headers = _get_auth_headers()
        resp = requests.post(
            f"{ML_SERVICE_URL}/recommend",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.warning("⚠️ Sesión expirada. Por favor, inicia sesión nuevamente.")
        else:
            st.error(f"Error al recomendar: {resp.status_code} - {resp.text}")
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
    
    return None


# -----------------------------------------------------------------------------
# Sidebar / auth
# -----------------------------------------------------------------------------
sesion = sesion_actual()
user_id = sesion["uid"] if sesion else None

with st.sidebar:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;font-weight:700;font-size:1.1rem;color:#0f172a;'>"
        f"{SVG_ARMA_CLOSET}<span>Mi clóset</span></div>",
        unsafe_allow_html=True,
    )

    if sesion:
        st.success(f"Hola, **{sesion.get('display_name', sesion['email'])}** 👋")
        st.caption("Tus prendas guardadas permanecen en tu clóset en la nube.")
        if st.button("Cerrar sesión", key="btn_logout"):
            cerrar_sesion()
            st.rerun()
    else:
        st.caption("Inicia sesión para guardar tus prendas en Mi clóset.")
        modo_auth = st.radio("Acceso", ["Iniciar sesión", "Crear cuenta"], horizontal=True, label_visibility="collapsed")

        correo_input = st.text_input("Correo electrónico", placeholder="tu@correo.com", key="auth_email")
        clave_input = st.text_input("Contraseña", type="password", placeholder="••••••••", key="auth_password")

        if modo_auth == "Iniciar sesión":
            if st.button("Iniciar sesión", type="primary", key="btn_login", use_container_width=True):
                ok, msg = iniciar_sesion(correo_input, clave_input)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            nombre_input = st.text_input("Nombre de usuario", placeholder="Ej: Nancy", key="auth_name")
            if st.button("Crear cuenta", type="primary", key="btn_signup", use_container_width=True):
                ok, msg = registrar_usuario(correo_input, clave_input, nombre_input)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def prendas_guardadas():
    if not user_id:
        return []
    try:
        return gcp_storage.obtener_prendas_nube(user_id)
    except Exception as exc:
        st.warning(f"No se pudo consultar Mi clóset en este momento: {exc}")
        return []


# -----------------------------------------------------------------------------
# Hero + tabs
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div id="inicio" class="hero-closet">
      <div class="hero-pill">{SVG_PERCHA} <span>Tu armario, con nuevas ideas</span></div>
      <h1 class="hero-titulo">Tu armario ya tiene la respuesta</h1>
      <p class="hero-sub">
        Sube tus prendas, elige la ocasión y descubre combinaciones explicadas en segundos.
        Sin registro obligatorio para probar, o con inicio de sesión y guardado en Mi clóset.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not _ml_disponible():
    st.warning(
        "⚠️ El servicio de ML no está configurado. Define la variable de entorno "
        "`ML_SERVICE_URL` apuntando a la URL de tu servicio de ML para habilitar "
        "la clasificación y recomendaciones."
    )

tab_rec, tab_closet = st.tabs(["Recomendador", "Mi clóset"])

# ===========================================================================
# 1. RECOMENDADOR
# ===========================================================================
with tab_rec:
    opciones = ["todas"] + OCASIONES
    ocasion = st.radio(
        "1 · ¿Para qué ocasión te vas a vestir?",
        opciones,
        horizontal=True,
        format_func=lambda o: "Cualquiera" if o == "todas" else NOMBRE_OCASION[o],
    )
    ocasion = None if ocasion == "todas" else ocasion

    archivos = st.file_uploader(
        "2 · Sube fotos de tu ropa (todas juntas)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    if archivos and len(archivos) > MAX_FOTOS_RECOMENDADAS:
        st.markdown(
            f"<div class='aviso-limite'>{SVG_ALERTA}<div>Subiste <strong>{len(archivos)} fotos</strong>. "
            f"Para que la página cargue rápido y sea fácil revisar tus prendas, te recomendamos subir "
            f"máximo <strong>{MAX_FOTOS_RECOMENDADAS} fotos</strong> por tanda.</div></div>",
            unsafe_allow_html=True,
        )

    prendas = []
    if archivos:
        st.write(f"3 · Revisa lo que detectó el sistema ({len(archivos)} fotos) y corrige si hace falta.")
        cols = st.columns(4)
        for i, archivo in enumerate(archivos):
            datos = archivo.getvalue()
            miniatura = crear_miniatura(datos, lado_max=300)
            pred = clasificar_prenda(datos) or {}

            tipo_p = pred.get("tipo", "superior")
            color_p = pred.get("color", COLORES[0])
            ocas_p = pred.get("ocasiones", [])
            patron_p = pred.get("patron", PATRONES[0])
            mezclilla_p = bool(pred.get("mezclilla", False))

            k = f"{i}_{archivo.name}"
            with cols[i % 4]:
                with st.container(border=True):
                    st.image(miniatura, width=190)
                    tipo = st.selectbox(
                        "Tipo", CLASES,
                        index=CLASES.index(tipo_p) if tipo_p in CLASES else 0,
                        format_func=NOMBRE_CLASE.get,
                        key=f"t_{k}",
                    )
                    color = st.selectbox(
                        "Color", COLORES,
                        index=COLORES.index(color_p) if color_p in COLORES else 0,
                        key=f"c_{k}",
                    )
                    with st.expander("Más detalles (patrón, mezclilla, ocasiones)"):
                        patron = st.selectbox(
                            "Patrón", PATRONES,
                            index=PATRONES.index(patron_p) if patron_p in PATRONES else 0,
                            key=f"p_{k}",
                        )
                        mezclilla = st.checkbox("Mezclilla", value=mezclilla_p, key=f"m_{k}")
                        ocas = st.multiselect(
                            "Ocasiones", OCASIONES,
                            default=[o for o in ocas_p if o in OCASIONES],
                            format_func=NOMBRE_OCASION.get,
                            key=f"o_{k}",
                        )
            prendas.append({
                "nombre": archivo.name,
                "imagen": datos,
                "tipo": tipo,
                "patron": patron,
                "mezclilla": mezclilla,
                "ocasiones": ocas,
                "color": {"nombre": color},  # el ML service completará los demás campos
            })

    if prendas:
        if not user_id:
            st.caption("Inicia sesión en el panel izquierdo para activar el guardado en Mi clóset.")

        if st.button(
            "Guardar estas prendas en mi clóset",
            disabled=not user_id,
            help=None if user_id else "Inicia sesión en la barra lateral",
        ):
            try:
                for p in prendas:
                    gcp_storage.guardar_prenda_nube(
                        user_id,
                        p["nombre"],
                        p["imagen"],
                        {k: p[k] for k in ("tipo", "patron", "mezclilla", "ocasiones", "color")},
                    )
                st.success(f"Se guardaron {len(prendas)} prendas en la nube.")
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudieron guardar las prendas: {exc}")

    guardadas = prendas_guardadas()
    usar_closet = st.checkbox(
        f"Incluir mi clóset guardado ({len(guardadas)} prendas)",
        value=bool(guardadas),
        disabled=not guardadas,
    )
    top = st.slider("¿Cuántos outfits mostrar?", 1, 15, 5)

    if st.button("Recomendar outfits", type="primary"):
        if not _ml_disponible():
            st.error("El servicio de ML no está configurado. Define `ML_SERVICE_URL`.")
        elif not user_id:
            st.warning("Inicia sesión para obtener recomendaciones.")
        else:
            prendas_extra_metadata = []
            for p in prendas:
                prenda_meta = {
                    "tipo": p["tipo"],
                    "patron": p["patron"],
                    "mezclilla": p["mezclilla"],
                    "ocasiones": p["ocasiones"],
                    "color": p["color"],  # Esto ya es un dict {"nombre": "rojo"}
                    "nombre": p.get("nombre", "Prenda temporal"),
                    "imagen_url": "",  # Vacío porque es una prenda subida temporalmente
                }
                prendas_extra_metadata.append(prenda_meta)
            
            payload = {
                "user_id": user_id,
                "ocasion": ocasion,
                "top": top,
                "incluir_closet": bool(usar_closet),
                "prendas_extra": prendas_extra_metadata,  # ✅ Solo metadata, sin bytes
            }
            
            with st.spinner("Armando combinaciones..."):
                respuesta = pedir_recomendaciones(payload)

            if respuesta is None:
                st.error("No se pudo contactar al servicio de ML. Intenta de nuevo en unos segundos.")
            else:
                resultados = respuesta.get("outfits", [])
                if not resultados:
                    st.warning(
                        "No se pudo armar ningún outfit. Se necesita una prenda de arriba y una de abajo, "
                        "o una prenda completa y calzado"
                        + (f", marcadas para «{NOMBRE_OCASION[ocasion]}»." if ocasion else ".")
                    )
                else:
                    etiqueta_oc = NOMBRE_OCASION[ocasion] if ocasion else "Cualquier ocasión"
                    st.markdown(
                        f"<div class='resumen-outfits'>{SVG_ETIQUETA}<div>Se muestran <strong>{len(resultados)}</strong> "
                        f"{'recomendación' if len(resultados) == 1 else 'recomendaciones'} para "
                        f"<strong>{etiqueta_oc}</strong>.</div></div>",
                        unsafe_allow_html=True,
                    )
                for n, r in enumerate(resultados, start=1):
                    with st.container(border=True):
                        c_head1, c_head2 = st.columns([2, 3])
                        with c_head1:
                            st.markdown(
                                f"<span class='calif'>{SVG_ETIQUETA}<span>Outfit #{n} · {r['calificacion']} / 10</span></span>",
                                unsafe_allow_html=True,
                            )
                        with c_head2:
                            st.progress(min(max(r["calificacion"] / 10, 0.0), 1.0))

                        cols = st.columns(len(r["piezas"]) + 1)
                        for c, p in zip(cols, r["piezas"]):
                            with c:
                                # El ML service devuelve `imagen_url` firmada; si no, usa bytes.
                                if p.get("imagen_url"):
                                    st.image(p["imagen_url"], width=175)
                                elif p.get("imagen"):
                                    st.image(crear_miniatura(p["imagen"], lado_max=280), width=175)
                                st.markdown(
                                    f"<div class='pieza-titulo'>{NOMBRE_CLASE.get(p['tipo'], p['tipo'])}</div>"
                                    f"<div class='pieza-sub'>Color: {p['color']['nombre']}</div>",
                                    unsafe_allow_html=True,
                                )
                        with cols[-1]:
                            razones_limpias = [limpiar_razon(x) for x in r.get("razones", [])]
                            st.markdown("**¿Por qué combina?**\n" + "\n".join(f"- {x}" for x in razones_limpias))

    st.divider()
    st.markdown("<div id='como-funciona' class='acento-linea'></div>", unsafe_allow_html=True)
    st.markdown("### Cómo funciona en 4 pasos")
    p1, p2, p3, p4 = st.columns(4)
    pasos_info = [
        (p1, "01", "Sube tus fotos", "Añade imágenes de las prendas que quieres combinar hoy."),
        (p2, "02", "Elige la ocasión", "Selecciona casual, trabajo, noche o formal según tu plan."),
        (p3, "03", "Decide cuántas", "Ajusta el número máximo de opciones que quieres revisar."),
        (p4, "04", "Revisa y guarda", "Mira calificación y motivos; con sesión guarda en tu clóset."),
    ]
    for col, num, tit, desc in pasos_info:
        with col:
            st.markdown(
                f"<div class='paso-card'><div class='paso-num'>{num}</div>"
                f"<div class='paso-titulo'>{tit}</div><p class='paso-texto'>{desc}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div id='faq' class='acento-linea'></div>", unsafe_allow_html=True)
    st.markdown("### Preguntas frecuentes")
    faqs = [
        ("¿Tengo que registrarme para usar el recomendador?",
         "No. Puedes subir tus fotos y generar combinaciones al momento sin iniciar sesión."),
        ("¿Qué pasa con mis prendas si inicio sesión?",
         "Se guardan en Mi clóset en la nube para reutilizarlas cuando quieras."),
        ("¿Por qué a veces me muestra menos outfits de los que pedí?",
         "El selector indica el máximo a mostrar; si con las prendas actuales y la ocasión elegida solo se forman menos combinaciones válidas, se muestran las disponibles."),
        ("¿Sirve para cualquier ocasión?",
         "Sí, puedes elegir Cualquiera o filtrar por una ocasión específica."),
    ]
    for pregunta, respuesta in faqs:
        with st.expander(pregunta):
            st.write(respuesta)

# ===========================================================================
# 2. MI CLÓSET
# ===========================================================================
with tab_closet:
    if not sesion or not user_id:
        st.info("Inicia sesión en la barra lateral para ver o guardar tu clóset.")
    else:
        guardadas = prendas_guardadas()
        st.write(f"**{len(guardadas)}** {'prenda guardada' if len(guardadas) == 1 else 'prendas guardadas'}.")

        if not guardadas:
            st.info("Aún no tienes prendas guardadas. Ve a **Recomendador**, sube fotos y pulsa **Guardar estas prendas en mi clóset**.")
        else:
            if len(guardadas) > MAX_FOTOS_RECOMENDADAS:
                st.markdown(
                    f"<div class='aviso-limite'>{SVG_ALERTA}<div>Tienes <strong>{len(guardadas)} prendas</strong> guardadas. "
                    f"Las fotos se muestran en miniatura para mantener la página rápida.</div></div>",
                    unsafe_allow_html=True,
                )

            cols = st.columns(4)
            for i, g in enumerate(guardadas):
                d = g["datos"]
                with cols[i % 4]:
                    with st.container(border=True):
                        st.image(crear_miniatura(g["imagen"], lado_max=280), width=185)
                        st.markdown(
                            f"**{NOMBRE_CLASE.get(d['tipo'], d['tipo'])}** · {d['color']['nombre']}",
                            unsafe_allow_html=True,
                        )
                        if st.button("Quitar prenda", key=f"del_{g['id']}"):
                            try:
                                gcp_storage.borrar_prenda_nube(user_id, g["id"])
                                st.rerun()
                            except Exception as exc:
                                st.error(f"No se pudo quitar la prenda: {exc}")