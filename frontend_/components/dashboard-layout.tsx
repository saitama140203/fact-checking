"use client"

import type React from "react"

import { Sidebar } from "@/components/sidebar"
import { ApiStatus } from "@/components/api-status"

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="pl-64 transition-all duration-300">
        <div className="p-6">
          {/* API Status Indicator */}
          <div className="mb-4 flex justify-end">
            <ApiStatus />
          </div>
          {children}
        </div>
      </main>
    </div>
  )
}
