"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Component hiển thị trạng thái kết nối API
 * Production-ready với auto-refresh và error handling
 */
export function ApiStatus() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null)
  const [isChecking, setIsChecking] = useState(false)

  const checkHealth = async () => {
    setIsChecking(true)
    try {
      const healthy = await api.checkHealth()
      setIsHealthy(healthy)
    } catch (error) {
      setIsHealthy(false)
    } finally {
      setIsChecking(false)
    }
  }

  useEffect(() => {
    // Check ngay khi component mount
    
    checkHealth()

    // Auto-refresh mỗi 30 giây
    const interval = setInterval(checkHealth, 30000)

    return () => clearInterval(interval)
  }, [])

  if (isHealthy === null && !isChecking) {
    return null
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        "flex items-center gap-1.5 px-2 py-1 text-xs",
        isHealthy === true
          ? "bg-green-500/20 text-green-500 border-green-500/30"
          : isHealthy === false
          ? "bg-red-500/20 text-red-500 border-red-500/30"
          : "bg-yellow-500/20 text-yellow-500 border-yellow-500/30"
      )}
      onClick={checkHealth}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          checkHealth()
        }
      }}
      title={isChecking ? "Đang kiểm tra..." : "Click để kiểm tra lại"}
    >
      {isChecking ? (
        <>
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Đang kiểm tra...</span>
        </>
      ) : isHealthy === true ? (
        <>
          <Wifi className="h-3 w-3" />
          <span>Kết nối API</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3 w-3" />
          <span>Mất kết nối API</span>
        </>
      )}
    </Badge>
  )
}

