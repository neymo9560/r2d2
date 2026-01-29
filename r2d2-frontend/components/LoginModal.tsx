'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Lock, Eye, EyeOff, Bot } from 'lucide-react'

interface LoginModalProps {
  onLogin: (password: string) => void
}

export default function LoginModal({ onLogin }: LoginModalProps) {
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (password === 'Bine' || password === 'Bina') {
      onLogin(password)
    } else {
      setError('Mot de passe incorrect !')
      setTimeout(() => setError(''), 3000)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card max-w-md w-full"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="text-7xl mb-4"
          >
            🤖
          </motion.div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-green-400 bg-clip-text text-transparent">
            R2D2 Bot
          </h1>
          <p className="text-gray-400 mt-2">HFT Scalping Dashboard</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-gray-400 text-sm mb-2">
              Mot de passe
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-black/50 border border-gray-700 rounded-xl py-3 pl-10 pr-12 text-white focus:outline-none focus:border-cyan-500 transition-colors"
                placeholder="Entrez le mot de passe..."
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-red-400 text-sm text-center bg-red-500/10 py-2 rounded-lg"
            >
              {error}
            </motion.div>
          )}

          <button type="submit" className="btn-primary w-full text-lg">
            <Bot className="inline mr-2" size={20} />
            Accéder au Dashboard
          </button>
        </form>

        {/* Hints */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>🎮 Mode Contrôle : accès complet</p>
          <p>👀 Mode Viewer : lecture seule</p>
        </div>
      </motion.div>
    </div>
  )
}
