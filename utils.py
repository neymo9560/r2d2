"""
R2D2 Bot - Utilitaires et Logging
==================================
Ici on met tous les petits outils pratiques pour le bot.
C'est comme la boîte à outils du robot ! 🔧
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
from dotenv import load_dotenv

# On charge les variables secrètes du fichier .env
load_dotenv()


# ============================================
# CONFIGURATION GLOBALE
# ============================================

class NetworkMode(Enum):
    """Mode réseau : testnet (paper) ou mainnet (réel)"""
    TESTNET = "testnet"
    MAINNET = "mainnet"


@dataclass
class BotConfig:
    """
    Configuration du bot R2D2
    Tous les paramètres sont ici, facile à modifier !
    """
    # Mode réseau
    network_mode: NetworkMode = NetworkMode.TESTNET
    
    # URLs API Hyperliquid
    # Testnet = argent fictif pour tester
    # Mainnet = ARGENT RÉEL attention !
    api_url_testnet: str = "https://api.hyperliquid-testnet.xyz"
    api_url_mainnet: str = "https://api.hyperliquid.xyz"
    
    # Arbitrum Chain IDs
    chain_id_testnet: int = 421614  # Arbitrum Sepolia
    chain_id_mainnet: int = 42161   # Arbitrum One
    
    # Assets à trader (les cryptos volatiles)
    assets: List[str] = field(default_factory=lambda: ["BTC", "ETH"])
    
    # === PARAMÈTRES GRID BOT (optimisés HFT) ===
    # Le grid, c'est comme un filet de pêche avec plusieurs niveaux
    # On place des ordres à différents prix pour attraper les rebonds
    # 🔥 Serré à 0.3% pour plus de triggers et cycles rapides !
    grid_size: float = 0.003   # 0.3% entre niveaux (serré = plus de trades)
    grid_levels: int = 4       # 4 buy + 4 sell = 8 pièges tendus 🎣
    
    # === PARAMÈTRES TRAILING STOP (agressif pour lock rapide) ===
    # Le trailing, c'est un stop-loss qui suit le prix quand ça monte
    # Dès qu'on est en profit, on verrouille ! 🔒
    trailing_activation: float = 0.0010  # Active dès +0.10% profit
    trailing_distance: float = 0.0008    # Suit à 0.08% (lock vite sans whipsaw)
    
    # === PARAMÈTRES RSI/MA (réactifs pour HFT) ===
    # RSI = Force du marché (0-100)
    # MA = Moyenne mobile (tendance)
    # 🚀 RSI période 7 = plus réactif que 14 pour le scalping
    rsi_period: int = 7        # Court pour réactivité HFT
    rsi_oversold: float = 28.0   # Un peu plus strict pour meilleurs signaux
    rsi_overbought: float = 72.0 # Idem pour shorts
    ma_fast: int = 5   # Moyenne rapide (5 périodes)
    ma_slow: int = 10  # Moyenne lente (10 périodes)
    
    # === ANTI-SLIPPAGE (strict pour HFT) ===
    # Slippage = quand le prix bouge entre l'ordre et l'exécution
    # On veut ZÉRO surprise sur chaque trade !
    max_spread_percent: float = 0.0005   # Max 0.05% de spread
    min_orderbook_depth: float = 50000   # Min $50k depth (top 10 levels)
    
    # === GESTION DU RISQUE (serrée pour thousands de trades) ===
    # C'est SUPER important pour pas tout perdre !
    # 🎯 TP +0.20% = sweet spot green rapide sans hold trop long
    # 🛑 SL -0.10% = strict, on coupe vite si ça part mal
    take_profit_percent: float = 0.0020   # +0.20% = vert rapide ! 🚀
    stop_loss_percent: float = 0.0010     # -0.10% = coupe stricte 🛑
    max_hold_seconds: int = 60            # Max 1 minute → force repeat
    position_size_percent: float = 0.001  # 0.1% capital (tiny pour volume)
    leverage_min: int = 1
    leverage_max: int = 5
    max_daily_drawdown: float = 0.02      # -2% max par jour = stop bot
    
    # === TIMING (ultra-rapide) ===
    scan_interval_seconds: float = 0.5  # Scan toutes les 0.5s pour HFT 🔥
    
    def get_api_url(self) -> str:
        """Retourne l'URL API selon le mode"""
        if self.network_mode == NetworkMode.MAINNET:
            return self.api_url_mainnet
        return self.api_url_testnet
    
    def get_chain_id(self) -> int:
        """Retourne le chain ID selon le mode"""
        if self.network_mode == NetworkMode.MAINNET:
            return self.chain_id_mainnet
        return self.chain_id_testnet
    
    def to_dict(self) -> Dict:
        """Convertit la config en dictionnaire"""
        data = asdict(self)
        data['network_mode'] = self.network_mode.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BotConfig':
        """Crée une config depuis un dictionnaire"""
        if 'network_mode' in data:
            data['network_mode'] = NetworkMode(data['network_mode'])
        return cls(**data)


# ============================================
# STRUCTURES DE DONNÉES
# ============================================

@dataclass
class Trade:
    """
    Un trade, c'est une opération d'achat ou vente
    On garde toutes les infos pour les stats !
    """
    id: str
    asset: str
    side: str  # "long" ou "short"
    entry_price: float
    exit_price: Optional[float] = None
    size: float = 0.0
    leverage: int = 1
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "open"  # open, closed, cancelled
    exit_reason: str = ""  # tp, sl, trailing, timeout, manual
    
    def is_winner(self) -> bool:
        """Est-ce qu'on a gagné sur ce trade ?"""
        return self.pnl > 0
    
    def duration_seconds(self) -> float:
        """Durée du trade en secondes"""
        end = self.exit_time or datetime.now()
        return (end - self.entry_time).total_seconds()


@dataclass 
class BotStats:
    """
    Statistiques du bot en temps réel
    C'est le tableau de score du robot !
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_percent: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    current_streak: int = 0  # Série de gains/pertes en cours
    max_win_streak: int = 0
    start_capital: float = 0.0
    current_capital: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    last_trade_time: Optional[datetime] = None
    
    @property
    def winrate(self) -> float:
        """Pourcentage de trades gagnants"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def update_from_trade(self, trade: Trade):
        """Met à jour les stats après un trade"""
        self.total_trades += 1
        self.total_pnl += trade.pnl
        self.last_trade_time = trade.exit_time or datetime.now()
        
        if trade.is_winner():
            self.winning_trades += 1
            self.current_streak = max(1, self.current_streak + 1)
            self.max_win_streak = max(self.max_win_streak, self.current_streak)
            self.best_trade = max(self.best_trade, trade.pnl)
        else:
            self.losing_trades += 1
            self.current_streak = min(-1, self.current_streak - 1)
            self.worst_trade = min(self.worst_trade, trade.pnl)
        
        # Mise à jour du capital
        self.current_capital += trade.pnl
        if self.start_capital > 0:
            self.total_pnl_percent = ((self.current_capital - self.start_capital) / self.start_capital) * 100


# ============================================
# LOGGING SYMPA
# ============================================

class R2D2Logger:
    """
    Logger personnalisé pour R2D2
    Affiche des messages sympas et colorés !
    """
    
    # Emojis pour différents types de messages
    EMOJIS = {
        'win': '🎉',
        'loss': '😢',
        'trade': '🤖',
        'info': 'ℹ️',
        'warning': '⚠️',
        'error': '❌',
        'start': '🚀',
        'stop': '🛑',
        'money': '💰',
        'chart': '📊',
        'rocket': '🚀',
        'fire': '🔥',
        'check': '✅',
    }
    
    def __init__(self, name: str = "R2D2"):
        self.name = name
        self.logs: List[Dict] = []
        self.lock = threading.Lock()
        
        # Configuration du logger standard
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(name)
    
    def _add_log(self, level: str, message: str, emoji: str = ""):
        """Ajoute un log à l'historique"""
        with self.lock:
            log_entry = {
                'time': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'emoji': emoji
            }
            self.logs.append(log_entry)
            # Garde seulement les 1000 derniers logs
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
    
    def info(self, message: str):
        """Message d'information standard"""
        emoji = self.EMOJIS['info']
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('info', message, emoji)
    
    def trade_win(self, asset: str, pnl_percent: float, pnl_usd: float):
        """
        Message quand on gagne un trade !
        C'est le moment de célébrer 🎉
        """
        emoji = self.EMOJIS['win']
        fire = self.EMOJIS['fire'] if pnl_percent > 0.2 else ""
        message = f"Trade GAGNÉ sur {asset} ! +{pnl_percent:.2f}% (+${pnl_usd:.2f}) {fire}"
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('win', message, emoji)
    
    def trade_loss(self, asset: str, pnl_percent: float, pnl_usd: float):
        """Message quand on perd un trade (ça arrive...)"""
        emoji = self.EMOJIS['loss']
        message = f"Trade perdu sur {asset} : {pnl_percent:.2f}% (${pnl_usd:.2f})"
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('loss', message, emoji)
    
    def trade_open(self, asset: str, side: str, price: float, size: float):
        """Message quand on ouvre un trade"""
        emoji = self.EMOJIS['trade']
        direction = "LONG 📈" if side == "long" else "SHORT 📉"
        message = f"Ouverture {direction} sur {asset} @ ${price:.2f} (taille: {size:.4f})"
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('trade', message, emoji)
    
    def warning(self, message: str):
        """Message d'avertissement"""
        emoji = self.EMOJIS['warning']
        full_msg = f"{emoji} {message}"
        self.logger.warning(full_msg)
        self._add_log('warning', message, emoji)
    
    def error(self, message: str):
        """Message d'erreur"""
        emoji = self.EMOJIS['error']
        full_msg = f"{emoji} {message}"
        self.logger.error(full_msg)
        self._add_log('error', message, emoji)
    
    def bot_start(self, mode: str):
        """Message au démarrage du bot"""
        emoji = self.EMOJIS['start']
        mode_emoji = "🔴 MAINNET" if mode == "mainnet" else "🟢 TESTNET"
        message = f"R2D2 démarre en mode {mode_emoji} ! Let's go !"
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('start', message, emoji)
    
    def bot_stop(self, reason: str = ""):
        """Message à l'arrêt du bot"""
        emoji = self.EMOJIS['stop']
        message = f"R2D2 s'arrête. {reason}"
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('stop', message, emoji)
    
    def stats_update(self, stats: BotStats):
        """Affiche un résumé des stats"""
        emoji = self.EMOJIS['chart']
        message = (f"Stats: {stats.winning_trades}/{stats.total_trades} gagnés "
                   f"({stats.winrate:.1f}%) | PnL: ${stats.total_pnl:.2f}")
        full_msg = f"{emoji} {message}"
        self.logger.info(full_msg)
        self._add_log('stats', message, emoji)
    
    def get_recent_logs(self, count: int = 50) -> List[Dict]:
        """Retourne les N derniers logs"""
        with self.lock:
            return self.logs[-count:]


# ============================================
# HELPERS UTILES
# ============================================

def get_env_var(key: str, default: str = "") -> str:
    """Récupère une variable d'environnement"""
    return os.getenv(key, default)


def is_mainnet_mode() -> bool:
    """Vérifie si on est en mode mainnet"""
    return get_env_var("MAINNET_MODE", "false").lower() == "true"


def get_private_key() -> str:
    """Récupère la clé privée (ATTENTION: sensible !)"""
    return get_env_var("PRIVATE_KEY", "")


def get_wallet_address() -> str:
    """Récupère l'adresse du wallet"""
    return get_env_var("WALLET_ADDRESS", "")


def get_infura_url(mainnet: bool = False) -> str:
    """Récupère l'URL Infura selon le réseau"""
    if mainnet:
        return get_env_var("INFURA_URL_MAINNET", "")
    return get_env_var("INFURA_URL_TESTNET", "")


def format_price(price: float, decimals: int = 2) -> str:
    """Formate un prix joliment"""
    return f"${price:,.{decimals}f}"


def format_percent(value: float, with_sign: bool = True) -> str:
    """Formate un pourcentage"""
    if with_sign and value > 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"


def format_pnl(pnl: float) -> str:
    """Formate un PnL avec couleur (texte)"""
    if pnl >= 0:
        return f"+${pnl:.2f} 🟢"
    return f"-${abs(pnl):.2f} 🔴"


def calculate_position_size(capital: float, percent: float, price: float, leverage: int = 1) -> float:
    """
    Calcule la taille de position
    Ex: Capital $10,000, 0.1% = $10 de risque
    Avec leverage 5x, on peut prendre $50 de position
    """
    risk_amount = capital * percent
    position_value = risk_amount * leverage
    return position_value / price


def calculate_pnl(entry_price: float, exit_price: float, size: float, side: str) -> Tuple[float, float]:
    """
    Calcule le PnL d'un trade
    Retourne (pnl_usd, pnl_percent)
    """
    if side == "long":
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
    else:  # short
        pnl_percent = ((entry_price - exit_price) / entry_price) * 100
    
    pnl_usd = size * entry_price * (pnl_percent / 100)
    return pnl_usd, pnl_percent


def generate_trade_id() -> str:
    """Génère un ID unique pour un trade"""
    import uuid
    return f"R2D2-{uuid.uuid4().hex[:8].upper()}"


def timestamp_to_datetime(ts: int) -> datetime:
    """Convertit un timestamp en datetime"""
    return datetime.fromtimestamp(ts / 1000)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convertit un datetime en timestamp"""
    return int(dt.timestamp() * 1000)


# ============================================
# VALIDATION
# ============================================

def validate_config(config: BotConfig) -> Tuple[bool, List[str]]:
    """
    Vérifie que la configuration est valide
    Retourne (is_valid, list_of_errors)
    """
    errors = []
    
    # Vérification des clés
    if not get_private_key():
        errors.append("PRIVATE_KEY manquante dans .env")
    
    if not get_wallet_address():
        errors.append("WALLET_ADDRESS manquante dans .env")
    
    # Vérification des paramètres
    if config.stop_loss_percent <= 0:
        errors.append("stop_loss_percent doit être > 0")
    
    if config.take_profit_percent <= 0:
        errors.append("take_profit_percent doit être > 0")
    
    if config.position_size_percent <= 0 or config.position_size_percent > 0.1:
        errors.append("position_size_percent doit être entre 0 et 10%")
    
    if config.leverage_max > 10:
        errors.append("leverage_max trop élevé (max recommandé: 10)")
    
    if not config.assets:
        errors.append("Au moins un asset requis")
    
    return len(errors) == 0, errors


# ============================================
# SINGLETON LOGGER GLOBAL
# ============================================

# Logger global utilisable partout
logger = R2D2Logger()


if __name__ == "__main__":
    # Test du module
    print("=== Test Utils R2D2 ===")
    
    # Test config
    config = BotConfig()
    print(f"Mode: {config.network_mode.value}")
    print(f"API URL: {config.get_api_url()}")
    print(f"Chain ID: {config.get_chain_id()}")
    
    # Test logger
    logger.info("Test de log info")
    logger.trade_win("BTC", 0.15, 12.50)
    logger.trade_loss("ETH", -0.08, -5.20)
    
    # Test calculs
    pnl_usd, pnl_pct = calculate_pnl(50000, 50150, 0.01, "long")
    print(f"PnL calculé: ${pnl_usd:.2f} ({pnl_pct:.2f}%)")
    
    print("\n✅ Utils OK !")
