import os
import json

# Configuración
folder = "./img"
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

# Función para limpiar el nombre y dejarlo profesional
def format_title(filename):
    # 1. Quitamos la extensión (.jpg, .png)
    name = filename.rsplit('.', 1)[0]
    
    # 2. Reemplazamos guiones bajos o medios por espacios
    name = name.replace('_', ' ').replace('-', ' ')
    
    # 3. Lista de palabras "basura" que no queremos que salgan en el título
    # Asegúrate de escribir estas palabras en minúsculas aquí
    trash_words = ['descarga', 'img', 'wallpaper', 'foto', 'copia']
    
    for word in trash_words:
        # Reemplazamos tanto en minúsculas como en mayúsculas para limpiar bien
        name = name.replace(word, '', 1).replace(word.capitalize(), '', 1)
        
    # 4. Ponemos en mayúsculas la primera letra de cada palabra y limpiamos espacios extra
    return name.strip().title()

# Estructura base
data = {
    "categories": categories,
    "wallpapers": []
}

# Obtener lista de archivos
archivos = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

for i, archivo in enumerate(archivos):
    cat_detectada = detect_category(archivo)
    titulo_bonito = format_title(archivo) # Aquí se limpia el nombre
    
    data["wallpapers"].append({
        "id": str(i + 1),
        "title": titulo_bonito, 
        "type": "video" if "live" in archivo.lower() else "image",
        "category": cat_detectada,
        "color": "blue", 
        "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo.replace(' ', '%20')}",
        "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo.replace(' ', '%20')}",
        "resolution": "8K Ultra HD",
        "is_vip": False
    })

# Guardar el JSON
with open('wallpapers.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"¡Listo! JSON generado con {len(data['wallpapers'])} imágenes.")
