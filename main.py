"""
R2D2 Bot - Module Principal
============================
C'est le cœur du robot ! 🤖
Ici on connecte tout ensemble :
- API Hyperliquid pour les trades
- Web3 pour le wallet
- Stratégie pour les décisions

Le bot tourne en boucle infinie et enchaîne les trades !
"""

import asyncio
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import signal
import sys

# Imports externes
import aiohttp
import requests
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Nos modules
from utils import (
    BotConfig, Trade, BotStats, NetworkMode, logger,
    get_private_key, get_wallet_address, get_infura_url,
    calculate_position_size, calculate_pnl, generate_trade_id,
    validate_config
)
from strategy import HybridScalpingStrategy, SignalType, TradingSignal

# Charger les variables d'environnement
load_dotenv()


# ============================================
# CLIENT API HYPERLIQUID
# ============================================

class HyperliquidClient:
    """
    Client pour l'API Hyperliquid
    
    Hyperliquid c'est un DEX (exchange décentralisé) sur Arbitrum
    avec des perpétuels (contrats futures sans expiration)
    
    On peut trader BTC, ETH et plein d'autres cryptos avec du levier !
    """
    
    def __init__(self, config: BotConfig, private_key: str = ""):
        self.config = config
        self.private_key = private_key
        self.wallet_address = ""
        
        # URLs API
        self.info_url = f"{config.get_api_url()}/info"
        self.exchange_url = f"{config.get_api_url()}/exchange"
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache des données
        self._price_cache: Dict[str, float] = {}
        self._orderbook_cache: Dict[str, Dict] = {}
        self._last_update: Dict[str, datetime] = {}
        
        # Initialiser le wallet si clé fournie
        if private_key:
            self._init_wallet(private_key)
    
    def _init_wallet(self, private_key: str):
        """
        Initialise le wallet avec la clé privée
        ATTENTION : La clé privée est ULTRA sensible !
        """
        try:
            # Ajouter le préfixe 0x si manquant
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            account = Account.from_key(private_key)
            self.wallet_address = account.address
            self.private_key = private_key
            
            logger.info(f"Wallet connecté: {self.wallet_address[:10]}...{self.wallet_address[-6:]}")
        except Exception as e:
            logger.error(f"Erreur initialisation wallet: {e}")
    
    async def _ensure_session(self):
        """Crée la session HTTP si nécessaire"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Ferme la session HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    # ==========================================
    # MÉTHODES DE LECTURE (INFO)
    # ==========================================
    
    async def get_all_mids(self) -> Dict[str, float]:
        """
        Récupère tous les prix mid (milieu bid/ask) de tous les assets
        C'est le prix "juste" entre acheteurs et vendeurs
        """
        await self._ensure_session()
        
        try:
            payload = {"type": "allMids"}
            async with self.session.post(self.info_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    # Convertir en dict {asset: price}
                    prices = {}
                    for asset, price in data.items():
                        prices[asset] = float(price)
                    self._price_cache = prices
                    return prices
                else:
                    logger.warning(f"Erreur API allMids: {response.status}")
                    return self._price_cache
        except Exception as e:
            logger.error(f"Erreur get_all_mids: {e}")
            return self._price_cache
    
    async def get_orderbook(self, asset: str) -> Dict:
        """
        Récupère le carnet d'ordres (L2) pour un asset
        
        Le carnet montre tous les ordres en attente :
        - Bids (offres d'achat) : Les gens qui veulent acheter
        - Asks (offres de vente) : Les gens qui veulent vendre
        """
        await self._ensure_session()
        
        try:
            payload = {"type": "l2Book", "coin": asset}
            async with self.session.post(self.info_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parser le format Hyperliquid
                    orderbook = {
                        "bids": [],
                        "asks": []
                    }
                    
                    if "levels" in data:
                        levels = data["levels"]
                        if len(levels) >= 2:
                            # Bids
                            for level in levels[0]:
                                orderbook["bids"].append([
                                    float(level.get("px", 0)),
                                    float(level.get("sz", 0))
                                ])
                            # Asks
                            for level in levels[1]:
                                orderbook["asks"].append([
                                    float(level.get("px", 0)),
                                    float(level.get("sz", 0))
                                ])
                    
                    self._orderbook_cache[asset] = orderbook
                    return orderbook
                else:
                    return self._orderbook_cache.get(asset, {"bids": [], "asks": []})
        except Exception as e:
            logger.error(f"Erreur get_orderbook: {e}")
            return self._orderbook_cache.get(asset, {"bids": [], "asks": []})
    
    async def get_user_state(self) -> Dict:
        """
        Récupère l'état du compte utilisateur
        - Positions ouvertes
        - Capital disponible
        - PnL non réalisé
        """
        if not self.wallet_address:
            return {}
        
        await self._ensure_session()
        
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.wallet_address
            }
            async with self.session.post(self.info_url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.error(f"Erreur get_user_state: {e}")
            return {}
    
    async def get_open_orders(self) -> List[Dict]:
        """Récupère les ordres ouverts"""
        if not self.wallet_address:
            return []
        
        await self._ensure_session()
        
        try:
            payload = {
                "type": "openOrders",
                "user": self.wallet_address
            }
            async with self.session.post(self.info_url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Erreur get_open_orders: {e}")
            return []
    
    async def get_candles(
        self, 
        asset: str, 
        interval: str = "1m",
        limit: int = 100
    ) -> List[Dict]:
        """
        Récupère les bougies historiques
        Interval: 1m, 5m, 15m, 1h, 4h, 1d
        """
        await self._ensure_session()
        
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (limit * 60 * 1000)  # Pour 1m
            
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": asset,
                    "interval": interval,
                    "startTime": start_time,
                    "endTime": end_time
                }
            }
            async with self.session.post(self.info_url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Erreur get_candles: {e}")
            return []
    
    # ==========================================
    # MÉTHODES D'ÉCRITURE (EXCHANGE)
    # ==========================================
    
    def _sign_order(self, order_data: Dict) -> Dict:
        """
        Signe un ordre avec la clé privée
        C'est obligatoire pour prouver que c'est bien TOI qui trades !
        """
        if not self.private_key:
            raise ValueError("Clé privée requise pour signer")
        
        # Hyperliquid utilise un format de signature spécifique
        # Ici on simplifie - en production il faut utiliser le SDK officiel
        timestamp = int(time.time() * 1000)
        
        # Structure basique - le vrai SDK gère la signature EIP-712
        signed_order = {
            "action": order_data,
            "nonce": timestamp,
            "signature": {
                "r": "0x" + "0" * 64,  # Placeholder
                "s": "0x" + "0" * 64,
                "v": 27
            },
            "vaultAddress": None
        }
        
        return signed_order
    
    async def place_order(
        self,
        asset: str,
        is_buy: bool,
        size: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        reduce_only: bool = False,
        post_only: bool = True  # Pour les rebates maker !
    ) -> Dict:
        """
        Place un ordre sur Hyperliquid
        
        Paramètres :
        - asset : "BTC", "ETH", etc.
        - is_buy : True = achat (long), False = vente (short)
        - size : Taille en unités de l'asset
        - price : Prix limite (None = market order)
        - order_type : "limit", "market", "stop"
        - reduce_only : True = ferme une position existante
        - post_only : True = ordre maker uniquement (pour les rebates !)
        
        IMPORTANT : post_only = True nous donne des REBATES négatifs !
        Sur Hyperliquid, les makers gagnent environ -0.003% par trade.
        C'est de l'argent gratuit si l'ordre est exécuté !
        """
        await self._ensure_session()
        
        # Récupérer le prix actuel si pas de prix spécifié
        if price is None:
            prices = await self.get_all_mids()
            price = prices.get(asset, 0)
            if price == 0:
                return {"error": "Prix non disponible"}
        
        # Construire l'ordre
        order = {
            "type": "order",
            "orders": [{
                "a": self._get_asset_index(asset),  # Index de l'asset
                "b": is_buy,  # True = buy, False = sell
                "p": str(price),  # Prix
                "s": str(size),  # Taille
                "r": reduce_only,  # Reduce only
                "t": {
                    "limit": {
                        "tif": "Alo" if post_only else "Gtc"  # Post-only ou Good-til-cancel
                    }
                } if order_type == "limit" else {"market": {}}
            }],
            "grouping": "na"
        }
        
        try:
            # En mode simulation, on ne signe pas vraiment
            if not self.private_key:
                logger.info(f"[SIMULATION] Ordre: {'BUY' if is_buy else 'SELL'} {size} {asset} @ ${price}")
                return {"status": "simulated", "order": order}
            
            # Signer et envoyer l'ordre
            signed = self._sign_order(order)
            
            async with self.session.post(self.exchange_url, json=signed) as response:
                result = await response.json()
                
                if response.status == 200:
                    logger.info(f"Ordre placé: {'BUY' if is_buy else 'SELL'} {size} {asset} @ ${price}")
                else:
                    logger.error(f"Erreur ordre: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Erreur place_order: {e}")
            return {"error": str(e)}
    
    async def cancel_order(self, asset: str, order_id: int) -> Dict:
        """Annule un ordre"""
        await self._ensure_session()
        
        cancel_request = {
            "type": "cancel",
            "cancels": [{
                "a": self._get_asset_index(asset),
                "o": order_id
            }]
        }
        
        try:
            signed = self._sign_order(cancel_request)
            async with self.session.post(self.exchange_url, json=signed) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Erreur cancel_order: {e}")
            return {"error": str(e)}
    
    async def cancel_all_orders(self, asset: Optional[str] = None) -> Dict:
        """Annule tous les ordres (optionnellement pour un asset)"""
        orders = await self.get_open_orders()
        
        results = []
        for order in orders:
            if asset is None or order.get("coin") == asset:
                result = await self.cancel_order(
                    order.get("coin", ""),
                    order.get("oid", 0)
                )
                results.append(result)
        
        return {"cancelled": len(results)}
    
    def _get_asset_index(self, asset: str) -> int:
        """
        Retourne l'index de l'asset dans Hyperliquid
        Chaque asset a un numéro unique
        """
        # Mapping simplifié - en production, récupérer via l'API
        asset_indices = {
            "BTC": 0,
            "ETH": 1,
            "ATOM": 2,
            "MATIC": 3,
            "DYDX": 4,
            "SOL": 5,
            "AVAX": 6,
            "BNB": 7,
            "APE": 8,
            "OP": 9,
            "LTC": 10,
            "ARB": 11,
            "DOGE": 12,
        }
        return asset_indices.get(asset, 0)


# ============================================
# CONNEXION WEB3 (ARBITRUM)
# ============================================

class Web3Connector:
    """
    Connecteur Web3 pour Arbitrum
    
    On utilise Web3 pour :
    - Vérifier le wallet
    - Récupérer les balances
    - Signer les transactions si nécessaire
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.w3: Optional[Web3] = None
        self.account = None
        self.connected = False
    
    def connect(self, infura_url: str = "") -> bool:
        """
        Connecte au provider Infura/Arbitrum
        
        Testnet: Arbitrum Sepolia (chain 421614)
        Mainnet: Arbitrum One (chain 42161)
        """
        try:
            # Récupérer l'URL depuis .env si pas fournie
            if not infura_url:
                is_mainnet = self.config.network_mode == NetworkMode.MAINNET
                infura_url = get_infura_url(mainnet=is_mainnet)
            
            if not infura_url:
                logger.warning("URL Infura non configurée, mode simulation")
                return False
            
            self.w3 = Web3(Web3.HTTPProvider(infura_url))
            
            if self.w3.is_connected():
                chain_id = self.w3.eth.chain_id
                expected_chain = self.config.get_chain_id()
                
                if chain_id == expected_chain:
                    logger.info(f"Web3 connecté à chain {chain_id}")
                    self.connected = True
                    return True
                else:
                    logger.warning(f"Chain mismatch: attendu {expected_chain}, reçu {chain_id}")
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur connexion Web3: {e}")
            return False
    
    def get_balance(self, address: str) -> float:
        """Récupère le solde ETH d'une adresse"""
        if not self.w3 or not self.connected:
            return 0.0
        
        try:
            balance_wei = self.w3.eth.get_balance(address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Erreur get_balance: {e}")
            return 0.0
    
    def load_wallet(self, private_key: str) -> Optional[str]:
        """
        Charge un wallet depuis une clé privée
        Retourne l'adresse du wallet
        """
        try:
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            self.account = Account.from_key(private_key)
            return self.account.address
        except Exception as e:
            logger.error(f"Erreur load_wallet: {e}")
            return None


# ============================================
# BOT PRINCIPAL R2D2
# ============================================

class BotState(Enum):
    """États possibles du bot"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class R2D2Bot:
    """
    Le Bot R2D2 - Scalper HFT pour Hyperliquid
    
    Ce robot enchaîne des trades ultra-rapides pour gratter
    des petits profits à chaque mouvement du marché !
    
    Stratégie hybride :
    - Grid Bot pour les rebonds
    - Trailing Stop pour verrouiller les gains
    - RSI/MA pour filtrer les mauvais moments
    """
    
    config: BotConfig
    capital: float = 10000.0
    
    # État du bot
    state: BotState = BotState.STOPPED
    
    # Composants
    client: Optional[HyperliquidClient] = None
    web3: Optional[Web3Connector] = None
    strategy: Optional[HybridScalpingStrategy] = None
    
    # Statistiques
    stats: BotStats = field(default_factory=BotStats)
    
    # Historique
    trades_history: List[Trade] = field(default_factory=list)
    
    # Contrôle
    _running: bool = False
    _task: Optional[asyncio.Task] = None
    
    # Callbacks pour l'UI
    on_trade: Optional[Callable] = None
    on_stats_update: Optional[Callable] = None
    on_state_change: Optional[Callable] = None
    
    def __post_init__(self):
        """Initialisation après création"""
        self.stats.start_capital = self.capital
        self.stats.current_capital = self.capital
    
    async def initialize(self) -> bool:
        """
        Initialise tous les composants du bot
        C'est comme faire le check-up avant le décollage ! 🚀
        """
        self.state = BotState.STARTING
        self._notify_state_change()
        
        logger.info("Initialisation de R2D2...")
        
        # Valider la configuration
        is_valid, errors = validate_config(self.config)
        if not is_valid:
            for error in errors:
                logger.error(error)
            self.state = BotState.ERROR
            return False
        
        # Initialiser le client Hyperliquid
        private_key = get_private_key()
        self.client = HyperliquidClient(self.config, private_key)
        
        # Initialiser Web3
        self.web3 = Web3Connector(self.config)
        self.web3.connect()
        
        # Initialiser la stratégie
        self.strategy = HybridScalpingStrategy(self.config)
        
        # Récupérer le capital initial si connecté
        if self.client.wallet_address:
            user_state = await self.client.get_user_state()
            if user_state:
                # Extraire le capital depuis l'état du compte
                account_value = user_state.get("marginSummary", {}).get("accountValue", "0")
                if account_value:
                    self.capital = float(account_value)
                    self.stats.start_capital = self.capital
                    self.stats.current_capital = self.capital
        
        logger.info(f"Capital initial: ${self.capital:.2f}")
        
        mode = "MAINNET 🔴" if self.config.network_mode == NetworkMode.MAINNET else "TESTNET 🟢"
        logger.bot_start(mode)
        
        return True
    
    async def start(self):
        """
        Démarre la boucle principale du bot
        C'est parti pour enchaîner les trades ! 💰
        """
        if self.state == BotState.RUNNING:
            logger.warning("Bot déjà en cours d'exécution")
            return
        
        # Initialiser si nécessaire
        if self.state != BotState.STARTING:
            if not await self.initialize():
                return
        
        self._running = True
        self.state = BotState.RUNNING
        self._notify_state_change()
        
        # Lancer la boucle principale
        self._task = asyncio.create_task(self._main_loop())
    
    async def stop(self, reason: str = ""):
        """Arrête le bot proprement"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Fermer toutes les positions
        if self.strategy:
            active_trades = self.strategy.get_active_trades()
            for trade in active_trades:
                logger.info(f"Fermeture position {trade.asset}...")
                # En production, fermer vraiment la position
        
        # Annuler tous les ordres
        if self.client:
            await self.client.cancel_all_orders()
            await self.client.close()
        
        self.state = BotState.STOPPED
        self._notify_state_change()
        logger.bot_stop(reason)
    
    async def pause(self):
        """Met le bot en pause"""
        self._running = False
        self.state = BotState.PAUSED
        self._notify_state_change()
        logger.info("Bot en pause")
    
    async def resume(self):
        """Reprend après une pause"""
        if self.state == BotState.PAUSED:
            self._running = True
            self.state = BotState.RUNNING
            self._notify_state_change()
            self._task = asyncio.create_task(self._main_loop())
            logger.info("Bot repris")
    
    async def _main_loop(self):
        """
        Boucle principale du bot
        
        C'est ici que la magie opère ! 🎩
        Le bot scanne le marché en boucle et trade automatiquement
        """
        logger.info("Démarrage boucle principale...")
        
        # Initialiser les grilles
        prices = await self.client.get_all_mids()
        self.strategy.setup_grids(self.config.assets, prices, self.capital)
        
        scan_count = 0
        
        while self._running:
            try:
                scan_count += 1
                
                # Vérifier le drawdown journalier
                if self._check_daily_drawdown():
                    await self.stop("Drawdown journalier max atteint (-2%)")
                    break
                
                # Scanner chaque asset
                for asset in self.config.assets:
                    if not self._running:
                        break
                    
                    await self._process_asset(asset)
                
                # Mise à jour des stats périodique
                if scan_count % 10 == 0:
                    logger.stats_update(self.stats)
                    self._notify_stats_update()
                
                # Attendre avant le prochain scan
                await asyncio.sleep(self.config.scan_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur boucle principale: {e}")
                await asyncio.sleep(5)  # Pause avant retry
    
    async def _process_asset(self, asset: str):
        """
        Traite un asset : génère signal et trade si nécessaire
        """
        # Récupérer les données
        prices = await self.client.get_all_mids()
        current_price = prices.get(asset, 0)
        
        if current_price == 0:
            return
        
        orderbook = await self.client.get_orderbook(asset)
        
        # Vérifier les trades actifs pour cet asset
        active_trades = [t for t in self.strategy.get_active_trades() if t.asset == asset]
        
        for trade in active_trades:
            # Vérifier si on doit fermer
            should_close, reason = self.strategy.should_close_position(trade, current_price)
            
            if should_close:
                # Fermer le trade
                closed_trade = self.strategy.close_trade(trade, current_price, reason)
                self.trades_history.append(closed_trade)
                
                # Mettre à jour le capital
                self.capital += closed_trade.pnl
                self.stats.current_capital = self.capital
                self.stats.update_from_trade(closed_trade)
                
                # Callback pour l'UI
                if self.on_trade:
                    self.on_trade(closed_trade)
                
                # Placer l'ordre de fermeture réel
                is_buy = closed_trade.side == "short"  # Inverse pour fermer
                await self.client.place_order(
                    asset=asset,
                    is_buy=is_buy,
                    size=closed_trade.size,
                    reduce_only=True
                )
        
        # Si pas de position, chercher un signal
        if not active_trades:
            signal = self.strategy.generate_signal(asset, current_price, orderbook)
            
            if signal.signal_type != SignalType.HOLD:
                # Ouvrir un nouveau trade
                trade = self.strategy.open_trade(signal, self.capital)
                
                if trade:
                    # Placer l'ordre réel
                    is_buy = trade.side == "long"
                    await self.client.place_order(
                        asset=asset,
                        is_buy=is_buy,
                        size=trade.size,
                        post_only=True  # Pour les rebates !
                    )
    
    def _check_daily_drawdown(self) -> bool:
        """
        Vérifie si on a dépassé le drawdown max journalier
        Protection contre les grosses pertes !
        """
        if self.stats.start_capital <= 0:
            return False
        
        drawdown = (self.stats.start_capital - self.capital) / self.stats.start_capital
        return drawdown >= self.config.max_daily_drawdown
    
    def _notify_state_change(self):
        """Notifie un changement d'état"""
        if self.on_state_change:
            self.on_state_change(self.state)
    
    def _notify_stats_update(self):
        """Notifie une mise à jour des stats"""
        if self.on_stats_update:
            self.on_stats_update(self.stats)
    
    def switch_network(self, to_mainnet: bool):
        """
        Change de réseau (testnet <-> mainnet)
        
        ATTENTION : Mainnet = argent réel !
        Le bouton "GO LIVE" dans l'UI utilise cette fonction
        """
        if self.state == BotState.RUNNING:
            logger.warning("Arrête le bot avant de changer de réseau !")
            return False
        
        if to_mainnet:
            self.config.network_mode = NetworkMode.MAINNET
            logger.warning("⚠️ PASSAGE EN MAINNET - ARGENT RÉEL !")
        else:
            self.config.network_mode = NetworkMode.TESTNET
            logger.info("Retour en testnet (paper trading)")
        
        return True
    
    def get_state_info(self) -> Dict:
        """Retourne toutes les infos d'état pour l'UI"""
        return {
            "state": self.state.value,
            "network": self.config.network_mode.value,
            "capital": self.capital,
            "stats": {
                "total_trades": self.stats.total_trades,
                "winning_trades": self.stats.winning_trades,
                "winrate": self.stats.winrate,
                "total_pnl": self.stats.total_pnl,
                "current_streak": self.stats.current_streak
            },
            "active_trades": len(self.strategy.get_active_trades()) if self.strategy else 0,
            "assets": self.config.assets
        }


# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def create_bot(
    network: str = "testnet",
    capital: float = 10000.0,
    assets: List[str] = None
) -> R2D2Bot:
    """
    Crée une instance du bot R2D2
    
    Usage :
        bot = create_bot(network="testnet", capital=10000)
        await bot.start()
    """
    config = BotConfig()
    
    # Configurer le réseau
    if network == "mainnet":
        config.network_mode = NetworkMode.MAINNET
    else:
        config.network_mode = NetworkMode.TESTNET
    
    # Configurer les assets
    if assets:
        config.assets = assets
    
    return R2D2Bot(config=config, capital=capital)


async def run_bot_standalone():
    """
    Lance le bot en mode standalone (sans UI)
    Pour les tests ou le trading en ligne de commande
    """
    print("""
    ╔═══════════════════════════════════════════╗
    ║         R2D2 Bot - Mode Standalone        ║
    ║   Scalper HFT pour Hyperliquid            ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Créer le bot
    bot = create_bot(network="testnet", capital=10000)
    
    # Gérer Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nArrêt demandé...")
        asyncio.create_task(bot.stop("Interruption utilisateur"))
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrer le bot
    await bot.start()
    
    # Attendre que le bot s'arrête
    while bot.state == BotState.RUNNING:
        await asyncio.sleep(1)
    
    print("\nBot arrêté.")


# ============================================
# POINT D'ENTRÉE
# ============================================

if __name__ == "__main__":
    print("Démarrage R2D2...")
    
    # Lancer le bot
    asyncio.run(run_bot_standalone())
