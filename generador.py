import json
import os
import random
import re
import subprocess
import cv2
import requests
from PIL import Image
from transformers import pipeline

folder = "./img"
thumbs_folder = "./img/thumbs"

# Mapeo de prefijos manuales (Tienen prioridad absoluta sobre la IA)
PREFIX_MAP = {
    "an_": "Anime",
    "cy_": "Cyberpunk",
    "na_": "Naturaleza",
    "fa_": "Fantasía",
    "mi_": "Minimalista",
    "au_": "Autos",
    "ur_": "Urbano",
    "es_": "Espacio",
    "ab_": "Abstracto"
}

# Prompts descriptivos optimizados para CLIP (Evitan confusiones con trajes, cosplays y renders 3D)
category_prompts = {
    "an anime illustration, 2d Japanese animation, manga drawing, or animated character artwork": "Anime",
    "a cyberpunk futuristic neon city, glowing sci-fi scene, high tech dystopian city": "Cyberpunk",
    "a realistic natural landscape, green forest, mountains, waterfall, beach, or nature view": "Naturaleza",
    "a fantasy concept art, mythical dragon, magic spell, dark fantasy monster, or surreal magical world": "Fantasía",
    "a minimal flat color wallpaper, simple clean background with minimal vectors or isolated object": "Minimalista",
    "a sports car, super car, luxury vehicle, motorcycle, or automotive photography": "Autos",
    "a realistic urban city street, real life buildings, architecture, or city photography": "Urbano",
    "outer space, galaxy, cosmos, nebula, stars, planets, or astronomy photo": "Espacio",
    "an abstract 3d geometric render, fluid colorful artwork, wallpaper pattern, digital abstract graphics": "Abstracto"
}

candidate_prompts = list(category_prompts.keys())
categories_clean = list(category_prompts.values())

print("⏳ Cargando modelo de Clasificación de IA de Alta Precisión (CLIP Large)...")
try:
    # Usamos el modelo Large para máxima precisión de detección
    classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-large-patch14", device=-1)
except Exception as e:
    print(f"⚠️ No se pudo cargar el modelo CLIP Large: {e}. Se usará detección por palabras clave/fallback.")
    classifier = None

def send_discord_notification(total_items, total_vips, total_videos, new_count):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        print("ℹ️ No se encontró DISCORD_WEBHOOK, omitiendo notificación a Discord.")
        return

    payload = {
        "embeds": [{
            "title": "🚀 Wallpaper Pipeline Actualizado",
            "color": 3447003,
            "fields": [
                {"name": "Total Wallpapers", "value": str(total_items), "inline": True},
                {"name": "Fondos Nuevos", "value": str(new_count), "inline": True},
                {"name": "Fondos VIP", "value": str(total_vips), "inline": True},
                {"name": "Live Videos", "value": str(total_videos), "inline": True},
                {"name": "Estado", "value": "✅ JSON generado y publicado correctamente.", "inline": False}
            ],
            "footer": {"text": "ImpostorCore Auto-System"}
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print("✅ Notificación enviada a Discord con éxito.")
        else:
            print(f"❌ Error enviando notificación a Discord: {response.status_code}")
    except Exception as e:
        print(f"❌ Excepción al conectar con Discord: {e}")

def send_onesignal_notification(new_count, latest_item):
    app_id = os.environ.get("ONESIGNAL_APP_ID", "782f3005-fc46-45ab-a98a-f44a07537b65")
    rest_key = os.environ.get("ONESIGNAL_REST_KEY")

    if not rest_key:
        print("⚠️ No se encontró ONESIGNAL_REST_KEY, omitiendo notificación Push.")
        return

    if new_count <= 0 or not latest_item:
        print("ℹ️ No hay ítems nuevos para enviar notificación Push.")
        return

    titles_es = [
        "🔥 ¡Tu pantalla merece un cambio!",
        "✨ ¡Nuevo Fondo Exclusivo!",
        "🚀 ¡Renueva tu estilo ahora!",
        "🎨 ¡Nuevos Wallpapers Disponibles!"
    ]
    titles_en = [
        "🔥 Upgrade Your Screen Now!",
        "✨ Exclusive New Wallpaper!",
        "🚀 Fresh Style Update!",
        "🎨 New Wallpapers Available!"
    ]

    selected_title_es = random.choice(titles_es)
    selected_title_en = random.choice(titles_en)

    if new_count == 1:
        msg_es = f"😍 Agregamos '{latest_item.get('title', 'un nuevo fondo')}'. ¡Toca para verlo antes que nadie!"
        msg_en = f"😍 Just added '{latest_item.get('title', 'a new wallpaper')}'. Tap to check it out!"
    else:
        msg_es = f"⚡ Agregamos {new_count} nuevos fondos HD y AMOLED. ¡Entra y renueva tu pantalla!"
        msg_en = f"⚡ Added {new_count} new HD & AMOLED wallpapers. Check them out!"

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {rest_key}"
    }

    payload = {
        "app_id": app_id,
        "included_segments": ["All"],
        "headings": {"es": selected_title_es, "en": selected_title_en},
        "contents": {"es": msg_es, "en": msg_en},
        "big_picture": latest_item.get("thumbnail", ""),
        "large_icon": latest_item.get("thumbnail", ""),
        "chrome_web_image": latest_item.get("thumbnail", ""),
        "data": {
            "wallpaper_id": str(latest_item.get("id", "")),
            "category": str(latest_item.get("category", ""))
        }
    }

    try:
        response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"🚀 Notificación Push enviada a OneSignal con éxito ({new_count} nuevo/s).")
        else:
            print(f"❌ Error enviando Push a OneSignal: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Excepción conectando con OneSignal: {e}")

def optimize_video(input_path):
    temp_path = input_path + ".opt.mp4"
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale='min(1080,iw)':-2",
        "-c:v", "libx264", "-crf", "26", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        temp_path
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(temp_path, input_path)
    except Exception as e:
        print(f"Error optimizando video {input_path}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def generate_webp_thumbnail(file_path, output_webp_path, max_size=(720, 1280)):
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_webp_path, "WEBP", quality=75, optimize=True)
            return True
    except Exception as e:
        print(f"Error creando miniatura WebP {file_path}: {e}")
        return False

def extract_video_frame(video_path, output_jpg):
    try:
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            cv2.imwrite(output_jpg, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        cap.release()
        return success
    except Exception as e:
        print(f"Error extrayendo frame {video_path}: {e}")
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

def analyze_with_ai(file_name, file_path, is_video, temp_frame_path=None):
    if is_video:
        return "Live Video", False

    # 1. Comprobar si tiene prefijo manual obligatorio
    fn_lower = file_name.lower()
    for pref, cat in PREFIX_MAP.items():
        if fn_lower.startswith(pref) or f"_{pref}" in fn_lower:
            print(f"  └ Categoría asignada por PREFIJO: {cat}")
            return cat, fn_lower.startswith("vip_")

    # 2. Análisis mediante IA (CLIP Large)
    if not classifier:
        return "Todos", False

    try:
        target_path = temp_frame_path if (is_video and temp_frame_path and os.path.exists(temp_frame_path)) else file_path
        image = Image.open(target_path).convert("RGB")
        
        prediction = classifier(image, candidate_labels=candidate_prompts)
        best_prompt = prediction[0]['label']
        confidence = prediction[0]['score']

        # Ajuste de tolerancia
        if confidence < 0.28:
            best_category = "Todos"
        else:
            best_category = category_prompts[best_prompt]

        is_vip_ai = confidence > 0.65
        print(f"  └ AI Categoría: {best_category} ({round(confidence*100, 1)}%) | VIP: {is_vip_ai}")
        return best_category, is_vip_ai
    except Exception as e:
        print(f"  └ Error en IA ({e}), asignando 'Todos'")
        return "Todos", False

def format_title(filename):
    name = filename.rsplit(".", 1)[0]
    if name.lower().startswith("vip_"):
        name = name[4:]

    prefixes = ["an_", "cy_", "na_", "fa_", "mi_", "au_", "ur_", "es_", "ab_", "lv_"]
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
    return title if title else "Wallpaper"

# Creación de carpetas
os.makedirs(folder, exist_ok=True)
os.makedirs(thumbs_folder, exist_ok=True)

# Mover archivos sueltos a la carpeta /img
valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm")
for item in os.listdir("."):
    if item.lower().endswith(valid_extensions) and os.path.isfile(item):
        os.rename(item, os.path.join(folder, item))

# Leer el catálogo JSON anterior para identificar archivos NUEVOS
existing_file_names = set()
if os.path.exists("wallpapers.json"):
    try:
        with open("wallpapers.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            existing_file_names = {item.get("file_name") for item in old_data.get("wallpapers", []) if "file_name" in item}
    except Exception as e:
        print(f"⚠️ No se pudo leer wallpapers.json previo: {e}")

categories_list = ["Todos"] + categories_clean + ["Live Video"]
data = {"categories": categories_list, "wallpapers": []}

archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_") and os.path.isfile(os.path.join(folder, f))
]

print(f"\nProcesando {len(archivos)} archivos en {folder}...\n")

new_items = []

for i, archivo in enumerate(archivos):
    ruta_completa = os.path.join(folder, archivo)
    nombre_base = os.path.splitext(archivo)[0]
    
    es_vip_manual = archivo.lower().startswith("vip_")
    resolucion_real = get_media_info(ruta_completa)
    titulo_bonito = format_title(archivo)
    url_archivo = archivo.replace(" ", "%20")

    es_video = (
        archivo.lower().endswith((".mp4", ".webm"))
        or "live" in archivo.lower()
        or "lv_" in archivo.lower()
    )

    thumb_filename = f"{nombre_base}.webp"
    thumb_path = os.path.join(thumbs_folder, thumb_filename)

    temp_frame = None
    if es_video:
        optimize_video(ruta_completa)
        temp_frame = os.path.join(thumbs_folder, f"temp_{nombre_base}.jpg")
        if extract_video_frame(ruta_completa, temp_frame):
            generate_webp_thumbnail(temp_frame, thumb_path)
    else:
        generate_webp_thumbnail(ruta_completa, thumb_path)

    cat_detectada, is_vip_ai = analyze_with_ai(archivo, ruta_completa, es_video, temp_frame)

    if temp_frame and os.path.exists(temp_frame):
        os.remove(temp_frame)

    es_vip_final = es_vip_manual or is_vip_ai

    item_obj = {
        "id": str(i + 1),
        "title": titulo_bonito,
        "file_name": archivo,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": cat_detectada,
        "color": "blue",
        "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/thumbs/{thumb_filename}",
        "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{url_archivo}",
        "resolution": resolucion_real,
        "is_vip": es_vip_final
    }

    data["wallpapers"].append(item_obj)

    if archivo not in existing_file_names:
        new_items.append(item_obj)

# Guardar catálogo actualizado
with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n¡Listo! Generado wallpapers.json con {len(data['wallpapers'])} items.")

total_vips = sum(1 for w in data["wallpapers"] if w.get("is_vip"))
total_videos = sum(1 for w in data["wallpapers"] if w.get("is_video"))

send_discord_notification(len(data["wallpapers"]), total_vips, total_videos, len(new_items))

if len(new_items) > 0:
    ultimo_nuevo = new_items[-1]
    send_onesignal_notification(len(new_items), ultimo_nuevo)
else:
    print("ℹ️ No hay imágenes o videos nuevos en este despliegue. Se omite el envío de notificaciones Push.")
