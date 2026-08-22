import json
import os
import re
import urllib.parse
import cv2  # Extrae fotogramas de video
from PIL import Image
from supabase import create_client, Client

# Configuración de Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "wallpapers"  # Corregido al nombre real de tu bucket

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error iniciando cliente Supabase: {e}")

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

def upload_to_supabase(file_path, destination_name):
    if not supabase:
        safe_bucket = urllib.parse.quote(BUCKET_NAME)
        safe_file = urllib.parse.quote(destination_name)
        return f"{SUPABASE_URL}/storage/v1/object/public/{safe_bucket}/{safe_file}"

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        content_type = "video/webm" if destination_name.lower().endswith(".webm") else "video/mp4"

        supabase.storage.from_(BUCKET_NAME).upload(
            file=file_bytes,
            path=destination_name,
            file_options={"x-upsert": "true", "content-type": content_type}
        )
    except Exception as e:
        print(f"Aviso subida {destination_name}: {e}")

    safe_bucket = urllib.parse.quote(BUCKET_NAME)
    safe_file = urllib.parse.quote(destination_name)
    return f"{SUPABASE_URL}/storage/v1/object/public/{safe_bucket}/{safe_file}"

def extract_video_frame(video_path, output_jpg):
    try:
        cap = cv2.VideoCapture(video_path)
        # Saltamos al frame 15 para evitar que la miniatura quede en negro al inicio
        cap.set(cv2.CAP_PROP_POS_FRAMES, 15)
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, frame = cap.read()
        
        if success:
            cv2.imwrite(output_jpg, frame)
        cap.release()
        return success
    except Exception as e:
        print(f"Error en miniatura para {video_path}: {e}")
        return False

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
    cat_detectada = detect_category(archivo)
    titulo_bonito = format_title(archivo)

    es_video = (
        archivo.lower().endswith((".mp4", ".webm"))
        or "live" in archivo.lower()
        or "lv_" in archivo.lower()
    )

    if es_video:
        # Generar miniatura JPG para que la app no muestre el cuadro plomo vacio
        nombre_base = os.path.splitext(archivo)[0]
        thumb_file = f"thumb_{nombre_base}.jpg"
        thumb_path = os.path.join(folder, thumb_file)

        if not os.path.exists(thumb_path):
            extract_video_frame(ruta_completa, thumb_path)

        safe_thumb = urllib.parse.quote(thumb_file)
        url_thumbnail = f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{safe_thumb}"

        # Subir video a Supabase
        hd_url = upload_to_supabase(ruta_completa, archivo)
    else:
        safe_img = urllib.parse.quote(archivo)
        url_thumbnail = f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{safe_img}"
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
        "resolution": "1080p Full HD",
        "is_vip": es_vip,
    })

with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Proceso finalizado. Registrados {len(data['wallpapers'])} wallpapers.")

