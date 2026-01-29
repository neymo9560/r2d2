# 🚀 Déployer R2D2 sur Oracle Cloud (GRATUIT À VIE)

## Étape 1 : Créer un compte Oracle Cloud (5 min)

1. Va sur **https://www.oracle.com/cloud/free/**
2. Clique sur **"Start for free"**
3. Remplis le formulaire :
   - Email
   - Mot de passe
   - Pays : France
   - **Region : Frankfurt (EU)** ← Important pour la latence !
4. Tu devras entrer une carte bancaire (ils ne débitent JAMAIS, c'est juste pour vérifier)
5. Attends la validation du compte (quelques minutes)

---

## Étape 2 : Créer une instance gratuite (10 min)

1. Connecte-toi à **https://cloud.oracle.com/**
2. Dans le menu hamburger (☰) → **Compute** → **Instances**
3. Clique **"Create Instance"**
4. Configure :
   - **Name** : `r2d2-bot`
   - **Image** : Ubuntu 22.04 (coche "Always Free Eligible")
   - **Shape** : Clique "Change Shape" → **Ampere** → **VM.Standard.A1.Flex**
     - OCPUs : **1** (tu peux mettre jusqu'à 4 gratuitement)
     - Memory : **6 GB** (tu peux mettre jusqu'à 24 gratuitement)
   - **Networking** : Laisse par défaut (Create new VCN)
   - **SSH Keys** : **Generate a key pair for me** → **Save Private Key** (GARDE CE FICHIER !)
5. Clique **"Create"**
6. Attends que l'instance soit "RUNNING" (2-3 min)
7. Note l'**adresse IP publique** affichée

---

## Étape 3 : Ouvrir le port 8501 (5 min)

1. Sur la page de ton instance, clique sur **"Virtual Cloud Network"** (lien bleu)
2. Clique sur **"Security Lists"** → **"Default Security List"**
3. Clique **"Add Ingress Rules"**
4. Ajoute cette règle :
   - **Source CIDR** : `0.0.0.0/0`
   - **Destination Port Range** : `8501`
   - **Description** : `Streamlit Dashboard`
5. Clique **"Add Ingress Rules"**

---

## Étape 4 : Se connecter au serveur (2 min)

### Sur Windows (avec PowerShell) :

```powershell
# Remplace par ton fichier clé et ton IP
ssh -i "C:\Users\TON_USER\Downloads\ssh-key.key" ubuntu@TON_IP_PUBLIQUE
```

### Si ça marche pas, utilise PuTTY :
1. Télécharge PuTTY : https://www.putty.org/
2. Convertis la clé avec PuTTYgen (Load → Save as .ppk)
3. Dans PuTTY : Host = ton IP, Connection → SSH → Auth → Browse ta clé .ppk

---

## Étape 5 : Installer le bot (5 min)

Une fois connecté au serveur, copie-colle ces commandes **une par une** :

```bash
# 1. Mise à jour
sudo apt update && sudo apt upgrade -y

# 2. Installer Docker
sudo apt install -y docker.io docker-compose git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 3. Se déconnecter et reconnecter (pour que Docker marche)
exit
```

Reconnecte-toi (refais la commande ssh), puis :

```bash
# 4. Cloner ton repo (REMPLACE PAR TON URL GITHUB)
git clone https://github.com/TON_USERNAME/windsurf-project.git r2d2
cd r2d2

# 5. Créer le fichier .env avec tes clés
nano .env
```

Dans nano, colle ceci (remplace les valeurs) :

```
NETWORK_MODE=testnet
PRIVATE_KEY=ta_cle_privee_ici
WALLET_ADDRESS=ton_adresse_wallet
CONTROL_PASSWORD=Bine
VIEWER_PASSWORD=Bina
```

Sauvegarde : `Ctrl+X` → `Y` → `Enter`

```bash
# 6. Lancer le bot !
docker-compose up -d

# 7. Vérifier que ça tourne
docker-compose logs -f
```

---

## Étape 6 : Accéder au dashboard 🎉

Ouvre ton navigateur et va sur :

```
http://TON_IP_PUBLIQUE:8501
```

**Mots de passe :**
- Mode Contrôle : `Bine`
- Mode Viewer : `Bina`

---

## 🔧 Commandes utiles

```bash
# Voir les logs en direct
docker-compose logs -f

# Arrêter le bot
docker-compose down

# Redémarrer le bot
docker-compose restart

# Mettre à jour le bot (après un git pull)
docker-compose up -d --build
```

---

## ⚠️ Avant de passer en MAINNET

1. Teste bien en **testnet** d'abord !
2. Commence avec un **petit capital** (genre $50-100)
3. Change `NETWORK_MODE=mainnet` dans le `.env`
4. Redémarre : `docker-compose up -d --build`

---

## 🆘 En cas de problème

### Le dashboard ne s'affiche pas
```bash
# Vérifier que le container tourne
docker ps

# Voir les erreurs
docker-compose logs

# Ouvrir le port dans le firewall Ubuntu
sudo iptables -I INPUT -p tcp --dport 8501 -j ACCEPT
```

### Erreur de connexion SSH
- Vérifie que tu utilises le bon fichier clé
- Vérifie que l'IP est correcte
- Sur Windows, la clé doit avoir les bonnes permissions

---

**C'est tout ! Ton bot R2D2 tourne maintenant 24/7 gratuitement ! 🤖🔥**
