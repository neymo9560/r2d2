# 🤖 R2D2 Bot - Scalper HFT pour Hyperliquid

Salut ! 👋 Bienvenue dans **R2D2**, ton bot de trading automatique ultra-rapide !

Ce robot enchaîne des mini-gains hyper vite sur Hyperliquid, un exchange décentralisé sur Arbitrum. Il utilise une stratégie hybride combinant **Grid Bot**, **Trailing Stop** et **indicateurs RSI/MA** pour maximiser les profits.

---

## 🎯 Ce que fait R2D2

- **Scalping ultra-rapide** : Des dizaines/centaines de trades par jour
- **Grid Bot** : Place un "filet" d'ordres pour attraper les rebonds
- **Trailing Stop** : Verrouille les profits dès +0.1%
- **Filtres RSI/MA** : Évite les mauvais moments pour trader
- **Anti-slippage** : Vérifie le carnet d'ordres avant chaque trade
- **Post-only orders** : Profite des rebates maker négatifs (-0.003%)
- **Gestion du risque** : Stop-loss à -0.1%, max drawdown -2%/jour

---

## ⚡ Installation Rapide

### Étape 1 : Installe Python
Télécharge Python 3.10+ depuis [python.org](https://www.python.org/downloads/)

### Étape 2 : Installe les dépendances

```bash
# Clone ou télécharge le projet, puis :
cd r2d2-bot

# Installe toutes les dépendances
pip install -r requirements.txt
```

**Ou installe manuellement :**
```bash
pip install hyperliquid-python-sdk web3 streamlit pandas numpy ta plotly python-dotenv aiohttp requests websockets
```

### Étape 3 : Configure ton .env

1. Copie le fichier `.env.example` en `.env`
2. Remplis tes clés :

```env
# Ta clé privée (ULTRA SECRET !)
PRIVATE_KEY=ta_cle_privee_sans_0x

# Ton adresse wallet
WALLET_ADDRESS=0xTonAdresse

# URL Infura (crée un compte gratuit sur infura.io)
INFURA_URL_TESTNET=https://arbitrum-sepolia.infura.io/v3/TA_CLE
INFURA_URL_MAINNET=https://arbitrum-mainnet.infura.io/v3/TA_CLE

# Mode (false = testnet, true = mainnet)
MAINNET_MODE=false

# Mots de passe UI
PASSWORD_CONTROL=Bine
PASSWORD_VIEWER=Bina
```

### Étape 4 : Lance l'interface !

```bash
streamlit run app.py
```

Ouvre ton navigateur sur `http://localhost:8501` et c'est parti ! 🚀

---

## 🎮 Comment utiliser

### Connexion

- **Mode Contrôle** (mot de passe: `Bine`) : Accès complet - start/stop, paramètres, trades
- **Mode Viewer** (mot de passe: `Bina`) : Lecture seule - dashboard, logs, graphiques

### Dashboard

Le dashboard affiche en temps réel :
- 💰 **PnL Total** : Tes gains/pertes
- 📊 **Winrate** : Pourcentage de trades gagnants
- 🔥 **Streak** : Série de victoires/défaites
- 📈 **Graphiques** : Courbe de capital et prix

### Modes Réseau

- **🟢 TESTNET** (Paper Trading) : Argent fictif pour tester - COMMENCE PAR ÇA !
- **🔴 MAINNET** : Argent réel - ATTENTION !

Clique sur "GO LIVE !" pour passer en mainnet (après avoir bien testé en paper !)

---

## 📁 Structure du Projet

```
r2d2-bot/
├── app.py          # Interface Streamlit (UI gamifiée)
├── main.py         # Cœur du bot, boucle de trading
├── strategy.py     # Stratégies (Grid, Trailing, RSI/MA)
├── backtest.py     # Test sur données historiques
├── utils.py        # Outils et logging
├── requirements.txt
├── .env.example    # Template de configuration
├── .env            # Ta config (NE PAS COMMIT !)
└── README.md
```

---

## 🔧 Paramètres de la Stratégie

### Grid Bot
- **Grid Size** : Écart entre les niveaux (défaut: 0.5%)
- **Grid Levels** : Nombre de niveaux (défaut: 5)

### Trailing Stop
- **Activation** : Seuil d'activation (défaut: +0.1%)
- **Distance** : Distance du stop (défaut: 0.05%)

### RSI/MA
- **RSI Oversold** : Seuil d'achat (défaut: 30)
- **RSI Overbought** : Seuil de vente (défaut: 70)
- **MA Fast/Slow** : Moyennes mobiles (5/10)

### Gestion du Risque
- **Stop Loss** : -0.1% par défaut
- **Take Profit** : +0.3% par défaut
- **Position Size** : 0.1% du capital
- **Leverage** : 1-5x dynamique
- **Max Drawdown** : -2% par jour (arrête le bot)

---

## 🧪 Backtest

Avant de trader en réel, teste ta stratégie sur des données historiques !

```bash
# Lance le backtest en ligne de commande
python backtest.py
```

Ou utilise l'onglet "Backtest" dans l'interface Streamlit.

**Exemple de résultats :**
```
╔══════════════════════════════════════════╗
║       RÉSULTATS BACKTEST R2D2            ║
╠══════════════════════════════════════════╣
║ 📊 Trades: 5000                          ║
║ ✅ Gagnants: 4100 (82.0%)                ║
║ 💰 PnL Total: $2,500.00                  ║
║ 📈 Rendement: +25.00%                    ║
║ 📉 Max Drawdown: -1.50%                  ║
╚══════════════════════════════════════════╝
```

---

## 🛠️ Mode Ligne de Commande

Tu peux aussi lancer le bot sans l'interface :

```bash
# Bot en mode standalone
python main.py
```

---

## ⚠️ AVERTISSEMENTS IMPORTANTS

### Risques

1. **Le trading de crypto est RISQUÉ** - Tu peux perdre ton argent
2. **Commence TOUJOURS en testnet** - Teste avant de risquer de l'argent réel
3. **Ce bot n'est PAS garanti rentable** - Les performances passées ne garantissent rien
4. **Commence PETIT** - Utilise une petite portion de ton capital
5. **Ne trade jamais plus que tu peux te permettre de perdre**

### Sécurité

1. **JAMAIS partager ta clé privée** - Elle donne accès à tous tes fonds
2. **Utilise un wallet dédié** - Pas ton wallet principal
3. **Le fichier .env ne doit JAMAIS être commit** - Il est dans .gitignore
4. **Vérifie les URLs API** - Méfie-toi du phishing

---

## 🐛 Debug / Problèmes Courants

### Le bot ne démarre pas
```bash
# Vérifie que toutes les dépendances sont installées
pip install -r requirements.txt

# Vérifie ton .env
cat .env  # (ou type .env sur Windows)
```

### Erreur de connexion API
- Vérifie ton URL Infura
- Vérifie ta connexion internet
- L'API Hyperliquid peut être temporairement down

### Erreur de wallet
- Vérifie que ta clé privée est correcte (sans le 0x)
- Vérifie que l'adresse correspond à la clé

### L'interface ne charge pas
```bash
# Relance Streamlit
streamlit run app.py --server.port 8502
```

---

## 📊 Comment ça marche (version simple)

1. **Le bot scanne le marché** toutes les 1-5 secondes
2. **Il regarde les indicateurs** (RSI, moyennes mobiles)
3. **Si les conditions sont bonnes** :
   - RSI < 30 + tendance haussière = ACHAT
   - RSI > 70 + tendance baissière = VENTE
4. **Il place un ordre** avec le bon sizing
5. **Le trailing stop protège les gains** dès +0.1%
6. **Le trade se ferme** automatiquement (TP, SL, ou timeout)
7. **On répète** à l'infini !

C'est comme un pêcheur qui jette et retire son filet en boucle pour attraper plein de petits poissons 🎣

---

## 🔗 Liens Utiles

- [Hyperliquid](https://hyperliquid.xyz) - L'exchange
- [Documentation API](https://hyperliquid.gitbook.io/hyperliquid-docs/) - Docs officielles
- [Infura](https://infura.io) - Provider Arbitrum
- [Python SDK](https://pypi.org/project/hyperliquid-python-sdk/) - SDK officiel

---

## 📝 Licence

Ce projet est fourni "tel quel" sans garantie. Utilise-le à tes propres risques.

---

## 🙏 Crédits

Créé avec ❤️ pour les traders qui veulent automatiser leur scalping sur Hyperliquid.

**Bonne chance et bon trading !** 🚀💰

---

*Rappel : Teste en paper trading avant le mainnet, commence petit, et ne risque jamais plus que tu peux perdre !*
