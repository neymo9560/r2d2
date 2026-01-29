# Dockerfile pour R2D2 Bot HFT
# ==============================
# Ce fichier permet de créer une "boîte" avec tout ce qu'il faut pour le bot

FROM python:3.11-slim

# Définir le dossier de travail
WORKDIR /app

# Copier les dépendances d'abord (pour le cache Docker)
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code du bot
COPY . .

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV NETWORK_MODE=testnet

# Exposer le port pour Streamlit
EXPOSE 8501

# Commande pour lancer le bot + dashboard
CMD ["sh", "-c", "python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
