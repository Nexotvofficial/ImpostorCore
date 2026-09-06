import json
import os
import re
import subprocess
import cv2
from PIL import Image
from transformers import pipeline

folder = "./img"
thumbs_folder = "./img/thumbs"

categories = [
    "Anime",
    "Cyberpunk",
    "Naturaleza",
    "Fantasía",
    "Minimalista",
    "Autos",
    "Urbano",
    "Espacio",
    "Abstracto"
]

print("Cargando modelo de Clasificación de IA (CLIP)...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

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
    """Crea una miniatura WebP comprimida al 75% para carga ultrarrápida en la app"""
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_webp_path, "WEBP", quality=75, optimize=True)
            return True
    except Exception as e:
        print(f"Error al crear miniatura WebP para {file_path}: {e}")
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
        print(f"Error generando frame para {video_path}: {e}")
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

def analyze_with_ai(file_path, is_video, temp_frame_path=None):
    if is_video:
        return "Live Video", False

    try:
        target_path = temp_frame_path if (is_video and temp_frame_path and os.path.exists(temp_frame_path)) else file_path
        image = Image.open(target_path).convert("RGB")
        
        # Clasificación de categoría
        prediction = classifier(image, candidate_labels=categories)
        best_category = prediction[0]['label']
        confidence = prediction[0]['score']

        # Detección de VIP por IA
        is_vip_ai = confidence > 0.60
        
        print(f"  └ AI Categoría: {best_category} ({round(confidence*100, 1)}%) | VIP sugerido: {is_vip_ai}")
        return best_category, is_vip_ai
    except Exception as e:
        print(f"  └ Error en IA ({e}), asignando categoría por defecto")
        return "Todos", False

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

categories_list = ["Todos"] + categories + ["Live Video"]
data = {"categories": categories_list, "wallpapers": []}

os.makedirs(folder, exist_ok=True)
os.makedirs(thumbs_folder, exist_ok=True)

# Mueve automáticamente archivos subidos por error a la raíz hacia img/
valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm")
for item in os.listdir("."):
    if item.lower().endswith(valid_extensions) and os.path.isfile(item):
        os.rename(item, os.path.join(folder, item))

archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_") and os.path.isfile(os.path.join(folder, f))
]

print(f"\nProcesando {len(archivos)} archivos en {folder}...\n")

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

    if es_video:
        optimize_video(ruta_completa)
        temp_frame = os.path.join(thumbs_folder, f"temp_{nombre_base}.jpg")
        
        if extract_video_frame(ruta_completa, temp_frame):
            generate_webp_thumbnail(temp_frame, thumb_path)
            if os.path.exists(temp_frame):
                os.remove(temp_frame)
    else:
        generate_webp_thumbnail(ruta_completa, thumb_path)

    cat_detectada, is_vip_ai = analyze_with_ai(ruta_completa, es_video)
    
    es_vip_final = es_vip_manual or is_vip_ai

    data["wallpapers"].append({
        "id": str(i + 1),
        "title": titulo_bonito,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": cat_detectada,
        "color": "blue",
        "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/thumbs/{thumb_filename}",
        "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{url_archivo}",
        "resolution": resolucion_real,
        "is_vip": es_vip_final
    })

with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n¡Listo! Generado wallpapers.json optimizado con {len(data['wallpapers'])} items.")
