import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'R2D2 Bot - HFT Scalping Dashboard',
  description: 'Bot de trading HFT ultra-rapide sur Hyperliquid 🤖🔥',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  )
}
