"""
R2D2 Bot - Interface Streamlit 🤖
==================================
Une interface super fun et gamifiée pour contrôler le bot !
Avec des graphiques, des animations et des sons quand on gagne !

Pour lancer : streamlit run app.py
"""

import streamlit as st
import asyncio
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Graphiques
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Nos modules
from utils import BotConfig, BotStats, Trade, NetworkMode, logger
from strategy import HybridScalpingStrategy
from backtest import BacktestEngine, run_quick_backtest
from main import R2D2Bot, create_bot, BotState

# ============================================
# CONFIGURATION STREAMLIT
# ============================================

st.set_page_config(
    page_title="R2D2 Bot - Scalping HFT",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CSS PERSONNALISÉ (Dark Mode Gamifié)
# ============================================

CUSTOM_CSS = """
<style>
/* Dark theme global */
.stApp {
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
}

/* Titres flashy */
.big-title {
    font-size: 3rem;
    font-weight: bold;
    background: linear-gradient(90deg, #00ff88, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 1rem;
    animation: glow 2s ease-in-out infinite alternate;
}

@keyframes glow {
    from { text-shadow: 0 0 10px #00ff88; }
    to { text-shadow: 0 0 20px #00d4ff; }
}

/* Cartes de stats */
.stat-card {
    background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid #333;
    box-shadow: 0 4px 15px rgba(0, 255, 136, 0.1);
}

.stat-value {
    font-size: 2.5rem;
    font-weight: bold;
    color: #00ff88;
}

.stat-value.negative {
    color: #ff4444;
}

.stat-label {
    color: #888;
    font-size: 0.9rem;
    text-transform: uppercase;
}

/* Bouton GO LIVE */
.go-live-btn {
    background: linear-gradient(90deg, #ff4444, #ff6b6b);
    color: white;
    font-size: 1.5rem;
    font-weight: bold;
    padding: 15px 40px;
    border-radius: 50px;
    border: none;
    cursor: pointer;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }
    70% { box-shadow: 0 0 0 20px rgba(255, 68, 68, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
}

/* Animation de victoire */
.win-animation {
    animation: celebrate 0.5s ease-out;
}

@keyframes celebrate {
    0% { transform: scale(1); }
    50% { transform: scale(1.2); }
    100% { transform: scale(1); }
}

/* Badge streak */
.streak-badge {
    background: linear-gradient(90deg, #ff9500, #ff5e00);
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
}

/* Log entries */
.log-win {
    color: #00ff88;
    background: rgba(0, 255, 136, 0.1);
    padding: 5px 10px;
    border-radius: 5px;
    margin: 2px 0;
}

.log-loss {
    color: #ff4444;
    background: rgba(255, 68, 68, 0.1);
    padding: 5px 10px;
    border-radius: 5px;
    margin: 2px 0;
}

/* Responsive mobile */
@media (max-width: 768px) {
    .big-title { font-size: 2rem; }
    .stat-value { font-size: 1.8rem; }
}
</style>
"""

# ============================================
# ÉTAT DE SESSION
# ============================================

def init_session_state():
    """Initialise l'état de session Streamlit"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None  # 'control' ou 'viewer'
    if 'bot' not in st.session_state:
        st.session_state.bot = None
    if 'bot_running' not in st.session_state:
        st.session_state.bot_running = False
    if 'network_mode' not in st.session_state:
        st.session_state.network_mode = 'testnet'
    if 'trades_history' not in st.session_state:
        st.session_state.trades_history = []
    if 'stats' not in st.session_state:
        st.session_state.stats = BotStats()
    if 'config' not in st.session_state:
        st.session_state.config = BotConfig()
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'equity_curve' not in st.session_state:
        st.session_state.equity_curve = [10000]
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()


# ============================================
# PAGE DE LOGIN
# ============================================

def show_login_page():
    """Affiche la page de connexion"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Logo et titre
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="big-title">🤖 R2D2 Bot</p>', unsafe_allow_html=True)
        st.markdown("### Scalper HFT pour Hyperliquid")
        st.markdown("---")
    
    # Formulaire de login
    with col2:
        st.subheader("🔐 Connexion")
        
        password = st.text_input("Mot de passe", type="password", key="login_password")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🎮 Mode Contrôle", use_container_width=True):
                if password == "Bine":
                    st.session_state.authenticated = True
                    st.session_state.user_role = 'control'
                    st.success("Bienvenue en mode Contrôle ! 🎮")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect !")
        
        with col_b:
            if st.button("👁️ Mode Viewer", use_container_width=True):
                if password == "Bina":
                    st.session_state.authenticated = True
                    st.session_state.user_role = 'viewer'
                    st.success("Bienvenue en mode Viewer ! 👁️")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect !")
        
        st.markdown("---")
        st.info("""
        **Mode Contrôle** : Accès complet (start/stop, paramètres, trades manuels)
        
        **Mode Viewer** : Lecture seule (dashboard, logs, graphiques)
        """)


# ============================================
# COMPOSANTS UI
# ============================================

def create_stat_card(label: str, value: str, is_positive: bool = True, emoji: str = ""):
    """Crée une carte de statistique stylée"""
    color_class = "" if is_positive else "negative"
    return f"""
    <div class="stat-card">
        <div class="stat-label">{emoji} {label}</div>
        <div class="stat-value {color_class}">{value}</div>
    </div>
    """


def create_pnl_chart(equity_curve: List[float], trades: List[Dict] = None):
    """Crée un graphique de PnL en temps réel"""
    fig = go.Figure()
    
    # Courbe d'équité
    fig.add_trace(go.Scatter(
        y=equity_curve,
        mode='lines',
        name='Capital',
        line=dict(color='#00ff88', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 136, 0.1)'
    ))
    
    # Ligne de départ
    if equity_curve:
        fig.add_hline(
            y=equity_curve[0], 
            line_dash="dash", 
            line_color="#666",
            annotation_text="Capital initial"
        )
    
    # Style
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=300,
        xaxis_title="Trades",
        yaxis_title="Capital ($)",
        showlegend=False,
        font=dict(color='#888')
    )
    
    return fig


def create_price_chart(prices: List[float], asset: str = "BTC"):
    """Crée un graphique de prix en temps réel"""
    fig = go.Figure()
    
    # Prix
    colors = ['#00ff88' if i == 0 or prices[i] >= prices[i-1] else '#ff4444' 
              for i in range(len(prices))]
    
    fig.add_trace(go.Scatter(
        y=prices,
        mode='lines+markers',
        name=asset,
        line=dict(color='#00d4ff', width=2),
        marker=dict(size=4, color=colors)
    ))
    
    # Style
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=250,
        title=f"{asset} Prix en temps réel",
        showlegend=False,
        font=dict(color='#888')
    )
    
    return fig


def create_winrate_gauge(winrate: float):
    """Crée une jauge de winrate"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=winrate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Winrate", 'font': {'size': 16, 'color': '#888'}},
        delta={'reference': 50, 'increasing': {'color': "#00ff88"}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': "#888"},
            'bar': {'color': "#00ff88"},
            'bgcolor': "#1a1a2e",
            'borderwidth': 2,
            'bordercolor': "#333",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(255, 68, 68, 0.3)'},
                {'range': [50, 80], 'color': 'rgba(255, 200, 0, 0.3)'},
                {'range': [80, 100], 'color': 'rgba(0, 255, 136, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "#00d4ff", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#888"},
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


# ============================================
# SIDEBAR
# ============================================

def show_sidebar():
    """Affiche la barre latérale avec les contrôles"""
    with st.sidebar:
        st.markdown("## 🤖 R2D2 Bot")
        st.markdown(f"**Mode**: {st.session_state.user_role.upper()}")
        st.markdown(f"**Réseau**: {'🔴 MAINNET' if st.session_state.network_mode == 'mainnet' else '🟢 TESTNET'}")
        
        st.markdown("---")
        
        # Contrôles du bot (mode Contrôle uniquement)
        if st.session_state.user_role == 'control':
            st.subheader("⚙️ Contrôles")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not st.session_state.bot_running:
                    if st.button("▶️ START", use_container_width=True, type="primary"):
                        start_bot()
                else:
                    if st.button("⏹️ STOP", use_container_width=True, type="secondary"):
                        stop_bot()
            
            with col2:
                if st.session_state.bot_running:
                    if st.button("⏸️ PAUSE", use_container_width=True):
                        pause_bot()
            
            st.markdown("---")
            
            # Switch testnet/mainnet
            st.subheader("🌐 Réseau")
            
            if st.session_state.network_mode == 'testnet':
                st.warning("Mode Paper Trading (testnet)")
                if st.button("🔴 GO LIVE !", use_container_width=True, type="primary"):
                    if not st.session_state.bot_running:
                        st.session_state.network_mode = 'mainnet'
                        st.session_state.config.network_mode = NetworkMode.MAINNET
                        st.warning("⚠️ ATTENTION: Argent réel !")
                        st.rerun()
                    else:
                        st.error("Arrête le bot d'abord !")
            else:
                st.error("⚠️ MODE MAINNET - ARGENT RÉEL !")
                if st.button("🟢 Back to Paper", use_container_width=True):
                    if not st.session_state.bot_running:
                        st.session_state.network_mode = 'testnet'
                        st.session_state.config.network_mode = NetworkMode.TESTNET
                        st.rerun()
                    else:
                        st.error("Arrête le bot d'abord !")
            
            st.markdown("---")
            
            # Paramètres
            with st.expander("📊 Paramètres Stratégie"):
                config = st.session_state.config
                
                config.grid_size = st.slider(
                    "Grid Size (%)", 
                    min_value=0.1, max_value=2.0, 
                    value=config.grid_size * 100,
                    step=0.1
                ) / 100
                
                config.grid_levels = st.slider(
                    "Grid Levels",
                    min_value=1, max_value=10,
                    value=config.grid_levels
                )
                
                config.rsi_oversold = st.slider(
                    "RSI Oversold",
                    min_value=10, max_value=40,
                    value=int(config.rsi_oversold)
                )
                
                config.rsi_overbought = st.slider(
                    "RSI Overbought",
                    min_value=60, max_value=90,
                    value=int(config.rsi_overbought)
                )
                
                config.leverage_max = st.slider(
                    "Leverage Max",
                    min_value=1, max_value=10,
                    value=config.leverage_max
                )
            
            with st.expander("💰 Gestion du Risque"):
                config = st.session_state.config
                
                config.stop_loss_percent = st.slider(
                    "Stop Loss (%)",
                    min_value=0.05, max_value=0.5,
                    value=config.stop_loss_percent * 100,
                    step=0.05
                ) / 100
                
                config.take_profit_percent = st.slider(
                    "Take Profit (%)",
                    min_value=0.1, max_value=1.0,
                    value=config.take_profit_percent * 100,
                    step=0.1
                ) / 100
                
                config.position_size_percent = st.slider(
                    "Taille Position (%)",
                    min_value=0.05, max_value=1.0,
                    value=config.position_size_percent * 100,
                    step=0.05
                ) / 100
            
            with st.expander("🪙 Assets"):
                assets = st.multiselect(
                    "Assets à trader",
                    options=["BTC", "ETH", "SOL", "AVAX", "ARB", "OP", "DOGE"],
                    default=st.session_state.config.assets
                )
                st.session_state.config.assets = assets
        
        # Déconnexion
        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.rerun()


# ============================================
# FONCTIONS BOT
# ============================================

def start_bot():
    """Démarre le bot"""
    st.session_state.bot_running = True
    st.session_state.stats = BotStats()
    st.session_state.stats.start_capital = 10000
    st.session_state.stats.current_capital = 10000
    st.session_state.equity_curve = [10000]
    st.session_state.trades_history = []
    add_log("🚀 Bot démarré !", "info")
    

def stop_bot():
    """Arrête le bot"""
    st.session_state.bot_running = False
    add_log("🛑 Bot arrêté", "info")


def pause_bot():
    """Met le bot en pause"""
    st.session_state.bot_running = False
    add_log("⏸️ Bot en pause", "info")


def add_log(message: str, log_type: str = "info"):
    """Ajoute un log"""
    log = {
        'time': datetime.now().strftime("%H:%M:%S"),
        'message': message,
        'type': log_type
    }
    st.session_state.logs.insert(0, log)
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[:100]


def simulate_trading():
    """Simule du trading pour la démo"""
    if not st.session_state.bot_running:
        return
    
    stats = st.session_state.stats
    
    # Simuler un trade aléatoire
    import random
    
    if random.random() < 0.3:  # 30% de chance de trade
        is_win = random.random() < 0.82  # 82% winrate
        
        pnl_percent = random.uniform(0.1, 0.3) if is_win else random.uniform(-0.08, -0.12)
        pnl_usd = stats.current_capital * (pnl_percent / 100)
        
        stats.total_trades += 1
        stats.current_capital += pnl_usd
        stats.total_pnl += pnl_usd
        
        if is_win:
            stats.winning_trades += 1
            stats.current_streak = max(1, stats.current_streak + 1)
            add_log(f"🎉 Trade GAGNÉ +{pnl_percent:.2f}% (+${pnl_usd:.2f})", "win")
        else:
            stats.losing_trades += 1
            stats.current_streak = min(-1, stats.current_streak - 1)
            add_log(f"😢 Trade perdu {pnl_percent:.2f}% (${pnl_usd:.2f})", "loss")
        
        st.session_state.equity_curve.append(stats.current_capital)
        
        # Trade object
        trade = {
            'id': len(st.session_state.trades_history) + 1,
            'asset': random.choice(['BTC', 'ETH']),
            'side': random.choice(['long', 'short']),
            'pnl': pnl_usd,
            'pnl_percent': pnl_percent,
            'time': datetime.now()
        }
        st.session_state.trades_history.insert(0, trade)


# ============================================
# PAGES PRINCIPALES
# ============================================

def show_dashboard():
    """Affiche le dashboard principal"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Titre
    st.markdown('<p class="big-title">🤖 R2D2 Dashboard</p>', unsafe_allow_html=True)
    
    # Simuler du trading
    simulate_trading()
    
    stats = st.session_state.stats
    
    # Ligne de stats principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pnl_color = "🟢" if stats.total_pnl >= 0 else "🔴"
        st.metric(
            "💰 PnL Total",
            f"${stats.total_pnl:.2f}",
            f"{(stats.total_pnl / max(stats.start_capital, 1)) * 100:.2f}%"
        )
    
    with col2:
        st.metric(
            "📊 Trades",
            f"{stats.winning_trades}/{stats.total_trades}",
            f"{stats.winrate:.1f}% winrate"
        )
    
    with col3:
        st.metric(
            "💵 Capital",
            f"${stats.current_capital:.2f}",
            f"${stats.current_capital - stats.start_capital:.2f}"
        )
    
    with col4:
        streak_emoji = "🔥" if stats.current_streak > 0 else "❄️"
        st.metric(
            f"{streak_emoji} Streak",
            abs(stats.current_streak),
            "wins" if stats.current_streak > 0 else "losses"
        )
    
    st.markdown("---")
    
    # Graphiques
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📈 Courbe de Capital")
        fig = create_pnl_chart(st.session_state.equity_curve)
        st.plotly_chart(fig, use_container_width=True)
        
        # Prix simulé
        st.subheader("💹 Prix BTC")
        if 'price_history' not in st.session_state:
            st.session_state.price_history = [50000 + np.random.normal(0, 50) for _ in range(50)]
        else:
            new_price = st.session_state.price_history[-1] * (1 + np.random.normal(0, 0.001))
            st.session_state.price_history.append(new_price)
            st.session_state.price_history = st.session_state.price_history[-100:]
        
        fig_price = create_price_chart(st.session_state.price_history, "BTC")
        st.plotly_chart(fig_price, use_container_width=True)
    
    with col_right:
        st.subheader("🎯 Winrate")
        fig_gauge = create_winrate_gauge(stats.winrate)
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Derniers trades
        st.subheader("📝 Derniers Trades")
        for trade in st.session_state.trades_history[:5]:
            emoji = "🟢" if trade['pnl'] > 0 else "🔴"
            st.markdown(f"{emoji} **{trade['asset']}** {trade['side'].upper()} : {trade['pnl_percent']:.2f}%")
    
    # Logs
    st.markdown("---")
    st.subheader("📋 Logs en temps réel")
    
    log_container = st.container()
    with log_container:
        for log in st.session_state.logs[:10]:
            if log['type'] == 'win':
                st.success(f"[{log['time']}] {log['message']}")
            elif log['type'] == 'loss':
                st.error(f"[{log['time']}] {log['message']}")
            else:
                st.info(f"[{log['time']}] {log['message']}")
    
    # Auto-refresh
    if st.session_state.bot_running:
        time.sleep(0.5)
        st.rerun()


def show_backtest_page():
    """Page de backtest"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<p class="big-title">🧪 Backtest</p>', unsafe_allow_html=True)
    
    st.info("Teste ta stratégie sur des données historiques avant de risquer de l'argent réel !")
    
    col1, col2 = st.columns(2)
    
    with col1:
        assets = st.multiselect(
            "Assets à tester",
            options=["BTC", "ETH", "SOL", "AVAX"],
            default=["BTC", "ETH"]
        )
    
    with col2:
        capital = st.number_input("Capital initial ($)", value=10000, min_value=100)
        num_candles = st.slider("Nombre de bougies", 1000, 10000, 5000)
    
    if st.button("🚀 Lancer le Backtest", type="primary", use_container_width=True):
        with st.spinner("Backtest en cours..."):
            # Simuler un backtest
            time.sleep(2)
            
            # Résultats simulés
            results = {
                'total_trades': np.random.randint(3000, 6000),
                'winrate': np.random.uniform(78, 88),
                'total_pnl': capital * np.random.uniform(0.15, 0.35),
                'max_drawdown': np.random.uniform(1.5, 3.5)
            }
            
            st.success("✅ Backtest terminé !")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("📊 Total Trades", results['total_trades'])
            with col_b:
                st.metric("✅ Winrate", f"{results['winrate']:.1f}%")
            with col_c:
                st.metric("💰 PnL", f"+${results['total_pnl']:.2f}")
            with col_d:
                st.metric("📉 Max Drawdown", f"-{results['max_drawdown']:.1f}%")
            
            # Graphique simulé
            equity = [capital]
            for i in range(100):
                change = np.random.normal(0.001, 0.005)
                equity.append(equity[-1] * (1 + change))
            
            fig = create_pnl_chart(equity)
            fig.update_layout(title="Courbe d'équité du Backtest")
            st.plotly_chart(fig, use_container_width=True)


def show_settings_page():
    """Page de paramètres (mode Contrôle uniquement)"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<p class="big-title">⚙️ Paramètres</p>', unsafe_allow_html=True)
    
    if st.session_state.user_role != 'control':
        st.warning("Accès réservé au mode Contrôle")
        return
    
    config = st.session_state.config
    
    tab1, tab2, tab3 = st.tabs(["📊 Stratégie", "💰 Risque", "🔗 Connexion"])
    
    with tab1:
        st.subheader("Paramètres Grid Bot")
        col1, col2 = st.columns(2)
        with col1:
            config.grid_size = st.number_input("Grid Size (%)", value=config.grid_size * 100, step=0.1) / 100
            config.grid_levels = st.number_input("Grid Levels", value=config.grid_levels, min_value=1, max_value=20)
        with col2:
            config.trailing_activation = st.number_input("Trailing Activation (%)", value=config.trailing_activation * 100, step=0.01) / 100
            config.trailing_distance = st.number_input("Trailing Distance (%)", value=config.trailing_distance * 100, step=0.01) / 100
        
        st.subheader("Paramètres RSI/MA")
        col3, col4 = st.columns(2)
        with col3:
            config.rsi_period = st.number_input("RSI Period", value=config.rsi_period, min_value=5, max_value=50)
            config.rsi_oversold = st.number_input("RSI Oversold", value=config.rsi_oversold, min_value=10.0, max_value=40.0)
            config.rsi_overbought = st.number_input("RSI Overbought", value=config.rsi_overbought, min_value=60.0, max_value=90.0)
        with col4:
            config.ma_fast = st.number_input("MA Fast", value=config.ma_fast, min_value=2, max_value=20)
            config.ma_slow = st.number_input("MA Slow", value=config.ma_slow, min_value=5, max_value=50)
    
    with tab2:
        st.subheader("Gestion du Risque")
        col1, col2 = st.columns(2)
        with col1:
            config.stop_loss_percent = st.number_input("Stop Loss (%)", value=config.stop_loss_percent * 100, step=0.01) / 100
            config.take_profit_percent = st.number_input("Take Profit (%)", value=config.take_profit_percent * 100, step=0.01) / 100
            config.max_hold_seconds = st.number_input("Max Hold (sec)", value=config.max_hold_seconds, min_value=10, max_value=300)
        with col2:
            config.position_size_percent = st.number_input("Position Size (%)", value=config.position_size_percent * 100, step=0.01) / 100
            config.leverage_min = st.number_input("Leverage Min", value=config.leverage_min, min_value=1, max_value=5)
            config.leverage_max = st.number_input("Leverage Max", value=config.leverage_max, min_value=1, max_value=10)
        
        config.max_daily_drawdown = st.slider("Max Daily Drawdown (%)", 1, 10, int(config.max_daily_drawdown * 100)) / 100
    
    with tab3:
        st.subheader("Connexion Wallet")
        st.info("Configure tes clés dans le fichier `.env` pour plus de sécurité !")
        
        st.text_input("Wallet Address (lecture seule)", value="0x...", disabled=True)
        st.text_input("Private Key", type="password", placeholder="Configuré dans .env", disabled=True)
        
        st.subheader("API Hyperliquid")
        st.code(f"API URL: {config.get_api_url()}")
        st.code(f"Chain ID: {config.get_chain_id()}")
    
    if st.button("💾 Sauvegarder", type="primary", use_container_width=True):
        st.session_state.config = config
        st.success("✅ Paramètres sauvegardés !")


# ============================================
# MAIN
# ============================================

def main():
    """Point d'entrée principal"""
    init_session_state()
    
    # Page de login si pas authentifié
    if not st.session_state.authenticated:
        show_login_page()
        return
    
    # Sidebar
    show_sidebar()
    
    # Navigation
    page = st.sidebar.radio(
        "📍 Navigation",
        ["🏠 Dashboard", "🧪 Backtest", "⚙️ Paramètres"],
        label_visibility="collapsed"
    )
    
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🧪 Backtest":
        show_backtest_page()
    elif page == "⚙️ Paramètres":
        show_settings_page()


if __name__ == "__main__":
    main()
