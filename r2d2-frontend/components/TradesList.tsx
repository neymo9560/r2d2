'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

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

interface TradesListProps {
  trades: Trade[]
}

export default function TradesList({ trades }: TradesListProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
            <th className="pb-3">Heure</th>
            <th className="pb-3">Asset</th>
            <th className="pb-3">Direction</th>
            <th className="pb-3">Entrée</th>
            <th className="pb-3">Sortie</th>
            <th className="pb-3">PnL</th>
            <th className="pb-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => (
            <motion.tr
              key={trade.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="border-b border-gray-800 hover:bg-white/5 transition-colors"
            >
              <td className="py-3 text-gray-300">{trade.time}</td>
              <td className="py-3 font-bold">{trade.asset}</td>
              <td className="py-3">
                <span className={`flex items-center gap-1 ${trade.side === 'long' ? 'text-green-400' : 'text-red-400'}`}>
                  {trade.side === 'long' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                  {trade.side.toUpperCase()}
                </span>
              </td>
              <td className="py-3">${trade.entryPrice.toFixed(2)}</td>
              <td className="py-3">{trade.exitPrice ? `$${trade.exitPrice.toFixed(2)}` : '-'}</td>
              <td className="py-3">
                {trade.pnl !== undefined ? (
                  <span className={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnlPercent?.toFixed(2)}%
                    <span className="text-xs ml-1">
                      ({trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)})
                    </span>
                  </span>
                ) : '-'}
              </td>
              <td className="py-3">
                <span className={`px-2 py-1 rounded-full text-xs ${
                  trade.status === 'open' 
                    ? 'bg-yellow-500/20 text-yellow-400' 
                    : 'bg-gray-500/20 text-gray-400'
                }`}>
                  {trade.status === 'open' ? '🔄 OPEN' : '✅ CLOSED'}
                </span>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
      
      {trades.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Aucun trade pour le moment... Le bot attend le bon signal ! 🎯
        </div>
      )}
    </div>
  )
}
