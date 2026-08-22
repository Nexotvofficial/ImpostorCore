import json
import os
import re
import urllib.parse
import cv2  # Extrae fotogramas de video
from PIL import Image
from supabase import create_client, Client

# Configuración de Supabase desde las variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "wallpapers"

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de carpetas y categorías
folder = "./img"
categories = [
    "Todos",
    "Anime",
    "Cyberpunk",
    "Naturaleza",
    "Fantasía",
    "Minimalista",
    "Live Video",
]

# Función para subir archivos a Supabase Storage
def upload_to_supabase(file_path, destination_name):
    if not supabase:
        print("⚠️ Supabase no está configurado. Revisa tus variables de entorno.")
        return None

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Determinamos el tipo de contenido (MIME type)
        content_type = "video/mp4"
        if destination_name.lower().endswith(".webm"):
            content_type = "video/webm"

        # Intentamos subir (o sobreescribir si ya existe)
        res = supabase.storage.from_(BUCKET_NAME).upload(
            file=file_bytes,
            path=destination_name,
            file_options={"x-upsert": "true", "content-type": content_type}
        )

        # Construimos la URL pública (codificando adecuadamente el bucket y nombre)
        encoded_bucket = urllib.parse.quote(BUCKET_NAME)
        encoded_dest = urllib.parse.quote(destination_name)
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{encoded_bucket}/{encoded_dest}"
        return public_url
    except Exception as e:
        print(f"Error subiendo {destination_name} a Supabase: {e}")
        # Si ya existe o falla, generamos la URL pública de respaldo
        encoded_bucket = urllib.parse.quote(BUCKET_NAME)
        encoded_dest = urllib.parse.quote(destination_name)
        return f"{SUPABASE_URL}/storage/v1/object/public/{encoded_bucket}/{encoded_dest}"

def extract_video_frame(video_path, output_jpg):
    try:
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            cv2.imwrite(output_jpg, frame)
        cap.release()
        return success
    except Exception as e:
        print(f"Error generando miniatura para {video_path}: {e}")
        return False

def get_media_info(file_path):
    ext = file_path.lower().rsplit(".", 1)[-1]
    if ext in ["mp4", "webm", "gif"]:
        return "1080p Full HD"

    try:
        with Image.open(file_path) as img:
            width, height = img.size
            max_dim = max(width, height)
            if max_dim >= 7680:
                return "8K Ultra HD"
            elif max_dim >= 3840:
                return "4K Ultra HD"
            elif max_dim >= 2560:
                return "2K Quad HD"
            elif max_dim >= 1920:
                return "1080p Full HD"
            elif max_dim >= 1280:
                return "720p HD"
            else:
                return "SD"
    except Exception:
        return "1080p Full HD"

def detect_category(filename):
    name = filename.lower()
    if name.startswith("vip_"):
        name = name[4:]

    if name.startswith("fa_") or "fantasia" in name or "fantasía" in name:
        return "Fantasía"
    if name.startswith("mi_") or "minimal" in name:
        return "Minimalista"
    if name.startswith("cy_") or "cyber" in name:
        return "Cyberpunk"
    if name.startswith("na_") or "naturaleza" in name:
        return "Naturaleza"
    if name.startswith("an_") or "anime" in name:
        return "Anime"
    if name.startswith("lv_") or "live" in name or name.endswith((".mp4", ".webm")):
        return "Live Video"
    return "Todos"

def format_title(filename):
    name = filename.rsplit(".", 1)[0]
    if name.lower().startswith("vip_"):
        name = name[4:]

    prefixes = ["an_", "cy_", "na_", "fa_", "mi_", "lv_"]
    for pref in prefixes:
        if name.lower().startswith(pref):
            name = name[len(pref):]
            break

    name = re.sub(r"\(\d+\)", "", name)
    name = name.replace("_", " ").replace("-", " ")
    trash_words = ["descarga", "img", "wallpaper", "foto", "copia"]
    for word in trash_words:
        name = re.sub(r"\b" + word + r"\b", "", name, flags=re.IGNORECASE)

    title = " ".join(name.split()).title()
    return title if title else "Live Wallpaper"

data = {"categories": categories, "wallpapers": []}

if not os.path.exists(folder):
    os.makedirs(folder)

valid_extensions = (".jpg", ".jpeg", ".png", ".mp4", ".webm")
archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_")
]

for i, archivo in enumerate(archivos):
    ruta_completa = os.path.join(folder, archivo)
    es_vip = archivo.lower().startswith("vip_")
    resolucion_real = get_media_info(ruta_completa)
    cat_detectada = detect_category(archivo)
    titulo_bonito = format_title(archivo)
    url_archivo_github = urllib.parse.quote(archivo)

    es_video = (
        archivo.lower().endswith((".mp4", ".webm"))
        or "live" in archivo.lower()
        or "lv_" in archivo.lower()
    )

    if es_video:
        # Extraer miniatura si no existe
        nombre_base = os.path.splitext(archivo)[0]
        thumb_file = f"thumb_{nombre_base}.jpg"
        thumb_path = os.path.join(folder, thumb_file)

        if not os.path.exists(thumb_path):
            extract_video_frame(ruta_completa, thumb_path)

        url_thumbnail = (
            "https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/"
            + urllib.parse.quote(thumb_file)
        )

        # Subir el archivo de video a Supabase Storage
        print(f"Subiendo video a Supabase: {archivo}...")
        hd_url = upload_to_supabase(ruta_completa, archivo)
    else:
        url_thumbnail = (
            "https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/"
            + url_archivo_github
        )
        hd_url = url_thumbnail

    data["wallpapers"].append({
        "id": str(i + 1),
        "title": titulo_bonito,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": cat_detectada,
        "color": "blue",
        "thumbnail": url_thumbnail,
        "hd_url": hd_url,
        "resolution": resolucion_real,
        "is_vip": es_vip,
    })

with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"¡Listo! JSON generado con éxito. Procesados {len(data['wallpapers'])} archivos.")

