"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"

interface TrendChartProps {
  data: Array<{
    date: string
    fake_count: number
    real_count: number
    total: number
    fake_percentage: number
  }>
  title?: string
  description?: string
}

export function TrendChart({ data, title = "Xu hướng tin giả", description }: TrendChartProps) {
  const chartConfig = {
    fake_count: {
      label: "Tin giả",
      color: "oklch(0.6 0.2 25)",
    },
    real_count: {
      label: "Tin thật",
      color: "oklch(0.7 0.18 145)",
    },
  }

  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorFake" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="oklch(0.6 0.2 25)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="oklch(0.6 0.2 25)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorReal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="oklch(0.7 0.18 145)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="oklch(0.7 0.18 145)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
              <XAxis dataKey="date" stroke="oklch(0.65 0 0)" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="oklch(0.65 0 0)" fontSize={12} tickLine={false} axisLine={false} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Legend />
              <Area
                type="monotone"
                dataKey="fake_count"
                stroke="oklch(0.6 0.2 25)"
                fillOpacity={1}
                fill="url(#colorFake)"
                name="Fake News"
              />
              <Area
                type="monotone"
                dataKey="real_count"
                stroke="oklch(0.7 0.18 145)"
                fillOpacity={1}
                fill="url(#colorReal)"
                name="Real News"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
