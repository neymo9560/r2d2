#!/bin/bash
# ==============================================
# Script d'installation automatique R2D2 sur Oracle Cloud
# ==============================================
# Ce script fait TOUT pour toi ! Lance-le et c'est parti 🚀

echo "🤖 Installation de R2D2 Bot sur Oracle Cloud..."
echo "================================================"

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation de Docker
echo "🐳 Installation de Docker..."
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Créer le dossier pour le bot
echo "📁 Création du dossier r2d2..."
mkdir -p ~/r2d2
cd ~/r2d2

# Cloner le repo (tu devras mettre ton URL GitHub)
echo "📥 Clonage du repository..."
# git clone https://github.com/TON_USERNAME/r2d2-bot.git .

echo ""
echo "✅ Installation terminée !"
echo ""
echo "📝 Prochaines étapes :"
echo "   1. Clone ton repo : git clone https://github.com/TON_USERNAME/r2d2-bot.git"
echo "   2. Va dans le dossier : cd r2d2-bot"
echo "   3. Crée le fichier .env avec tes clés"
echo "   4. Lance le bot : docker-compose up -d"
echo ""
echo "🌐 Le dashboard sera accessible sur : http://TON_IP:8501"
echo ""
