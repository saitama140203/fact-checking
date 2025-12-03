import type React from "react"
import type { Metadata, Viewport } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { Toaster } from "sonner"
import "./globals.css"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "FakeGuard - Phát hiện tin giả trên Reddit",
  description: "Nền tảng AI phân tích và phát hiện tin giả từ Reddit theo thời gian thực",
  generator: "v0.app",
}

export const viewport: Viewport = {
  themeColor: "#0f172a",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" className="dark">
      <body className={`font-sans antialiased`}>
        {children}
        <Toaster 
          position="top-right"
          richColors
          closeButton
          expand={true}
          duration={4000}
        />
        <Analytics />
      </body>
    </html>
  )
}
