import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Footer from './components/Footer'
import Navigation from './components/Navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DocuShield - AI-Powered Document Intelligence',
  description: 'Enterprise document analysis with multi-LLM AI, real-time enrichment, and intelligent risk assessment',
  keywords: 'document analysis, AI, multi-LLM, MCP integration, TiDB, enterprise security, risk assessment',
  authors: [{ name: 'DocuShield Team' }],
  viewport: 'width=device-width, initial-scale=1',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          
          <main className="flex-1">
            {children}
          </main>
          
          <Footer />
        </div>
      </body>
    </html>
  )
}
