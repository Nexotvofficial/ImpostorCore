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


# Función para detectar la resolución exacta según el alto/ancho en píxeles
def get_image_info(image_path):
  try:
    with Image.open(image_path) as img:
      width, height = img.size
      max_dim = max(width, height)

      # Clasificación según dimensiones de la foto
      if max_dim >= 7680:
        resolution = "8K Ultra HD"
      elif max_dim >= 3840:
        resolution = "4K Ultra HD"
      elif max_dim >= 2560:
        resolution = "2K Quad HD"
      elif max_dim >= 1920:
        resolution = "1080p Full HD"
      elif max_dim >= 1280:
        resolution = "720p HD"
      else:
        resolution = "SD"

      return resolution
  except Exception:
    return "HD"


def detect_category(filename):
  name = filename.lower()
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
  if name.startswith("lv_") or "live" in name:
    return "Live Video"
  return "Todos"


def format_title(filename):
  name = filename.rsplit(".", 1)[0]
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
  return title if title else "Wallpaper HD"


# Estructura base
data = {"categories": categories, "wallpapers": []}

if not os.path.exists(folder):
  os.makedirs(folder)

archivos = [
    f
    for f in os.listdir(folder)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

for i, archivo in enumerate(archivos):
  ruta_completa = os.path.join(folder, archivo)

  # Detectamos resolución real
  resolucion_real = get_image_info(ruta_completa)

  cat_detectada = detect_category(archivo)
  titulo_bonito = format_title(archivo)
  url_archivo = archivo.replace(" ", "%20")

  data["wallpapers"].append({
      "id": str(i + 1),
      "title": titulo_bonito,
      "type": "video" if "live" in archivo.lower() else "image",
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
      "is_vip": False,
  })

with open("wallpapers.json", "w", encoding="utf-8") as f:
  json.dump(data, f, indent=2, ensure_ascii=False)

print(
    f"¡Listo! Procesadas {len(data['wallpapers'])} imágenes con resolución"
    " detectada."
)
