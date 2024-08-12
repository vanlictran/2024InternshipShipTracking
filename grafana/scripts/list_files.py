#!/usr/bin/env python3

import os
import json

# Chemin du répertoire à lister
directory = '/usr/share/nginx/html/datas/'

# Lister les fichiers dans le répertoire
files = os.listdir(directory)

# Générer un JSON avec les fichiers
result = {
    "files": files
}

# Retourner le JSON avec les en-têtes appropriés
print("Content-Type: application/json")
print()
print(json.dumps(result))
