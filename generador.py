import json
import os
import random
import re
import subprocess
import cv2
import requests
import numpy as np
from PIL import Image
from transformers import pipeline

folder = "./img"
thumbs_folder = "./img/thumbs"

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

# Prompts para generación de Tags inteligentes
tag_prompts = [
    "dark theme", "neon lights", "colorful", "character", "landscape", 
    "futuristic", "retro", "amoled black", "detailed artwork", "minimalist"
]

candidate_prompts = list(category_prompts.keys())
categories_clean = list(category_prompts.values())

print("⏳ Cargando modelo de Clasificación de IA de Alta Precisión (CLIP Large)...")
try:
    classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-large-patch14", device=-1)
except Exception as e:
    print(f"⚠️ No se pudo cargar el modelo CLIP Large: {e}. Se usará fallback.")
    classifier = None

def get_orientation_and_ratio(file_path):
    """Detección de Orientación y Relación de Aspecto"""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            ratio = round(width / height, 2)
            if width > height:
                orientation = "landscape"
            elif height > width:
                orientation = "portrait"
            else:
                orientation = "square"
            return orientation, ratio
    except Exception:
        return "portrait", 0.56

def extract_dominant_color_and_amoled(file_path):
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img_small = img.resize((100, 100))
            arr = np.array(img_small)
            
            black_pixels = np.sum(np.all(arr <= [15, 15, 15], axis=-1))
            total_pixels = 100 * 100
            # Se convierte explícitamente a bool nativo de Python para evitar np.bool_
            is_amoled = bool((black_pixels / total_pixels) >= 0.35)

            avg_color = arr.mean(axis=(0, 1)).astype(int)
            hex_color = f"#{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"
            return hex_color, is_amoled
    except Exception as e:
        print(f"Error analizando color/amoled en {file_path}: {e}")
        return "#121212", False

def generate_tags_and_score(image, confidence):
    """Buscador por Etiquetas de IA y Puntuación Estética (Aesthetic Score)"""
    tags = []
    if classifier:
        try:
            predictions = classifier(image, candidate_labels=tag_prompts)
            tags = [p['label'] for p in predictions if p['score'] > 0.25][:4]
        except Exception:
            pass

    score = round(min(9.9, max(5.0, (float(confidence) * 4.0) + 5.5)), 1)
    return tags, score

def send_discord_notification(total_items, total_vips, total_videos, new_count):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
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
                {"name": "Estado", "value": "✅ JSON generado con Score IA, Tags y Orientación.", "inline": False}
            ],
            "footer": {"text": "ImpostorCore Auto-System"}
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception:
        pass

def send_onesignal_notification(new_count, latest_item):
    app_id = os.environ.get("ONESIGNAL_APP_ID", "782f3005-fc46-45ab-a98a-f44a07537b65")
    rest_key = os.environ.get("ONESIGNAL_REST_KEY")

    if not rest_key or new_count <= 0 or not latest_item:
        return

    titles_es = ["🔥 ¡Tu pantalla merece un cambio!", "✨ ¡Nuevo Fondo Exclusivo!", "🎨 ¡Nuevos Wallpapers Disponibles!"]
    titles_en = ["🔥 Upgrade Your Screen Now!", "✨ Exclusive New Wallpaper!", "🎨 New Wallpapers Available!"]

    msg_es = f"😍 Agregamos '{latest_item.get('title', 'un nuevo fondo')}'. ¡Toca para verlo!" if new_count == 1 else f"⚡ Agregamos {new_count} nuevos fondos HD y AMOLED."
    msg_en = f"😍 Just added '{latest_item.get('title', 'a new wallpaper')}'." if new_count == 1 else f"⚡ Added {new_count} new HD & AMOLED wallpapers."

    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Basic {rest_key}"}
    payload = {
        "app_id": app_id,
        "included_segments": ["All"],
        "headings": {"es": random.choice(titles_es), "en": random.choice(titles_en)},
        "contents": {"es": msg_es, "en": msg_en},
        "big_picture": latest_item.get("thumbnail", ""),
        "large_icon": latest_item.get("thumbnail", ""),
        "data": {"wallpaper_id": str(latest_item.get("id", "")), "category": str(latest_item.get("category", ""))}
    }
    try:
        requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload, timeout=10)
    except Exception:
        pass

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
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def generate_webp_thumbnail(file_path, output_webp_path, max_size=(720, 1280)):
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_webp_path, "WEBP", quality=75, optimize=True)
            return True
    except Exception:
        return False

def extract_video_frame(video_path, output_jpg):
    try:
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            cv2.imwrite(output_jpg, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        cap.release()
        return success
    except Exception:
        return False

def get_media_info(file_path):
    ext = file_path.lower().rsplit(".", 1)[-1]
    if ext in ["mp4", "webm", "gif"]:
        return "1080p Full HD"
    try:
        with Image.open(file_path) as img:
            max_dim = max(img.size)
            if max_dim >= 3840:
                return "4K Ultra HD"
            elif max_dim >= 2560:
                return "2K Quad HD"
            elif max_dim >= 1920:
                return "1080p Full HD"
            else:
                return "HD"
    except Exception:
        return "1080p Full HD"

def analyze_with_ai(file_name, file_path, is_video, temp_frame_path=None):
    if is_video:
        return "Live Video", False, [], 8.0

    fn_lower = file_name.lower()
    for pref, cat in PREFIX_MAP.items():
        if fn_lower.startswith(pref) or f"_{pref}" in fn_lower:
            return cat, fn_lower.startswith("vip_"), [cat.lower()], 8.5

    if not classifier:
        return "Todos", False, [], 7.0

    try:
        target_path = temp_frame_path if (is_video and temp_frame_path and os.path.exists(temp_frame_path)) else file_path
        image = Image.open(target_path).convert("RGB")
        
        prediction = classifier(image, candidate_labels=candidate_prompts)
        confidence = float(prediction[0]['score'])
        best_category = "Todos" if confidence < 0.28 else category_prompts[prediction[0]['label']]

        tags, aesthetic_score = generate_tags_and_score(image, confidence)
        is_vip_ai = bool(confidence > 0.65 or aesthetic_score >= 8.8)

        return best_category, is_vip_ai, tags, aesthetic_score
    except Exception:
        return "Todos", False, [], 7.0

def format_title(filename):
    name = filename.rsplit(".", 1)[0]
    if name.lower().startswith("vip_"):
        name = name[4:]

    prefixes = ["an_", "cy_", "na_", "fa_", "mi_", "au_", "ur_", "es_", "ab_", "lv_"]
    for pref in prefixes:
        if name.lower().startswith(pref):
            name = name[len(pref):]
            break

    name = re.sub(r"\(\d+\)", "", name).replace("_", " ").replace("-", " ")
    trash_words = ["descarga", "img", "wallpaper", "foto", "copia"]
    for word in trash_words:
        name = re.sub(r"\b" + word + r"\b", "", name, flags=re.IGNORECASE)

    title = " ".join(name.split()).title()
    return title if title else "Wallpaper"

# Creación de carpetas
os.makedirs(folder, exist_ok=True)
os.makedirs(thumbs_folder, exist_ok=True)

valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm")
for item in os.listdir("."):
    if item.lower().endswith(valid_extensions) and os.path.isfile(item):
        os.rename(item, os.path.join(folder, item))

existing_file_names = set()
if os.path.exists("wallpapers.json"):
    try:
        with open("wallpapers.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            existing_file_names = {item.get("file_name") for item in old_data.get("wallpapers", []) if "file_name" in item}
    except Exception:
        pass

categories_list = ["Todos"] + categories_clean + ["Live Video"]
data = {"categories": categories_list, "wallpapers": []}

archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_") and os.path.isfile(os.path.join(folder, f))
]

print(f"\nProcesando {len(archivos)} archivos...\n")
new_items = []

for i, archivo in enumerate(archivos):
    ruta_completa = os.path.join(folder, archivo)
    nombre_base = os.path.splitext(archivo)[0]

    es_vip_manual = archivo.lower().startswith("vip_")
    resolucion_real = get_media_info(ruta_completa)
    titulo_bonito = format_title(archivo)
    url_archivo = archivo.replace(" ", "%20")

    es_video = bool(archivo.lower().endswith((".mp4", ".webm")) or "live" in archivo.lower() or "lv_" in archivo.lower())

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

    # Detección de Orientación y Colores
    orientation, aspect_ratio = get_orientation_and_ratio(temp_frame if (es_video and temp_frame) else ruta_completa)
    hex_color, is_amoled = extract_dominant_color_and_amoled(temp_frame if (es_video and temp_frame) else ruta_completa)

    # Análisis con IA (Tags y Aesthetic Score)
    cat_detectada, is_vip_ai, tags, aesthetic_score = analyze_with_ai(archivo, ruta_completa, es_video, temp_frame)

    if temp_frame and os.path.exists(temp_frame):
        os.remove(temp_frame)

    es_vip_final = bool(es_vip_manual or is_vip_ai)

    item_obj = {
        "id": str(i + 1),
        "title": titulo_bonito,
        "file_name": archivo,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": cat_detectada,
        "tags": tags,
        "color": hex_color,
        "is_amoled": is_amoled,
        "orientation": orientation,
        "aspect_ratio": aspect_ratio,
        "aesthetic_score": aesthetic_score,
        "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/thumbs/{thumb_filename}",
        "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{url_archivo}",
        "resolution": resolucion_real,
        "is_vip": es_vip_final
    }

    data["wallpapers"].append(item_obj)

    if archivo not in existing_file_names:
        new_items.append(item_obj)

# Conversión automática de tipos NumPy a tipos nativos durante la serialización a JSON
with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(
        data, 
        f, 
        indent=2, 
        ensure_ascii=False, 
        default=lambda x: x.item() if hasattr(x, 'item') else str(x)
    )

print(f"\n¡Listo! Generado wallpapers.json con {len(data['wallpapers'])} items.")

total_vips = sum(1 for w in data["wallpapers"] if w.get("is_vip"))
total_videos = sum(1 for w in data["wallpapers"] if w.get("is_video"))

send_discord_notification(len(data["wallpapers"]), total_vips, total_videos, len(new_items))

if len(new_items) > 0:
    send_onesignal_notification(len(new_items), new_items[-1])
