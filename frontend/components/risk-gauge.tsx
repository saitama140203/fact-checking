"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface RiskGaugeProps {
  score: number
  level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  title?: string
}

const levelColors = {
  LOW: { bg: "bg-success", text: "text-success" },
  MEDIUM: { bg: "bg-warning", text: "text-warning" },
  HIGH: { bg: "bg-chart-4", text: "text-chart-4" },
  CRITICAL: { bg: "bg-danger", text: "text-danger" },
}

export function RiskGauge({ score, level, title = "Risk Score" }: RiskGaugeProps) {
  const colors = levelColors[level]
  const rotation = (score / 100) * 180 - 90 // -90 to 90 degrees

  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        {/* Gauge */}
        <div className="relative w-40 h-20 overflow-hidden">
          {/* Background arc */}
          <div className="absolute inset-0 rounded-t-full border-8 border-b-0 border-muted" />

          {/* Colored segments */}
          <div className="absolute inset-0 rounded-t-full overflow-hidden">
            <div
              className="absolute bottom-0 left-1/2 w-1 h-20 origin-bottom transition-transform duration-500"
              style={{ transform: `rotate(${rotation}deg)` }}
            >
              <div className={cn("w-1 h-16", colors.bg)} />
            </div>
          </div>

          {/* Center point */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-card border-2 border-primary" />
        </div>

        {/* Score */}
        <div className="mt-4 text-center">
          <div className={cn("text-4xl font-bold", colors.text)}>{score.toFixed(0)}</div>
          <div className={cn("text-sm font-medium mt-1", colors.text)}>{level}</div>
        </div>
      </CardContent>
    </Card>
  )
}
