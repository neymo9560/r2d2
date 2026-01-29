"""
R2D2 Bot - Stratégies de Trading
=================================
Ici c'est le cerveau du robot ! 🧠
On combine plusieurs stratégies pour maximiser les gains :
- Grid Bot : Un filet d'ordres pour attraper les rebonds
- Trailing Stop : Un stop qui suit le prix pour verrouiller les gains
- RSI/MA : Des indicateurs pour savoir quand acheter/vendre
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np
import pandas as pd

from utils import (
    BotConfig, Trade, BotStats, logger,
    calculate_position_size, calculate_pnl, generate_trade_id
)


# ============================================
# INDICATEURS TECHNIQUES
# ============================================

class TechnicalIndicators:
    """
    Calcule les indicateurs techniques
    C'est comme les instruments de bord d'un avion ! 📊
    """
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """
        Calcule le RSI (Relative Strength Index)
        
        RSI < 30 = Survendu = Le prix a trop baissé = Moment d'ACHETER 📈
        RSI > 70 = Suracheté = Le prix a trop monté = Moment de VENDRE 📉
        RSI entre 30-70 = Zone neutre = On attend
        
        C'est comme un élastique : quand il est trop étiré, il revient !
        """
        if len(prices) < period + 1:
            return 50.0  # Valeur neutre si pas assez de données
        
        # Convertir en array numpy pour le calcul
        prices_array = np.array(prices[-period-1:])
        
        # Calculer les variations de prix
        deltas = np.diff(prices_array)
        
        # Séparer les gains et les pertes
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Moyenne des gains et pertes
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        # Éviter division par zéro
        if avg_loss == 0:
            return 100.0
        
        # Calcul RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> float:
        """
        Calcule la Moyenne Mobile (Moving Average)
        
        C'est la moyenne des X derniers prix.
        Si MA rapide > MA lente = Tendance haussière 📈
        Si MA rapide < MA lente = Tendance baissière 📉
        """
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """
        Calcule l'EMA (Exponential Moving Average)
        Comme la MA mais donne plus de poids aux prix récents
        """
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        prices_array = np.array(prices[-period*2:])
        multiplier = 2 / (period + 1)
        ema = prices_array[0]
        
        for price in prices_array[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> float:
        """
        Calcule la volatilité (écart-type des rendements)
        
        Haute volatilité = Prix qui bouge beaucoup = Plus de risque MAIS plus d'opportunités
        Basse volatilité = Prix stable = Moins d'opportunités
        """
        if len(prices) < period:
            return 0.01  # Valeur par défaut
        
        prices_array = np.array(prices[-period:])
        returns = np.diff(prices_array) / prices_array[:-1]
        
        return float(np.std(returns))
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """
        Calcule les Bandes de Bollinger
        
        - Bande haute : Prix élevé = potentiel de vente
        - Bande basse : Prix bas = potentiel d'achat
        - Bande moyenne : La moyenne mobile
        """
        if len(prices) < period:
            current = prices[-1] if prices else 0
            return current * 1.02, current, current * 0.98
        
        prices_array = np.array(prices[-period:])
        middle = np.mean(prices_array)
        std = np.std(prices_array)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return float(upper), float(middle), float(lower)


# ============================================
# ANALYSE DU CARNET D'ORDRES (ORDERBOOK)
# ============================================

@dataclass
class OrderbookAnalysis:
    """
    Analyse du carnet d'ordres
    Le carnet montre tous les ordres d'achat et vente en attente
    """
    bid_price: float = 0.0      # Meilleur prix d'achat
    ask_price: float = 0.0      # Meilleur prix de vente
    spread: float = 0.0         # Écart bid-ask
    spread_percent: float = 0.0 # Spread en %
    bid_depth: float = 0.0      # Profondeur côté achat (en $)
    ask_depth: float = 0.0      # Profondeur côté vente (en $)
    is_liquid: bool = False     # Assez de liquidité ?
    is_spread_ok: bool = False  # Spread acceptable ?
    
    @property
    def can_trade(self) -> bool:
        """Peut-on trader en sécurité ?"""
        return self.is_liquid and self.is_spread_ok


class OrderbookAnalyzer:
    """
    Analyseur du carnet d'ordres
    Vérifie qu'on peut trader sans trop de slippage (glissement de prix)
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
    
    def analyze(self, orderbook: Dict) -> OrderbookAnalysis:
        """
        Analyse un carnet d'ordres
        
        Le format attendu :
        {
            "bids": [[price, size], ...],  # Ordres d'achat
            "asks": [[price, size], ...]   # Ordres de vente
        }
        """
        analysis = OrderbookAnalysis()
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return analysis
        
        # Meilleurs prix
        analysis.bid_price = float(bids[0][0])
        analysis.ask_price = float(asks[0][0])
        
        # Spread (écart entre achat et vente)
        # Un spread élevé = coût caché sur chaque trade !
        analysis.spread = analysis.ask_price - analysis.bid_price
        analysis.spread_percent = (analysis.spread / analysis.bid_price) * 100
        
        # Profondeur du carnet (combien de $ disponibles)
        # On veut assez de liquidité pour pas faire bouger le prix
        analysis.bid_depth = sum(float(b[0]) * float(b[1]) for b in bids[:10])
        analysis.ask_depth = sum(float(a[0]) * float(a[1]) for a in asks[:10])
        
        # Vérifications anti-slippage
        # On skip le trade si les conditions sont mauvaises
        analysis.is_spread_ok = analysis.spread_percent <= (self.config.max_spread_percent * 100)
        analysis.is_liquid = min(analysis.bid_depth, analysis.ask_depth) >= self.config.min_orderbook_depth
        
        return analysis


# ============================================
# SIGNAUX DE TRADING
# ============================================

class SignalType(Enum):
    """Types de signaux"""
    LONG = "long"   # Acheter
    SHORT = "short" # Vendre à découvert
    HOLD = "hold"   # Attendre


@dataclass
class TradingSignal:
    """
    Un signal de trading
    C'est la décision du robot : acheter, vendre ou attendre
    """
    signal_type: SignalType
    asset: str
    price: float
    confidence: float = 0.0  # 0-1, confiance dans le signal
    reason: str = ""
    rsi: float = 50.0
    ma_fast: float = 0.0
    ma_slow: float = 0.0
    volatility: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================
# GRID BOT
# ============================================

@dataclass
class GridLevel:
    """
    Un niveau de la grille
    C'est comme un piège à poisson à un certain prix !
    """
    price: float
    side: str  # "buy" ou "sell"
    size: float
    is_active: bool = True
    order_id: Optional[str] = None


class GridStrategy:
    """
    Stratégie Grid Bot
    
    Imagine un filet de pêche avec plusieurs niveaux :
    - On place des ordres d'ACHAT sous le prix actuel
    - On place des ordres de VENTE au-dessus du prix actuel
    - Quand le prix rebondit, on attrape les petits mouvements !
    
    C'est parfait pour les marchés qui oscillent (range)
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.grids: Dict[str, List[GridLevel]] = {}  # Grilles par asset
    
    def create_grid(self, asset: str, current_price: float, capital: float) -> List[GridLevel]:
        """
        Crée une grille d'ordres autour du prix actuel
        
        Exemple avec grid_size=0.5% et 5 niveaux :
        Prix actuel: $50,000
        - Achat niveau 1: $49,750 (-0.5%)
        - Achat niveau 2: $49,500 (-1.0%)
        - Vente niveau 1: $50,250 (+0.5%)
        - Vente niveau 2: $50,500 (+1.0%)
        """
        levels = []
        size_per_level = calculate_position_size(
            capital, 
            self.config.position_size_percent / self.config.grid_levels,
            current_price,
            1
        )
        
        # Créer les niveaux d'achat (sous le prix)
        for i in range(1, self.config.grid_levels + 1):
            price = current_price * (1 - self.config.grid_size * i)
            levels.append(GridLevel(
                price=price,
                side="buy",
                size=size_per_level
            ))
        
        # Créer les niveaux de vente (au-dessus du prix)
        for i in range(1, self.config.grid_levels + 1):
            price = current_price * (1 + self.config.grid_size * i)
            levels.append(GridLevel(
                price=price,
                side="sell",
                size=size_per_level
            ))
        
        self.grids[asset] = levels
        logger.info(f"Grille créée pour {asset}: {len(levels)} niveaux autour de ${current_price:.2f}")
        
        return levels
    
    def check_grid_triggers(self, asset: str, current_price: float) -> List[GridLevel]:
        """
        Vérifie quels niveaux de la grille sont déclenchés
        Retourne les niveaux à exécuter
        """
        if asset not in self.grids:
            return []
        
        triggered = []
        for level in self.grids[asset]:
            if not level.is_active:
                continue
            
            # Niveau d'achat déclenché si prix <= niveau
            if level.side == "buy" and current_price <= level.price:
                triggered.append(level)
                level.is_active = False
            
            # Niveau de vente déclenché si prix >= niveau
            elif level.side == "sell" and current_price >= level.price:
                triggered.append(level)
                level.is_active = False
        
        return triggered
    
    def reset_grid(self, asset: str):
        """Remet la grille à zéro"""
        if asset in self.grids:
            del self.grids[asset]


# ============================================
# TRAILING STOP
# ============================================

@dataclass
class TrailingStopState:
    """
    État du trailing stop pour une position
    """
    is_active: bool = False
    highest_price: float = 0.0  # Plus haut atteint (pour long)
    lowest_price: float = float('inf')  # Plus bas atteint (pour short)
    stop_price: float = 0.0
    entry_price: float = 0.0
    side: str = ""


class TrailingStopStrategy:
    """
    Stratégie Trailing Stop
    
    C'est un stop-loss intelligent qui SUIT le prix quand ça monte !
    
    Exemple pour un LONG :
    1. On achète à $50,000
    2. Le prix monte à $50,150 (+0.3%) -> Trailing s'active !
    3. Stop placé à $50,100 (distance 0.1%)
    4. Prix monte à $50,200 -> Stop suit à $50,150
    5. Prix redescend à $50,150 -> STOP déclenché = On vend avec profit !
    
    Comme ça, on laisse courir les gains mais on les protège 🛡️
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.states: Dict[str, TrailingStopState] = {}  # État par trade_id
    
    def initialize(self, trade_id: str, entry_price: float, side: str):
        """Initialise le trailing pour un nouveau trade"""
        self.states[trade_id] = TrailingStopState(
            is_active=False,
            highest_price=entry_price if side == "long" else float('inf'),
            lowest_price=entry_price if side == "short" else float('inf'),
            stop_price=0.0,
            entry_price=entry_price,
            side=side
        )
    
    def update(self, trade_id: str, current_price: float, volatility: float = 0.01) -> Tuple[bool, float]:
        """
        Met à jour le trailing stop avec ajustement dynamique selon la volatilité 📈
        
        En haute volatilité (>0.02), on élargit le trailing pour éviter les whipsaws !
        Retourne (should_close, stop_price)
        """
        if trade_id not in self.states:
            return False, 0.0
        
        state = self.states[trade_id]
        
        # 🔥 Ajustement dynamique : si marché volatile, on élargit le trailing
        # Ça évite de se faire sortir par des mèches random
        trailing_distance = self.config.trailing_distance
        if volatility > 0.02:
            trailing_distance *= 1.2  # +20% de marge en haute vol
        
        if state.side == "long":
            # Calcul du profit actuel
            profit_percent = (current_price - state.entry_price) / state.entry_price
            
            # Active le trailing si on atteint le seuil (+0.10%)
            if profit_percent >= self.config.trailing_activation:
                if not state.is_active:
                    state.is_active = True
                    logger.info(f"🔒 Trailing activé ! Profit: +{profit_percent*100:.2f}%")
            
            # Met à jour le plus haut et fait suivre le stop
            if current_price > state.highest_price:
                state.highest_price = current_price
                old_stop = state.stop_price
                state.stop_price = current_price * (1 - trailing_distance)
                if state.is_active and old_stop > 0:
                    logger.info(f"📈 Trailing mis à jour : stop à ${state.stop_price:.2f}")
            
            # Vérifie si le stop est touché = on LOCK le green !
            if state.is_active and current_price <= state.stop_price:
                return True, state.stop_price
        
        else:  # short
            # Calcul du profit actuel
            profit_percent = (state.entry_price - current_price) / state.entry_price
            
            # Active le trailing si on atteint le seuil
            if profit_percent >= self.config.trailing_activation:
                if not state.is_active:
                    state.is_active = True
                    logger.info(f"🔒 Trailing activé ! Profit: +{profit_percent*100:.2f}%")
            
            # Met à jour le plus bas et fait suivre le stop
            if current_price < state.lowest_price:
                state.lowest_price = current_price
                old_stop = state.stop_price
                state.stop_price = current_price * (1 + trailing_distance)
                if state.is_active and old_stop > 0:
                    logger.info(f"📉 Trailing mis à jour : stop à ${state.stop_price:.2f}")
            
            # Vérifie si le stop est touché = on LOCK le green !
            if state.is_active and current_price >= state.stop_price:
                return True, state.stop_price
        
        return False, state.stop_price
    
    def remove(self, trade_id: str):
        """Supprime l'état du trailing"""
        if trade_id in self.states:
            del self.states[trade_id]


# ============================================
# STRATÉGIE HYBRIDE PRINCIPALE
# ============================================

class HybridScalpingStrategy:
    """
    Stratégie Hybride de Scalping R2D2
    
    Combine le meilleur de 3 mondes :
    1. Grid Bot : Attrape les rebonds dans un range
    2. Trailing Stop : Protège et maximise les profits
    3. RSI/MA : Filtre les mauvais moments
    
    Le but : Enchaîner des dizaines de petits trades gagnants !
    Vise +0.1% à +0.3% par trade, des centaines de fois par jour.
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.grid = GridStrategy(config)
        self.trailing = TrailingStopStrategy(config)
        self.orderbook_analyzer = OrderbookAnalyzer(config)
        self.indicators = TechnicalIndicators()
        
        # Historique des prix par asset
        self.price_history: Dict[str, List[float]] = {}
        self.max_history = 100  # Garde les 100 derniers prix
        
        # Trades actifs
        self.active_trades: Dict[str, Trade] = {}
    
    def update_price(self, asset: str, price: float):
        """Met à jour l'historique des prix"""
        if asset not in self.price_history:
            self.price_history[asset] = []
        
        self.price_history[asset].append(price)
        
        # Limite la taille de l'historique
        if len(self.price_history[asset]) > self.max_history:
            self.price_history[asset] = self.price_history[asset][-self.max_history:]
    
    def get_indicators(self, asset: str) -> Dict[str, float]:
        """
        Calcule tous les indicateurs pour un asset
        C'est le tableau de bord du pilote !
        """
        prices = self.price_history.get(asset, [])
        
        if len(prices) < 15:
            # Pas assez de données
            return {
                'rsi': 50.0,
                'ma_fast': prices[-1] if prices else 0,
                'ma_slow': prices[-1] if prices else 0,
                'volatility': 0.01,
                'bb_upper': 0,
                'bb_middle': 0,
                'bb_lower': 0
            }
        
        rsi = self.indicators.calculate_rsi(prices, self.config.rsi_period)
        ma_fast = self.indicators.calculate_ma(prices, self.config.ma_fast)
        ma_slow = self.indicators.calculate_ma(prices, self.config.ma_slow)
        volatility = self.indicators.calculate_volatility(prices)
        bb_upper, bb_middle, bb_lower = self.indicators.calculate_bollinger_bands(prices)
        
        return {
            'rsi': rsi,
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
            'volatility': volatility,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower
        }
    
    def calculate_dynamic_leverage(self, volatility: float) -> int:
        """
        Calcule le levier dynamique selon la volatilité
        
        Haute volatilité = Levier bas (plus prudent)
        Basse volatilité = Levier plus élevé (on peut se permettre)
        """
        # Volatilité normale autour de 0.01-0.02
        if volatility > 0.03:
            return self.config.leverage_min  # Très volatile = levier min
        elif volatility > 0.02:
            return 2
        elif volatility > 0.01:
            return 3
        else:
            return self.config.leverage_max  # Calme = on peut augmenter
    
    def generate_signal(self, asset: str, current_price: float, orderbook: Dict) -> TradingSignal:
        """
        Génère un signal de trading optimisé HFT 🚀
        
        C'est LE moment où le robot décide : j'achète, je vends, ou j'attends ?
        
        Conditions pour LONG (achat) :
        - RSI < 28 (survendu = le prix a trop baissé) 
        - MA rapide > MA lente (tendance qui repart à la hausse)
        - Volatilité suffisante (>0.5%) pour du mouvement
        - Spread OK et liquidité OK
        
        Conditions pour SHORT (vente) :
        - RSI > 72 (suracheté = le prix a trop monté)
        - MA rapide < MA lente (tendance qui repart à la baisse)
        - Mêmes filtres vol/spread
        """
        # Mettre à jour le prix
        self.update_price(asset, current_price)
        
        # Analyser le carnet d'ordres
        ob_analysis = self.orderbook_analyzer.analyze(orderbook)
        
        # Obtenir les indicateurs
        indicators = self.get_indicators(asset)
        
        # Signal par défaut : attendre
        signal = TradingSignal(
            signal_type=SignalType.HOLD,
            asset=asset,
            price=current_price,
            rsi=indicators['rsi'],
            ma_fast=indicators['ma_fast'],
            ma_slow=indicators['ma_slow'],
            volatility=indicators['volatility']
        )
        
        rsi = indicators['rsi']
        ma_fast = indicators['ma_fast']
        ma_slow = indicators['ma_slow']
        volatility = indicators['volatility']
        
        # 🔥 FILTRE VOLATILITÉ : Si le marché dort, on attend qu'il se réveille !
        # Pas de mouvement = pas d'opportunité de scalping
        if volatility < 0.005:
            signal.reason = "Trop calme, on attend du mouvement 🔥"
            return signal
        
        # 🚨 FILTRE ZONE NEUTRE RSI : On évite la zone 40-60
        # C'est le "no man's land" où le marché hésite
        if 40 <= rsi <= 60:
            signal.reason = f"RSI en zone neutre ({rsi:.1f}) - on attend un extrême"
            return signal
        
        # Vérification anti-slippage (spread et liquidité)
        if not ob_analysis.can_trade:
            if not ob_analysis.is_spread_ok:
                signal.reason = f"Spread trop élevé ({ob_analysis.spread_percent:.3f}%)"
            else:
                signal.reason = f"Liquidité insuffisante (${ob_analysis.bid_depth:.0f})"
            return signal
        
        # Condition LONG : RSI survendu + MA haussière
        if rsi < self.config.rsi_oversold and ma_fast > ma_slow:
            signal.signal_type = SignalType.LONG
            signal.confidence = min(1.0, (self.config.rsi_oversold - rsi) / 30)
            signal.reason = f"RSI survendu ({rsi:.1f}) + MA haussière 🟢"
            logger.info(f"🟢 Signal LONG sur {asset}: {signal.reason}")
        
        # Condition SHORT : RSI suracheté + MA baissière
        elif rsi > self.config.rsi_overbought and ma_fast < ma_slow:
            signal.signal_type = SignalType.SHORT
            signal.confidence = min(1.0, (rsi - self.config.rsi_overbought) / 30)
            signal.reason = f"RSI suracheté ({rsi:.1f}) + MA baissière 🔴"
            logger.info(f"🔴 Signal SHORT sur {asset}: {signal.reason}")
        
        # Vérifier aussi les niveaux de grille (attrape les rebonds !)
        triggered_levels = self.grid.check_grid_triggers(asset, current_price)
        if triggered_levels:
            level = triggered_levels[0]
            if level.side == "buy":
                signal.signal_type = SignalType.LONG
                signal.reason = f"Grille touchée 🎣 Niveau ${level.price:.2f}"
                logger.info(f"🎣 Grille déclenchée: LONG {asset} @ ${level.price:.2f}")
            else:
                signal.signal_type = SignalType.SHORT
                signal.reason = f"Grille touchée 🎣 Niveau ${level.price:.2f}"
                logger.info(f"🎣 Grille déclenchée: SHORT {asset} @ ${level.price:.2f}")
        
        return signal
    
    def should_close_position(self, trade: Trade, current_price: float, volatility: float = 0.01) -> Tuple[bool, str]:
        """
        Vérifie si on doit fermer une position - Optimisé HFT ! 🚀
        
        ORDRE DE PRIORITÉ (important pour maximiser les greens) :
        1. 🔒 Trailing Stop (premier check - lock les gains dès +0.10%)
        2. 🎯 Take Profit fixe (+0.20% = on prend le vert rapide)
        3. ⏰ Timeout (max 1 minute - force le repeat)
        4. 🛑 Stop Loss (-0.10% - on coupe vite si ça part mal)
        """
        # Calcul du PnL actuel
        if trade.side == "long":
            pnl_percent = ((current_price - trade.entry_price) / trade.entry_price)
        else:
            pnl_percent = ((trade.entry_price - current_price) / trade.entry_price)
        
        # 1. 🔒 TRAILING STOP (priorité #1 - verrouille les gains !)
        # C'est le plus important : dès qu'on est vert, on protège
        should_trail, stop_price = self.trailing.update(trade.id, current_price, volatility)
        if should_trail:
            logger.info(f"🎉 Green locké par trailing ! +{pnl_percent*100:.2f}% sur {trade.asset}")
            return True, "trailing"
        
        # 2. 🎯 TAKE PROFIT fixe (+0.20%)
        # Si on atteint le TP avant que le trailing se déclenche
        if pnl_percent >= self.config.take_profit_percent:
            logger.info(f"🚀 Vert rapide chopé ! +{pnl_percent*100:.2f}% sur {trade.asset}")
            return True, "tp"
        
        # 3. ⏰ TIMEOUT (max 1 minute)
        # Force le repeat même si pas encore TP/SL
        elapsed = (datetime.now() - trade.entry_time).total_seconds()
        if elapsed >= self.config.max_hold_seconds:
            result = "🟢" if pnl_percent > 0 else "🔴"
            logger.info(f"⏰ Timeout 1min ! {result} {pnl_percent*100:.2f}% sur {trade.asset}")
            return True, "timeout"
        
        # 4. 🛑 STOP LOSS (-0.10%)
        # Dernière protection - on coupe les pertes vite !
        if pnl_percent <= -self.config.stop_loss_percent:
            logger.info(f"🛑 Stop Loss touché ! {pnl_percent*100:.2f}% sur {trade.asset} - next !")
            return True, "sl"
        
        return False, ""
    
    def open_trade(self, signal: TradingSignal, capital: float) -> Optional[Trade]:
        """
        Ouvre un nouveau trade basé sur un signal - Mode chasse au vert ! 💰
        
        # Utilise post_only=True via Hyperliquid SDK pour rebates maker !
        # Sur HL : taker ~0.03%, maker rebates -0.003% = on GAGNE des fees !
        """
        if signal.signal_type == SignalType.HOLD:
            return None
        
        # Calcul du levier dynamique selon la volatilité
        leverage = self.calculate_dynamic_leverage(signal.volatility)
        
        # Calcul de la taille de position (0.1% du capital = tiny pour volume)
        size = calculate_position_size(
            capital,
            self.config.position_size_percent,
            signal.price,
            leverage
        )
        
        # Créer le trade
        trade = Trade(
            id=generate_trade_id(),
            asset=signal.asset,
            side=signal.signal_type.value,
            entry_price=signal.price,
            size=size,
            leverage=leverage,
            entry_time=datetime.now(),
            status="open"
        )
        
        # Initialiser le trailing stop pour ce trade
        self.trailing.initialize(trade.id, signal.price, trade.side)
        
        # Ajouter aux trades actifs
        self.active_trades[trade.id] = trade
        
        # 🚀 Log fun pour le démarrage du trade
        direction = "📈 LONG" if trade.side == "long" else "📉 SHORT"
        logger.info(f"🎯 Trade lancé – chasse au vert immédiat ! {direction} {trade.asset}")
        logger.trade_open(trade.asset, trade.side, trade.entry_price, trade.size)
        
        return trade
    
    def close_trade(self, trade: Trade, exit_price: float, reason: str, capital: float = 0) -> Trade:
        """
        Ferme un trade et calcule le PnL - puis prépare le REPEAT ! 🔁
        """
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = reason
        trade.status = "closed"
        
        # Calcul du PnL
        pnl_usd, pnl_percent = calculate_pnl(
            trade.entry_price,
            exit_price,
            trade.size,
            trade.side
        )
        
        trade.pnl = pnl_usd
        trade.pnl_percent = pnl_percent
        
        # Nettoyer le trailing
        self.trailing.remove(trade.id)
        if trade.id in self.active_trades:
            del self.active_trades[trade.id]
        
        # Logger le résultat avec style ! 🎉
        if trade.is_winner():
            logger.trade_win(trade.asset, pnl_percent, pnl_usd)
            # 🔁 REPEAT MODE : On reset la grille pour repartir direct !
            # Après un win, on recrée le filet pour attraper le prochain poisson
            self.grid.reset_grid(trade.asset)
            if capital > 0:
                self.grid.create_grid(trade.asset, exit_price, capital)
                logger.info(f"🎣 Grille resetée pour {trade.asset} - prêt pour le prochain ! 🔥")
        else:
            logger.trade_loss(trade.asset, pnl_percent, pnl_usd)
        
        return trade
    
    def get_active_trades(self) -> List[Trade]:
        """Retourne la liste des trades actifs"""
        return list(self.active_trades.values())
    
    def setup_grids(self, assets: List[str], prices: Dict[str, float], capital: float):
        """
        Initialise les grilles pour tous les assets
        On place le filet de pêche ! 🎣
        """
        for asset in assets:
            if asset in prices:
                self.grid.create_grid(asset, prices[asset], capital)


# ============================================
# TEST DU MODULE
# ============================================

if __name__ == "__main__":
    print("=== Test Strategy R2D2 ===")
    
    config = BotConfig()
    strategy = HybridScalpingStrategy(config)
    
    # Simuler des prix
    import random
    base_price = 50000
    prices = []
    for i in range(50):
        # Prix qui monte puis descend (pour tester RSI)
        if i < 20:
            price = base_price + random.uniform(-100, 200)
        else:
            price = base_price - random.uniform(-100, 200)
        prices.append(price)
        strategy.update_price("BTC", price)
    
    # Tester les indicateurs
    indicators = strategy.get_indicators("BTC")
    print(f"RSI: {indicators['rsi']:.2f}")
    print(f"MA Fast: ${indicators['ma_fast']:.2f}")
    print(f"MA Slow: ${indicators['ma_slow']:.2f}")
    print(f"Volatilité: {indicators['volatility']:.4f}")
    
    # Tester le signal
    mock_orderbook = {
        "bids": [[49950, 1], [49900, 2], [49850, 3]],
        "asks": [[50050, 1], [50100, 2], [50150, 3]]
    }
    
    signal = strategy.generate_signal("BTC", 50000, mock_orderbook)
    print(f"\nSignal: {signal.signal_type.value}")
    print(f"Raison: {signal.reason}")
    print(f"Confiance: {signal.confidence:.2f}")
    
    print("\n✅ Strategy OK !")
