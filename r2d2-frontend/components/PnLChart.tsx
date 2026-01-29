'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

interface PnLChartProps {
  data: { time: string; pnl: number }[]
}

export default function PnLChart({ data }: PnLChartProps) {
  const minPnl = Math.min(...data.map(d => d.pnl))
  const maxPnl = Math.max(...data.map(d => d.pnl))
  
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis 
            dataKey="time" 
            stroke="#666"
            tick={{ fill: '#888', fontSize: 12 }}
          />
          <YAxis 
            stroke="#666"
            tick={{ fill: '#888', fontSize: 12 }}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
            domain={[minPnl - 0.1, maxPnl + 0.1]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid #00d4ff',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#888' }}
            formatter={(value: number) => [`$${value.toFixed(4)}`, 'PnL']}
          />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke="#00ff88"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorPnl)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
