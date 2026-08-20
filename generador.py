import os
import json

# Lista de archivos en la carpeta img
carpeta = "./img"
archivos = os.listdir(carpeta)

# Estructura base
data = {
    "categories": ["Todos", "Anime", "Cyberpunk", "Naturaleza", "Live Video"],
    "wallpapers": []
}

for i, archivo in enumerate(archivos):
    if archivo.endswith((".jpg", ".jpeg", ".png")):
        data["wallpapers"].append({
            "id": str(i + 1),
            "title": archivo.split('.')[0],
            "type": "image",
            "category": "Todos", # Puedes cambiar esto con lógica simple
            "thumbnail": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo}",
            "hd_url": f"https://cdn.jsdelivr.net/gh/Nexotvofficial/ImpostorCore@main/img/{archivo}",
            "is_vip": False
        })

# Guardar el JSON
with open('wallpapers.json', 'w') as f:
    json.dump(data, f, indent=2)

print("¡JSON actualizado automáticamente!")
