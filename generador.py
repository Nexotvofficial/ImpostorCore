    import json
import os
import re
from PIL import Image

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


# Obtiene la resolución de fotos y asigna la de videos de forma segura sin romper Pillow
def get_media_info(file_path):
  ext = file_path.lower().rsplit(".", 1)[-1]

  # Si es video, asignamos resolución estándar directamente
  if ext in ["mp4", "webm", "gif"]:
    return "1080p Full HD"

  # Si es imagen, leemos sus píxeles reales con Pillow
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
    name = name[4:]  # Omitir el prefijo vip_ para detectar bien la categoría

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
  if (
      name.startswith("lv_")
      or "live" in name
      or name.endswith((".mp4", ".webm"))
  ):
    return "Live Video"
  return "Todos"


def format_title(filename):
  name = filename.rsplit(".", 1)[0]

  # Limpiar primero el prefijo vip_ si lo tiene
  if name.lower().startswith("vip_"):
    name = name[4:]

  prefixes = ["an_", "cy_", "na_", "fa_", "mi_", "lv_"]
  for pref in prefixes:
    if name.lower().startswith(pref):
      name = name[len(pref) :]
      break

  name = re.sub(r"\(\d+\)", "", name)
  name = name.replace("_", " ").replace("-", " ")
  trash_words = ["descarga", "img", "wallpaper", "foto", "copia"]
  for word in trash_words:
    name = re.sub(r"\b" + word + r"\b", "", name, flags=re.IGNORECASE)

  title = " ".join(name.split()).title()
  return title if title else "Live Wallpaper"


# Estructura principal
data = {"categories": categories, "wallpapers": []}

if not os.path.exists(folder):
  os.makedirs(folder)

# Acepta tanto imágenes como formatos de video
valid_extensions = (".jpg", ".jpeg", ".png", ".mp4", ".webm")
archivos = [
    f
    for f in os.listdir(folder)
    if f.lower().endswith(valid_extensions)
]

for i, archivo in enumerate(archivos):
  ruta_completa = os.path.join(folder, archivo)

  # Detección de VIP basada en el prefijo
  es_vip = archivo.lower().startswith("vip_")

  # Información y categoría
  resolucion_real = get_media_info(ruta_completa)
  cat_detectada = detect_category(archivo)
  titulo_bonito = format_title(archivo)
  url_archivo = archivo.replace(" ", "%20")

  # Detecta si es un archivo de video
  es_video = (
      archivo.lower().endswith((".mp4", ".webm"))
      or "live" in archivo.lower()
      or "lv_" in archivo.lower()
  )

  data["wallpapers"].append({
      "id": str(i + 1),
      "title": titulo_bonito,
      "type": "video" if es_video else "image",
      "category": cat_detectada,
      "color": "blue",
      "thumbnail": (
          "https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/"
          + url_archivo
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

print(
    f"¡Listo! JSON generado con éxito. Procesados {len(data['wallpapers'])}"
    " archivos."
)
