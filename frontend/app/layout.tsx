import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Footer from './components/Footer'
import UserMenu from './components/UserMenu'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DocuShield - Document Analysis & Workflow Platform',
  description: 'AI-powered document analysis with intelligent workflows and real-time insights',
  keywords: 'document analysis, AI, workflow, automation, insights',
  authors: [{ name: 'DocuShield Team' }],
  viewport: 'width=device-width, initial-scale=1',
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
          {/* Navigation Header */}
          <nav className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center">
                  <img 
                    src="/docushield-logo-svg.svg" 
                    alt="DocuShield" 
                    className="h-8 w-auto"
                  />
                </div>
                <div className="flex items-center space-x-4">
                  <div className="hidden md:block">
                    <div className="ml-10 flex items-baseline space-x-4">
                      <a href="/documents" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                        Documents
                      </a>
                      <a href="/search" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                        Search
                      </a>
                      <a href="/digital-twin" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                        Digital Twin
                      </a>
                      <a href="/dashboard" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                        Dashboard
                      </a>
                      <a href="/chat" className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors">
                        AI Chat
                      </a>
                    </div>
                  </div>
                  <UserMenu />
                </div>
              </div>
            </div>
          </nav>
          
          <main className="flex-1">
            {children}
          </main>
          
          <Footer />
        </div>
      </body>
    </html>
  )
}
