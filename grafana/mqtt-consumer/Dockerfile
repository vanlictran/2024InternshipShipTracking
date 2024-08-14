# Utiliser une image Python officielle comme image de base
FROM python:3.9-slim-buster

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de l'application dans le conteneur
COPY . /app

# Copier et installer les dépendances
COPY requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y libpq-dev build-essential

RUN pip install --no-cache-dir -r requirements.txt

# Commande pour exécuter le script Python
CMD ["python", "consumer.py"]