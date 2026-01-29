'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Zap, TrendingUp, TrendingDown, DollarSign, Activity, 
  Play, Square, RefreshCw, Settings, Trophy, Target,
  Flame, Rocket, Bot, Shield, Clock, BarChart3
} from 'lucide-react'
import StatsCard from '@/components/StatsCard'
import TradesList from '@/components/TradesList'
import PnLChart from '@/components/PnLChart'
import LoginModal from '@/components/LoginModal'

// Types
interface BotStats {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  totalPnL: number
  todayPnL: number
  capital: number
  isRunning: boolean
  currentAsset: string
  lastTradeTime: string
}

interface Trade {
  id: string
  asset: string
  side: 'long' | 'short'
  entryPrice: number
  exitPrice?: number
  pnl?: number
  pnlPercent?: number
  status: 'open' | 'closed'
  time: string
}

export default function Dashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isControlMode, setIsControlMode] = useState(false)
  const [showLogin, setShowLogin] = useState(true)
  const [botStats, setBotStats] = useState<BotStats>({
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalPnL: 0,
    todayPnL: 0,
    capital: 4.00,
    isRunning: false,
    currentAsset: 'BTC',
    lastTradeTime: '-'
  })
  const [trades, setTrades] = useState<Trade[]>([])
  const [pnlHistory, setPnlHistory] = useState<{time: string, pnl: number}[]>([])
  const [showWinAnimation, setShowWinAnimation] = useState(false)

  // Simuler des données pour la démo
  useEffect(() => {
    if (!isLoggedIn) return

    // Simuler des trades
    const demoTrades: Trade[] = [
      { id: '1', asset: 'BTC', side: 'long', entryPrice: 42150.50, exitPrice: 42234.80, pnl: 0.08, pnlPercent: 0.20, status: 'closed', time: '14:32:15' },
      { id: '2', asset: 'ETH', side: 'short', entryPrice: 2285.30, exitPrice: 2281.10, pnl: 0.04, pnlPercent: 0.18, status: 'closed', time: '14:31:42' },
      { id: '3', asset: 'BTC', side: 'long', entryPrice: 42089.00, exitPrice: 42045.20, pnl: -0.02, pnlPercent: -0.10, status: 'closed', time: '14:30:58' },
      { id: '4', asset: 'ETH', side: 'long', entryPrice: 2278.40, exitPrice: 2283.90, pnl: 0.05, pnlPercent: 0.24, status: 'closed', time: '14:29:33' },
      { id: '5', asset: 'BTC', side: 'short', entryPrice: 42198.00, status: 'open', time: '14:33:01' },
    ]
    setTrades(demoTrades)

    // Simuler stats
    setBotStats({
      totalTrades: 127,
      winningTrades: 98,
      losingTrades: 29,
      winRate: 77.2,
      totalPnL: 2.34,
      todayPnL: 0.89,
      capital: 4.00,
      isRunning: true,
      currentAsset: 'BTC',
      lastTradeTime: '14:33:01'
    })

    // Simuler historique PnL
    const history = []
    let cumPnl = 0
    for (let i = 0; i < 24; i++) {
      cumPnl += (Math.random() - 0.3) * 0.1
      history.push({ time: `${i}:00`, pnl: cumPnl })
    }
    setPnlHistory(history)
  }, [isLoggedIn])

  // Animation de win
  const triggerWinAnimation = () => {
    setShowWinAnimation(true)
    // Jouer un son
    if (typeof window !== 'undefined') {
      const audio = new Audio('/win.mp3')
      audio.volume = 0.3
      audio.play().catch(() => {})
    }
    setTimeout(() => setShowWinAnimation(false), 2000)
  }

  const handleLogin = (password: string) => {
    if (password === 'Bine') {
      setIsLoggedIn(true)
      setIsControlMode(true)
      setShowLogin(false)
    } else if (password === 'Bina') {
      setIsLoggedIn(true)
      setIsControlMode(false)
      setShowLogin(false)
    }
  }

  if (showLogin) {
    return <LoginModal onLogin={handleLogin} />
  }

  return (
    <main className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row justify-between items-center mb-8"
      >
        <div className="flex items-center gap-4 mb-4 md:mb-0">
          <motion.div 
            animate={{ rotate: botStats.isRunning ? 360 : 0 }}
            transition={{ duration: 2, repeat: botStats.isRunning ? Infinity : 0, ease: "linear" }}
            className="text-5xl"
          >
            🤖
          </motion.div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-cyan-400 to-green-400 bg-clip-text text-transparent">
              R2D2 Bot
            </h1>
            <p className="text-gray-400">HFT Scalping sur Hyperliquid</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className={`px-4 py-2 rounded-full flex items-center gap-2 ${botStats.isRunning ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            <div className={`w-3 h-3 rounded-full ${botStats.isRunning ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></div>
            {botStats.isRunning ? 'EN MARCHE' : 'ARRÊTÉ'}
          </div>
          
          <span className="px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded-full text-sm">
            {isControlMode ? '🎮 Contrôle' : '👀 Viewer'}
          </span>
        </div>
      </motion.header>

      {/* Win Animation Overlay */}
      <AnimatePresence>
        {showWinAnimation && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5 }}
            className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none"
          >
            <div className="text-8xl animate-bounce">🎉</div>
            <div className="absolute text-4xl font-bold text-green-400 animate-pulse">
              +GREEN! 💰
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
        <StatsCard 
          title="Capital" 
          value={`$${botStats.capital.toFixed(2)}`}
          icon={<DollarSign className="text-cyan-400" />}
          color="cyan"
        />
        <StatsCard 
          title="PnL Total" 
          value={`${botStats.totalPnL >= 0 ? '+' : ''}$${botStats.totalPnL.toFixed(2)}`}
          icon={<TrendingUp className="text-green-400" />}
          color={botStats.totalPnL >= 0 ? 'green' : 'red'}
          highlight
        />
        <StatsCard 
          title="PnL Aujourd'hui" 
          value={`${botStats.todayPnL >= 0 ? '+' : ''}$${botStats.todayPnL.toFixed(2)}`}
          icon={<Activity className="text-yellow-400" />}
          color={botStats.todayPnL >= 0 ? 'green' : 'red'}
        />
        <StatsCard 
          title="Win Rate" 
          value={`${botStats.winRate.toFixed(1)}%`}
          icon={<Trophy className="text-yellow-400" />}
          color="yellow"
          highlight
        />
        <StatsCard 
          title="Trades" 
          value={`${botStats.winningTrades}/${botStats.totalTrades}`}
          subtitle={`🟢 ${botStats.winningTrades} | 🔴 ${botStats.losingTrades}`}
          icon={<Target className="text-purple-400" />}
          color="purple"
        />
        <StatsCard 
          title="Dernier Trade" 
          value={botStats.lastTradeTime}
          icon={<Clock className="text-gray-400" />}
          color="gray"
        />
      </div>

      {/* Control Buttons */}
      {isControlMode && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-wrap gap-4 mb-8"
        >
          <button 
            onClick={() => setBotStats(prev => ({ ...prev, isRunning: !prev.isRunning }))}
            className={botStats.isRunning ? 'btn-danger' : 'btn-primary'}
          >
            {botStats.isRunning ? (
              <><Square className="inline mr-2" size={18} /> STOP</>
            ) : (
              <><Play className="inline mr-2" size={18} /> GO LIVE! 🚀</>
            )}
          </button>
          
          <button className="btn-primary" onClick={triggerWinAnimation}>
            <Zap className="inline mr-2" size={18} /> Test Win 🎉
          </button>
          
          <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl transition-all">
            <RefreshCw className="inline mr-2" size={18} /> Refresh
          </button>
          
          <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl transition-all">
            <Settings className="inline mr-2" size={18} /> Settings
          </button>
        </motion.div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PnL Chart */}
        <div className="lg:col-span-2 card">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="text-cyan-400" /> Évolution PnL
          </h2>
          <PnLChart data={pnlHistory} />
        </div>

        {/* Quick Stats */}
        <div className="card">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Flame className="text-orange-400" /> Stats Rapides
          </h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-black/30 rounded-xl">
              <span className="text-gray-400">Trades/Heure</span>
              <span className="text-xl font-bold text-cyan-400">~42</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-black/30 rounded-xl">
              <span className="text-gray-400">Profit Moyen</span>
              <span className="text-xl font-bold text-green-400">+0.18%</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-black/30 rounded-xl">
              <span className="text-gray-400">Perte Moyenne</span>
              <span className="text-xl font-bold text-red-400">-0.10%</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-black/30 rounded-xl">
              <span className="text-gray-400">Hold Time Moyen</span>
              <span className="text-xl font-bold text-purple-400">34s</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-black/30 rounded-xl">
              <span className="text-gray-400">Trailing Hits</span>
              <span className="text-xl font-bold text-yellow-400">67%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trades List */}
      <div className="mt-6 card">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Rocket className="text-green-400" /> Derniers Trades
        </h2>
        <TradesList trades={trades} />
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-gray-500 text-sm">
        <p>R2D2 Bot v1.0 - HFT Scalping sur Hyperliquid 🤖</p>
        <p className="mt-1">⚠️ Le trading comporte des risques. Ne tradez que ce que vous pouvez perdre.</p>
      </footer>
    </main>
  )
}
