import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
})

export const metadata: Metadata = {
  title: 'Jugaad Navigator - AI Administrative Assistant',
  description: 'Navigate India\'s complex administrative landscape with AI-powered guidance. Get creative, practical solutions for bureaucratic challenges.',
  keywords: 'AI assistant, administrative help, India bureaucracy, document verification, RTI, government processes',
  authors: [{ name: 'Jugaad Navigator Team' }],
  robots: 'index, follow',
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#000000',
  colorScheme: 'dark',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <head>
        <link rel="icon" href="/favicon.ico" />
        <meta name="theme-color" content="#000000" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body className={`${inter.className} antialiased bg-black text-white min-h-screen`}>
        <div id="root" className="min-h-screen flex flex-col">
          {children}
        </div>
      </body>
    </html>
  )
}