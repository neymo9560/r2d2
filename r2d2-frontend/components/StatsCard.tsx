'use client'

import { motion } from 'framer-motion'
import { ReactNode } from 'react'

interface StatsCardProps {
  title: string
  value: string
  subtitle?: string
  icon: ReactNode
  color: 'cyan' | 'green' | 'red' | 'yellow' | 'purple' | 'gray'
  highlight?: boolean
}

const colorClasses = {
  cyan: 'border-cyan-500/30 hover:border-cyan-500/60',
  green: 'border-green-500/30 hover:border-green-500/60',
  red: 'border-red-500/30 hover:border-red-500/60',
  yellow: 'border-yellow-500/30 hover:border-yellow-500/60',
  purple: 'border-purple-500/30 hover:border-purple-500/60',
  gray: 'border-gray-500/30 hover:border-gray-500/60',
}

const valueClasses = {
  cyan: 'text-cyan-400',
  green: 'text-green-400',
  red: 'text-red-400',
  yellow: 'text-yellow-400',
  purple: 'text-purple-400',
  gray: 'text-gray-400',
}

export default function StatsCard({ title, value, subtitle, icon, color, highlight }: StatsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      className={`
        card border ${colorClasses[color]}
        ${highlight ? 'ring-2 ring-offset-2 ring-offset-black ring-opacity-50' : ''}
        transition-all duration-300
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400 text-sm">{title}</span>
        {icon}
      </div>
      <div className={`text-2xl font-bold ${valueClasses[color]}`}>
        {value}
      </div>
      {subtitle && (
        <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
      )}
    </motion.div>
  )
}
