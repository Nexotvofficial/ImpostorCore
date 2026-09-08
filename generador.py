import json
import os
import random
import re
import subprocess
import cv2
import requests
from PIL import Image
from google import genai

folder = "./img"
thumbs_folder = "./img/thumbs"

# Inicializar cliente de Google Gemini
gemini_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_key) if gemini_key else None

def send_discord_notification(total_items, total_vips, total_videos, new_count):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        print("ℹ️ No se encontró DISCORD_WEBHOOK, omitiendo notificación a Discord.")
        return

    payload = {
        "embeds": [{
            "title": "🚀 Wallpaper Pipeline Actualizado (Google Gemini AI)",
            "color": 3447003,
            "fields": [
                {"name": "Total Wallpapers", "value": str(total_items), "inline": True},
                {"name": "Fondos Nuevos", "value": str(new_count), "inline": True},
                {"name": "Fondos VIP", "value": str(total_vips), "inline": True},
                {"name": "Live Videos", "value": str(total_videos), "inline": True},
                {"name": "Estado", "value": "✅ JSON generado, analizado por IA y publicado.", "inline": False}
            ],
            "footer": {"text": "ImpostorCore Auto-System"}
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 204]:
            print("✅ Notificación enviada a Discord con éxito.")
    except Exception as e:
        print(f"❌ Error enviando a Discord: {e}")

def send_onesignal_notification(new_count, latest_item):
    app_id = os.environ.get("ONESIGNAL_APP_ID", "782f3005-fc46-45ab-a98a-f44a07537b65")
    rest_key = os.environ.get("ONESIGNAL_REST_KEY")

    if not rest_key or new_count <= 0 or not latest_item:
        print("ℹ️ Omitiendo notificación Push de OneSignal.")
        return

    titles_es = ["🔥 ¡Tu pantalla merece un cambio!", "✨ ¡Nuevo Fondo Exclusivo!", "🚀 ¡Renueva tu estilo ahora!", "🎨 ¡Nuevos Wallpapers Disponibles!"]
    titles_en = ["🔥 Upgrade Your Screen Now!", "✨ Exclusive New Wallpaper!", "🚀 Fresh Style Update!", "🎨 New Wallpapers Available!"]

    msg_es = f"😍 Agregamos '{latest_item.get('title', 'un nuevo fondo')}'. ¡Toca para verlo!" if new_count == 1 else f"⚡ Agregamos {new_count} nuevos fondos HD y AMOLED."
    msg_en = f"😍 Just added '{latest_item.get('title', 'a new wallpaper')}'. Check it out!" if new_count == 1 else f"⚡ Added {new_count} new HD wallpapers."

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {rest_key}"
    }

    payload = {
        "app_id": app_id,
        "included_segments": ["All"],
        "headings": {"es": random.choice(titles_es), "en": random.choice(titles_en)},
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
        response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload)
        if response.status_code == 200:
            print(f"🚀 Notificación Push enviada a OneSignal con éxito ({new_count} nuevo/s).")
    except Exception as e:
        print(f"❌ Error con OneSignal: {e}")

def get_dominant_hex_color(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB").resize((1, 1))
            color = img.getpixel((0, 0))
            return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
    except Exception:
        return "#121212"

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

def analyze_with_google_ai(file_path, is_video, temp_frame_path=None):
    if is_video:
        return {"category": "Live Video", "is_vip": True, "tags": ["live", "video", "animado"]}

    if not client:
        print("⚠️ GEMINI_API_KEY no configurada. Asignando valores por defecto.")
        return {"category": "Todos", "is_vip": False, "tags": []}

    try:
        target_path = temp_frame_path if (is_video and temp_frame_path and os.path.exists(temp_frame_path)) else file_path
        image = Image.open(target_path)

        prompt = """
        Analiza esta imagen para un catálogo de fondos de pantalla (wallpapers).
        Responde ÚNICAMENTE un JSON estricto sin bloques markdown:
        {
            "category": "Selecciona UNA sola de estas opciones exactas: [Anime, Cyberpunk, Naturaleza, Fantasía, Minimalista, Autos, Urbano, Espacio, Abstracto, Gaming]",
            "is_vip": true o false (true si la calidad artística, resolución o nivel de detalle es extremadamente alto),
            "tags": ["tag1", "tag2", "tag3"] (3 a 5 palabras clave sobre elementos visuales en español)
        }
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt]
        )

        clean_json = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)

        print(f"  └ Google AI -> Cat: {result.get('category')} | VIP: {result.get('is_vip')} | Tags: {result.get('tags')}")
        return result
    except Exception as e:
        print(f"  └ Error analizando con Google AI: {e}")
        return {"category": "Todos", "is_vip": False, "tags": []}

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

categories_list = ["Todos", "Anime", "Cyberpunk", "Naturaleza", "Fantasía", "Minimalista", "Autos", "Urbano", "Espacio", "Abstracto", "Gaming", "Live Video"]
data = {"categories": categories_list, "wallpapers": []}

archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_") and os.path.isfile(os.path.join(folder, f))
]

print(f"\nProcesando {len(archivos)} archivos en {folder} con Google Gemini AI...\n")

new_items = []

for i, archivo in enumerate(archivos):
    ruta_completa = os.path.join(folder, archivo)
    nombre_base = os.path.splitext(archivo)[0]
    
    es_vip_manual = archivo.lower().startswith("vip_")
    resolucion_real = get_media_info(ruta_completa)
    titulo_bonito = format_title(archivo)
    url_archivo = archivo.replace(" ", "%20")

    es_video = archivo.lower().endswith((".mp4", ".webm")) or "live" in archivo.lower() or "lv_" in archivo.lower()

    thumb_filename = f"{nombre_base}.webp"
    thumb_path = os.path.join(thumbs_folder, thumb_filename)

    temp_frame = None
    if es_video:
        optimize_video(ruta_completa)
        temp_frame = os.path.join(thumbs_folder, f"temp_{nombre_base}.jpg")
        if extract_video_frame(ruta_completa, temp_frame):
            generate_webp_thumbnail(temp_frame, thumb_path)
            hex_color = get_dominant_hex_color(temp_frame)
    else:
        generate_webp_thumbnail(ruta_completa, thumb_path)
        hex_color = get_dominant_hex_color(ruta_completa)

    ai_data = analyze_with_google_ai(ruta_completa, es_video, temp_frame)
    
    if temp_frame and os.path.exists(temp_frame):
        os.remove(temp_frame)

    es_vip_final = es_vip_manual or ai_data.get("is_vip", False)

    item_obj = {
        "id": str(i + 1),
        "title": titulo_bonito,
        "file_name": archivo,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": ai_data.get("category", "Todos"),
        "tags": ai_data.get("tags", []),
        "color": hex_color,
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

# Enviar reporte a Discord
send_discord_notification(len(data["wallpapers"]), total_vips, total_videos, len(new_items))

# Enviar Notificación Push a OneSignal si hay archivos nuevos
if len(new_items) > 0:
    send_onesignal_notification(len(new_items), new_items[-1])
else:
    print("ℹ️ No hay imágenes o videos nuevos en este despliegue. Se omite la notificación Push.")
