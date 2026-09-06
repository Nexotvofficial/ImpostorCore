import json
import os
import re
import subprocess
import cv2
from PIL import Image
from transformers import pipeline

folder = "./img"

# Lista de categorías que la IA evaluará para clasificar cada imagen/video
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

print("Cargando modelo de Inteligencia Artificial (CLIP)...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# Comprime el video a 1080p con bitrate bajo usando FFmpeg
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
        print(f"Video optimizado exitosamente: {input_path}")
    except Exception as e:
        print(f"No se pudo optimizar el video {input_path}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Extrae miniatura JPG liviana del video
def extract_video_frame(video_path, output_jpg):
    try:
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            cv2.imwrite(output_jpg, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
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

def detect_category_ia(file_path, is_video, thumb_path=None):
    if is_video:
        return "Live Video"
    
    # Si es imagen, la analizamos visualmente con la IA
    try:
        target_path = thumb_path if (is_video and thumb_path and os.path.exists(thumb_path)) else file_path
        image = Image.open(target_path).convert("RGB")
        
        prediction = classifier(image, candidate_labels=categories)
        best_category = prediction[0]['label']
        confidence = round(prediction[0]['score'] * 100, 1)
        
        print(f"  └ AI detectó categoría: {best_category} ({confidence}%)")
        return best_category
    except Exception as e:
        print(f"  └ Error al clasificar con IA ({e}), usando 'Todos'")
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
    return title if title else "Wallpaper"

# Estructura del JSON de salida
categories_list = ["Todos"] + categories + ["Live Video"]
data = {"categories": categories_list, "wallpapers": []}

if not os.path.exists(folder):
    os.makedirs(folder)

valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm")
archivos = [
    f for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions) and not f.startswith("thumb_")
]

print(f"\nSe encontraron {len(archivos)} archivos en la carpeta {folder}:\n")

for i, archivo in enumerate(archivos):
    ruta_completa = os.path.join(folder, archivo)
    es_vip = archivo.lower().startswith("vip_")
    resolucion_real = get_media_info(ruta_completa)
    titulo_bonito = format_title(archivo)
    url_archivo = archivo.replace(" ", "%20")

    es_video = (
        archivo.lower().endswith((".mp4", ".webm"))
        or "live" in archivo.lower()
        or "lv_" in archivo.lower()
    )

    thumb_path = None
    if es_video:
        optimize_video(ruta_completa)
        nombre_base = os.path.splitext(archivo)[0]
        thumb_file = f"thumb_{nombre_base}.jpg"
        thumb_path = os.path.join(folder, thumb_file)

        if not os.path.exists(thumb_path):
            extract_video_frame(ruta_completa, thumb_path)

        url_thumbnail = thumb_file.replace(" ", "%20")
    else:
        url_thumbnail = url_archivo

    print(f"[{i+1}/{len(archivos)}] Procesando: {archivo}")
    cat_detectada = detect_category_ia(ruta_completa, es_video, thumb_path)

    data["wallpapers"].append({
        "id": str(i + 1),
        "title": titulo_bonito,
        "type": "video" if es_video else "image",
        "is_video": es_video,
        "category": cat_detectada,
        "color": "blue",
        "thumbnail": (
            "https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/"
            + url_thumbnail
        ),
        "hd_url": (
            "https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/"
            + url_archivo
        ),
        "resolution": resolucion_real,
        "is_vip": es_vip,
    })

with open("wallpapers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n¡Listo! JSON generado con éxito. Procesados {len(data['wallpapers'])} archivos.")
