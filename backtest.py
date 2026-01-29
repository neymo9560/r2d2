"""
R2D2 Bot - Module de Backtest
==============================
Ici on teste la stratégie sur des données historiques
AVANT de risquer de l'argent réel ! 🧪

Le backtest, c'est comme un simulateur de vol pour pilotes :
On s'entraîne sur le passé pour être prêt pour le futur !
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import pandas as pd
import numpy as np

from utils import (
    BotConfig, Trade, BotStats, logger, NetworkMode,
    calculate_pnl, generate_trade_id, format_percent, format_price
)
from strategy import HybridScalpingStrategy, SignalType, TradingSignal


# ============================================
# RÉCUPÉRATION DES DONNÉES HISTORIQUES
# ============================================

class HyperliquidDataFetcher:
    """
    Récupère les données historiques depuis l'API Hyperliquid
    Ces données nous permettent de tester notre stratégie sur le passé
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.base_url = config.get_api_url()
    
    async def fetch_candles(
        self, 
        asset: str, 
        interval: str = "1m",  # 1 minute
        limit: int = 1000
    ) -> List[Dict]:
        """
        Récupère les bougies (candles) historiques
        
        Une bougie contient :
        - Open : Prix d'ouverture
        - High : Prix le plus haut
        - Low : Prix le plus bas
        - Close : Prix de fermeture
        - Volume : Volume échangé
        
        C'est la base pour analyser le passé !
        """
        url = f"{self.base_url}/info"
        
        # Requête pour les candles
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": asset,
                "interval": interval,
                "startTime": int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                "endTime": int(datetime.now().timestamp() * 1000)
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if isinstance(data, list) else []
                    else:
                        logger.warning(f"Erreur API candles: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Erreur fetch candles: {e}")
            return []
    
    async def fetch_orderbook_snapshot(self, asset: str) -> Dict:
        """
        Récupère un snapshot du carnet d'ordres
        """
        url = f"{self.base_url}/info"
        
        payload = {
            "type": "l2Book",
            "coin": asset
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    return {"bids": [], "asks": []}
        except Exception as e:
            logger.error(f"Erreur fetch orderbook: {e}")
            return {"bids": [], "asks": []}
    
    def generate_synthetic_data(
        self, 
        asset: str,
        start_price: float,
        num_candles: int = 5000,
        volatility: float = 0.001
    ) -> pd.DataFrame:
        """
        Génère des données synthétiques pour le backtest
        
        Utile quand on n'a pas accès aux vraies données !
        On simule un marché réaliste avec des mouvements aléatoires
        """
        logger.info(f"Génération de {num_candles} bougies synthétiques pour {asset}")
        
        np.random.seed(42)  # Pour reproductibilité
        
        prices = [start_price]
        timestamps = []
        start_time = datetime.now() - timedelta(minutes=num_candles)
        
        for i in range(num_candles):
            # Mouvement aléatoire type random walk
            change = np.random.normal(0, volatility)
            # Ajout d'une tendance légère aléatoire
            trend = np.random.choice([-1, 1]) * 0.00001
            new_price = prices[-1] * (1 + change + trend)
            prices.append(new_price)
            timestamps.append(start_time + timedelta(minutes=i))
        
        # Créer le DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices[:-1],
            'close': prices[1:],
        })
        
        # Ajouter high/low réalistes
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, volatility, len(df)))
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, volatility, len(df)))
        df['volume'] = np.random.uniform(100, 1000, len(df))
        
        return df


# ============================================
# MOTEUR DE BACKTEST
# ============================================

@dataclass
class BacktestResult:
    """
    Résultats du backtest
    C'est le bulletin de notes de notre stratégie !
    """
    # Métriques principales
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    winrate: float = 0.0
    
    # PnL
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0
    average_trade_pnl: float = 0.0
    
    # Risque
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Capital
    start_capital: float = 0.0
    end_capital: float = 0.0
    
    # Timing
    start_date: str = ""
    end_date: str = ""
    duration_days: float = 0.0
    
    # Liste des trades
    trades: List[Dict] = field(default_factory=list)
    
    # Courbe d'équité
    equity_curve: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour affichage"""
        return asdict(self)
    
    def summary(self) -> str:
        """Résumé textuel des résultats"""
        return f"""
╔══════════════════════════════════════════╗
║       RÉSULTATS BACKTEST R2D2            ║
╠══════════════════════════════════════════╣
║ 📊 Trades: {self.total_trades:>5}                       ║
║ ✅ Gagnants: {self.winning_trades:>5} ({self.winrate:.1f}%)              ║
║ ❌ Perdants: {self.losing_trades:>5}                      ║
╠══════════════════════════════════════════╣
║ 💰 PnL Total: ${self.total_pnl:>10.2f}              ║
║ 📈 Rendement: {self.total_pnl_percent:>7.2f}%                 ║
║ 🏆 Meilleur: ${self.best_trade_pnl:>10.2f}              ║
║ 💀 Pire: ${self.worst_trade_pnl:>10.2f}                 ║
╠══════════════════════════════════════════╣
║ 📉 Max Drawdown: {self.max_drawdown_percent:>6.2f}%               ║
║ 📐 Sharpe Ratio: {self.sharpe_ratio:>6.2f}                ║
╠══════════════════════════════════════════╣
║ 💵 Capital Début: ${self.start_capital:>10.2f}          ║
║ 💵 Capital Fin: ${self.end_capital:>10.2f}            ║
╚══════════════════════════════════════════╝
"""


class BacktestEngine:
    """
    Moteur de Backtest
    
    Simule le trading sur des données historiques
    pour évaluer la performance de notre stratégie
    SANS risquer d'argent réel !
    
    C'est INDISPENSABLE avant de passer en live.
    """
    
    def __init__(self, config: BotConfig, initial_capital: float = 10000):
        self.config = config
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.strategy = HybridScalpingStrategy(config)
        self.data_fetcher = HyperliquidDataFetcher(config)
        
        # Historique
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
    
    def _simulate_orderbook(self, price: float, spread_bps: float = 5) -> Dict:
        """
        Simule un carnet d'ordres réaliste
        spread_bps = spread en points de base (5 = 0.05%)
        """
        spread = price * (spread_bps / 10000)
        bid = price - spread / 2
        ask = price + spread / 2
        
        # Créer plusieurs niveaux
        bids = []
        asks = []
        for i in range(10):
            bids.append([bid - i * spread, 10 + i * 5])
            asks.append([ask + i * spread, 10 + i * 5])
        
        return {"bids": bids, "asks": asks}
    
    def _check_daily_drawdown(self) -> bool:
        """
        Vérifie si on a dépassé le drawdown journalier max
        Si oui, on arrête le bot !
        """
        if self.capital <= 0:
            return True
        
        drawdown_percent = (self.peak_capital - self.capital) / self.peak_capital
        return drawdown_percent >= self.config.max_daily_drawdown
    
    def run_backtest(
        self, 
        data: pd.DataFrame, 
        asset: str = "BTC"
    ) -> BacktestResult:
        """
        Lance le backtest sur un DataFrame de données
        
        Le DataFrame doit avoir les colonnes :
        - timestamp, open, high, low, close, volume
        
        On simule chaque bougie comme si on était en live !
        """
        logger.info(f"🧪 Démarrage backtest sur {len(data)} bougies...")
        
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.peak_capital = self.initial_capital
        self.max_drawdown = 0.0
        
        active_trade: Optional[Trade] = None
        
        # Parcourir chaque bougie
        for idx, row in data.iterrows():
            # Vérifier le drawdown journalier
            if self._check_daily_drawdown():
                logger.warning("⚠️ Drawdown max atteint, arrêt du backtest")
                break
            
            current_price = row['close']
            
            # Simuler le carnet d'ordres
            orderbook = self._simulate_orderbook(current_price)
            
            # Si on a un trade actif, vérifier s'il faut le fermer
            if active_trade:
                # Simuler le mouvement intra-bougie avec high/low
                for check_price in [row['high'], row['low'], row['close']]:
                    should_close, reason = self.strategy.should_close_position(
                        active_trade, check_price
                    )
                    
                    if should_close:
                        # Fermer le trade
                        active_trade = self.strategy.close_trade(
                            active_trade, check_price, reason
                        )
                        self.trades.append(active_trade)
                        
                        # Mettre à jour le capital
                        self.capital += active_trade.pnl
                        self.equity_curve.append(self.capital)
                        
                        # Mettre à jour le peak et drawdown
                        if self.capital > self.peak_capital:
                            self.peak_capital = self.capital
                        else:
                            dd = (self.peak_capital - self.capital) / self.peak_capital
                            self.max_drawdown = max(self.max_drawdown, dd)
                        
                        active_trade = None
                        break
            
            # Si pas de trade actif, chercher un signal
            if not active_trade:
                signal = self.strategy.generate_signal(asset, current_price, orderbook)
                
                if signal.signal_type != SignalType.HOLD:
                    # Ouvrir un nouveau trade
                    active_trade = self.strategy.open_trade(signal, self.capital)
        
        # Fermer tout trade restant
        if active_trade:
            active_trade = self.strategy.close_trade(
                active_trade, data.iloc[-1]['close'], "end_of_data"
            )
            self.trades.append(active_trade)
            self.capital += active_trade.pnl
        
        # Calculer les résultats
        result = self._calculate_results(data, asset)
        
        logger.info(f"🧪 Backtest terminé: {result.total_trades} trades")
        
        return result
    
    def _calculate_results(self, data: pd.DataFrame, asset: str) -> BacktestResult:
        """
        Calcule toutes les métriques du backtest
        """
        result = BacktestResult()
        
        result.start_capital = self.initial_capital
        result.end_capital = self.capital
        result.total_pnl = self.capital - self.initial_capital
        result.total_pnl_percent = (result.total_pnl / self.initial_capital) * 100
        
        result.trades = [asdict(t) for t in self.trades]
        result.equity_curve = self.equity_curve
        
        if self.trades:
            result.total_trades = len(self.trades)
            result.winning_trades = sum(1 for t in self.trades if t.is_winner())
            result.losing_trades = result.total_trades - result.winning_trades
            result.winrate = (result.winning_trades / result.total_trades) * 100
            
            pnls = [t.pnl for t in self.trades]
            result.best_trade_pnl = max(pnls)
            result.worst_trade_pnl = min(pnls)
            result.average_trade_pnl = np.mean(pnls)
            
            # Sharpe Ratio (simplifié)
            if len(pnls) > 1:
                returns = np.array(pnls) / self.initial_capital
                if np.std(returns) > 0:
                    result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        
        result.max_drawdown = self.max_drawdown * self.peak_capital
        result.max_drawdown_percent = self.max_drawdown * 100
        
        # Dates
        if len(data) > 0:
            result.start_date = str(data.iloc[0]['timestamp'])
            result.end_date = str(data.iloc[-1]['timestamp'])
        
        return result
    
    async def run_forward_test(
        self, 
        asset: str = "BTC",
        duration_minutes: int = 60
    ) -> BacktestResult:
        """
        Forward Test (Paper Trading en temps réel)
        
        Comme un backtest mais sur des données LIVE !
        On ne trade pas vraiment, on simule juste.
        
        C'est l'étape entre le backtest et le trading réel.
        """
        logger.info(f"📝 Démarrage forward test sur {asset} pour {duration_minutes} min...")
        
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        
        active_trade: Optional[Trade] = None
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        prices_data = []
        
        while datetime.now() < end_time:
            try:
                # Récupérer le prix actuel via l'API
                candles = await self.data_fetcher.fetch_candles(asset, "1m", 1)
                
                if candles:
                    current_price = float(candles[-1].get('c', candles[-1].get('close', 50000)))
                else:
                    # Fallback: prix simulé
                    if prices_data:
                        current_price = prices_data[-1] * (1 + np.random.normal(0, 0.001))
                    else:
                        current_price = 50000  # Prix par défaut BTC
                
                prices_data.append(current_price)
                
                orderbook = await self.data_fetcher.fetch_orderbook_snapshot(asset)
                if not orderbook.get('bids'):
                    orderbook = self._simulate_orderbook(current_price)
                
                # Même logique que le backtest
                if active_trade:
                    should_close, reason = self.strategy.should_close_position(
                        active_trade, current_price
                    )
                    
                    if should_close:
                        active_trade = self.strategy.close_trade(
                            active_trade, current_price, reason
                        )
                        self.trades.append(active_trade)
                        self.capital += active_trade.pnl
                        self.equity_curve.append(self.capital)
                        active_trade = None
                
                if not active_trade:
                    signal = self.strategy.generate_signal(asset, current_price, orderbook)
                    
                    if signal.signal_type != SignalType.HOLD:
                        active_trade = self.strategy.open_trade(signal, self.capital)
                
                # Attendre avant le prochain scan
                await asyncio.sleep(self.config.scan_interval_seconds)
                
            except Exception as e:
                logger.error(f"Erreur forward test: {e}")
                await asyncio.sleep(5)
        
        # Créer un DataFrame pour les résultats
        if prices_data:
            df = pd.DataFrame({
                'timestamp': [start_time + timedelta(seconds=i) for i in range(len(prices_data))],
                'open': prices_data,
                'high': prices_data,
                'low': prices_data,
                'close': prices_data,
                'volume': [100] * len(prices_data)
            })
        else:
            df = pd.DataFrame()
        
        result = self._calculate_results(df, asset)
        logger.info(f"📝 Forward test terminé: {result.total_trades} trades")
        
        return result


# ============================================
# FONCTION PRINCIPALE DE TEST
# ============================================

def run_quick_backtest(
    assets: List[str] = ["BTC", "ETH"],
    initial_capital: float = 10000,
    num_candles: int = 5000
) -> Dict[str, BacktestResult]:
    """
    Lance un backtest rapide sur plusieurs assets
    Utilise des données synthétiques pour tester
    """
    config = BotConfig()
    results = {}
    
    for asset in assets:
        logger.info(f"\n{'='*50}")
        logger.info(f"Backtest {asset}")
        logger.info(f"{'='*50}")
        
        engine = BacktestEngine(config, initial_capital)
        
        # Générer des données synthétiques
        start_price = 50000 if asset == "BTC" else 3000
        data = engine.data_fetcher.generate_synthetic_data(
            asset, start_price, num_candles
        )
        
        # Lancer le backtest
        result = engine.run_backtest(data, asset)
        results[asset] = result
        
        print(result.summary())
    
    return results


# ============================================
# POINT D'ENTRÉE
# ============================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════╗
    ║     R2D2 BACKTEST - Mode Test Rapide      ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Lancer le backtest rapide
    results = run_quick_backtest(
        assets=["BTC", "ETH"],
        initial_capital=10000,
        num_candles=5000
    )
    
    # Résumé global
    print("\n" + "="*50)
    print("RÉSUMÉ GLOBAL")
    print("="*50)
    
    total_pnl = sum(r.total_pnl for r in results.values())
    total_trades = sum(r.total_trades for r in results.values())
    avg_winrate = np.mean([r.winrate for r in results.values()])
    
    print(f"💰 PnL Total: ${total_pnl:.2f}")
    print(f"📊 Trades Total: {total_trades}")
    print(f"✅ Winrate Moyen: {avg_winrate:.1f}%")
    
    print("\n✅ Backtest terminé avec succès !")
