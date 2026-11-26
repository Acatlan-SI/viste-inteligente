# Viste Inteligente

Aplicación web para clasificar prendas y solicitar recomendaciones de outfits según una ocasión. Este repositorio contiene el **frontend en Streamlit** y las integraciones con servicios externos; la clasificación y la generación de outfits se realizan en un servicio de ML independiente.

La aplicación está desplegada en Google Cloud Run: [viste-inteligente.cloud.run](https://viste-inteligente.cloud.run).

## Funcionalidades

### Recomendador

- Permite elegir entre **cualquier ocasión**, casual, business casual, formal, deportivo y fiesta/noche.
- Acepta varias imágenes JPG, JPEG, PNG y WEBP en una sola carga. Recomienda subir hasta 30 fotos por tanda; el límite es un aviso, no un bloqueo.
- Envía cada imagen al servicio ML para detectar tipo de prenda, color, patrón, mezclilla y ocasiones. Los campos se pueden revisar y corregir antes de pedir outfits.
- Permite incluir las prendas guardadas en **Mi clóset** y elegir cuántos resultados solicitar (de 1 a 15).
- Muestra los outfits devueltos por la API, su calificación sobre 10, las prendas y las razones de la combinación. Si la API devuelve menos resultados válidos que los solicitados, muestra los disponibles.
- Las imágenes cargadas se envían a `/classify`. Al pedir recomendaciones, las prendas de la carga actual se envían como metadatos, sin los bytes de imagen.

**En el comportamiento actual, se requiere iniciar sesión para solicitar recomendaciones y guardar prendas.** Se puede explorar la interfaz y clasificar imágenes sin iniciar sesión.

### Mi clóset

- Permite guardar imágenes y metadatos en Google Cloud Storage asociados a la cuenta.
- Lista las prendas guardadas, permite quitarlas y usarlas como parte de una recomendación.
- Las prendas se conservan hasta que el usuario las elimina; el almacenamiento actual no las elimina automáticamente por antigüedad.

### Cuenta

- Crear una cuenta e iniciar sesión con correo y contraseña mediante Firebase Authentication.
- Cerrar sesión desde la barra lateral.
- La sesión conserva el identificador de usuario y el token de Firebase para las llamadas autenticadas.

## Recorrido principal de la interfaz

1. Inicia sesión en la barra lateral para habilitar recomendaciones y el guardado en la nube.
2. En **Recomendador**, selecciona una ocasión y sube fotos.
3. Revisa las predicciones y ajusta tipo, color, patrón, mezclilla y ocasiones si hace falta.
4. Opcionalmente, guarda las prendas o incluye las que ya están en Mi clóset.
5. Selecciona la cantidad de outfits y pulsa **Recomendar outfits**.
6. Revisa las calificaciones, las imágenes y las razones presentadas. En **Mi clóset**, puedes consultar o eliminar prendas guardadas.

## Funciones del código

### `app.py`

| Función | Utilidad |
|---|---|
| `limpiar_razon(texto)` | Quita del final de una razón valores numéricos entre paréntesis para presentarla en la interfaz. |
| `crear_miniatura(datos, lado_max)` | Corrige la orientación de la imagen, crea una miniatura JPEG y la cachea para mostrarla con menor costo. |
| `_ml_disponible()` | Comprueba si se configuró la URL del servicio ML. |
| `_get_auth_headers()` | Prepara los encabezados JSON y el token de Firebase de la sesión actual. |
| `clasificar_prenda(datos)` | Envía una imagen a `POST /classify` y procesa la respuesta o muestra el error recibido. |
| `pedir_recomendaciones(payload)` | Envía los metadatos de la solicitud a `POST /recommend` y procesa la respuesta o muestra el error recibido. |
| `prendas_guardadas()` | Obtiene las prendas de la cuenta actual desde Cloud Storage y muestra un aviso si no se pueden consultar. |

El resto de `app.py` construye la interfaz: autenticación en la barra lateral, pestañas, formulario del recomendador, resultados, preguntas frecuentes y vista de Mi clóset.

### `src/auth.py`

| Función | Utilidad |
|---|---|
| `sesion_actual()` | Recupera la sesión almacenada en el estado de Streamlit. |
| `registrar_usuario(email, password, display_name)` | Registra una cuenta mediante Firebase Authentication y guarda la sesión resultante. |
| `iniciar_sesion(email, password)` | Autentica una cuenta mediante Firebase Authentication y guarda la sesión resultante. |
| `cerrar_sesion()` | Elimina la sesión local y actualiza la aplicación. |

### `src/gcp_storage.py`

| Función | Utilidad |
|---|---|
| `_get_bucket()` | Inicializa el cliente de Google Cloud Storage y obtiene el bucket configurado. |
| `guardar_prenda_nube(user_id, nombre_archivo, imagen_bytes, metadata)` | Guarda la imagen y sus metadatos bajo el identificador del usuario. |
| `obtener_prendas_nube(user_id)` | Recupera los metadatos y las imágenes de las prendas del usuario. |
| `borrar_prenda_nube(user_id, prenda_id)` | Elimina la imagen y los metadatos de una prenda. |
| `limpiar_vencidas_nube(user_id)` | Mantiene compatibilidad con el código que la invoca; actualmente no elimina prendas y devuelve `0`. |

### Configuración y recursos de interfaz

- `src/config.py`: catálogos de tipos de prenda, colores, patrones y ocasiones; nombres de presentación y rutas del CSS.
- `assets/estilo.css`: estilos y diseño adaptable.
- `.streamlit/config.toml`: tema visual de Streamlit.
- `requirements.txt`: dependencias de Python.
- `Dockerfile`: construcción de la imagen para Cloud Run.

## Integraciones y peticiones a la API

### Servicio ML

La URL base se configura con `ML_SERVICE_URL`. La interfaz quita las barras finales al leerla.

#### Clasificación: `POST {ML_SERVICE_URL}/classify`

- Envía la imagen como `multipart/form-data` en el campo `file`, con nombre `imagen.jpg` y tipo `image/jpeg`.
- Agrega `Authorization: Bearer <id_token>` si hay una sesión activa.
- Tiempo de espera del cliente: 15 segundos.
- La interfaz consume los campos `tipo`, `color`, `ocasiones`, `patron` y `mezclilla` de la respuesta.

#### Recomendaciones: `POST {ML_SERVICE_URL}/recommend`

- Envía JSON con los campos `user_id`, `ocasion` (o `null` para cualquier ocasión), `top`, `incluir_closet` y `prendas_extra`.
- Cada elemento de `prendas_extra` incluye tipo, patrón, mezclilla, ocasiones, color, nombre e `imagen_url`. Las fotos cargadas en esa sesión se envían como metadatos, no como bytes.
- Incluye el token de Firebase en `Authorization: Bearer <id_token>`.
- Tiempo de espera del cliente: 30 segundos.
- La interfaz espera un objeto con una lista `outfits`. Presenta la `calificacion`, las `piezas` y las `razones` de cada resultado. Para cada pieza puede mostrar `imagen_url` si está disponible.

Si `ML_SERVICE_URL` no está definido, la interfaz avisa que el servicio no está configurado y no puede clasificar ni generar recomendaciones. Este repositorio no incluye el servicio ML.

### Firebase Authentication

`src/auth.py` usa la API REST de Firebase Identity Toolkit:

- `POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=...` para registrar una cuenta.
- `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=...` para iniciar sesión.

La clave web se lee desde `FIREBASE_WEB_API_KEY` o, si no está definida, desde `st.secrets["firebase"]["web_api_key"]`.

### Google Cloud Storage

Las imágenes y los metadatos se guardan en rutas separadas por usuario dentro del bucket. El nombre del bucket se configura con `GCP_BUCKET_NAME`; si no se define, se usa `viste-inteligente-bucket`.

En local, el módulo usa `credentials.json` en la raíz si existe; si no, usa Application Default Credentials (ADC). En Cloud Run, configura una cuenta de servicio con permisos para acceder al bucket.

## Requisitos

- Python 3.12, igual que la versión base indicada en el `Dockerfile`.
- Acceso a un servicio ML que implemente `/classify` y `/recommend`.
- Una clave web de Firebase para autenticación.
- Para guardar y consultar prendas: acceso de Google Cloud a un bucket de Storage.

## Ejecutar localmente

Los siguientes comandos son para Windows PowerShell, desde la raíz del repositorio.

1. Crea y activa un entorno virtual:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   Si PowerShell bloquea la activación del entorno, consulta la política de ejecución de tu equipo o activa el entorno desde una terminal compatible.

2. Instala las dependencias del proyecto en el entorno:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   Esto prepara el entorno local con Streamlit, Requests, Pillow, Firebase Admin, Google Cloud Storage y `python-dotenv`.

3. Crea un archivo `.env` en la raíz del proyecto y configura los valores localmente:

   ```dotenv
   ML_SERVICE_URL=https://URL-DE-TU-SERVICIO-ML
   FIREBASE_WEB_API_KEY=TU_CLAVE_WEB_DE_FIREBASE
   GCP_BUCKET_NAME=TU_BUCKET
   ```

   Sustituye los valores de ejemplo por los de tus servicios. `GCP_BUCKET_NAME` es opcional si usarás el nombre predeterminado. Para Google Cloud Storage, coloca `credentials.json` de forma privada en la raíz o configura ADC. No incluyas credenciales reales en el repositorio ni en capturas o documentación.

4. Inicia la aplicación:

   ```powershell
   streamlit run app.py
   ```

   Abre la URL local que Streamlit muestra en la terminal, normalmente `http://localhost:8501`.

Sin `ML_SERVICE_URL` se puede abrir la interfaz, pero no se podrán clasificar prendas ni obtener recomendaciones. Sin la configuración de Firebase no se podrá iniciar sesión; sin acceso al bucket no se podrá guardar ni consultar Mi clóset.

## Construir y ejecutar con Docker

Desde la raíz del repositorio, construye la imagen:

```powershell
docker build -t viste-inteligente .
```

El entorno de ejecución del contenedor necesita las mismas variables de entorno y acceso a Google Cloud. `.env` y `credentials.json` se excluyen del contexto de construcción; no se copian a la imagen. Puedes pasar las variables al ejecutar el contenedor usando un archivo local protegido:

```powershell
docker run --rm -p 8080:8080 --env-file .env viste-inteligente
```

En ese caso configura el acceso a Cloud Storage con ADC para contenedores o el mecanismo de secretos de tu entorno, no agregando credenciales a la imagen. La aplicación queda disponible en `http://localhost:8080`.

## Protección de secretos

El archivo `.env` se mantiene **privado** porque contiene la URL del servicio y claves usadas para acceder a APIs. Está excluido del control de versiones; también se excluye del contexto de Docker para evitar que termine dentro de la imagen. No publiques su contenido ni subas claves, tokens o `credentials.json` al repositorio. En GCP, usa la configuración de secretos y permisos de la cuenta de servicio de Cloud Run.
