import os
import json

# Configuración
folder = "./img"
# Aquí añadimos las categorías que faltaban
categories = ["Todos", "Anime", "Cyberpunk", "Naturaleza", "Fantasía", "Minimalista", "Live Video"]

# Función para clasificar automáticamente según el nombre del archivo
def detect_category(filename):
    name = filename.lower()
    if "fantasia" in name or "fantasía" in name: return "Fantasía"
    if "minimal" in name: return "Minimalista"
    if "cyber" in name: return "Cyberpunk"
    if "naturaleza" in name: return "Naturaleza"
    if "anime" in name: return "Anime"
    if "live" in name: return "Live Video"
    return "Todos"

data = {
    "categories": categories,
    "wallpapers": []
}

# Obtener lista de archivos
archivos = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

for i, archivo in enumerate(archivos):
    cat_detectada = detect_category(archivo)
    
    data["wallpapers"].append({
        "id": str(i + 1),
        "title": archivo.split('.')[0].replace("_", " ").title(), # Formato bonito para el título
        "type": "video" if "live" in archivo.lower() else "image",
        "category": cat_detectada,
        "color": "blue", # Puedes ajustar esto luego
        "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo.replace(' ', '%20')}",
        "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo.replace(' ', '%20')}",
        "resolution": "8K Ultra HD",
        "is_vip": False
    })

# Guardar el JSON
with open('wallpapers.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"¡Listo! JSON generado con {len(data['wallpapers'])} imágenes.")
