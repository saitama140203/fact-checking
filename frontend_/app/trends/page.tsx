"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus, Calendar } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend, BarChart, Bar } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { cn } from "@/lib/utils"
import { TopicsCloud } from "@/components/topics-cloud"
import { api, TrendData, TrendingTopic } from "@/lib/api"
import { showError } from "@/lib/toast"

type SubredditStat = {
  subreddit: string
  fake_count: number
  real_count: number
  total_count: number
  fake_percentage: number
}

type DailyChartPoint = {
  date: string
  fake: number
  real: number
  total: number
}

const rangeOptions = [
  { label: "7 ngày gần nhất", value: "7" },
  { label: "14 ngày gần nhất", value: "14" },
  { label: "30 ngày gần nhất", value: "30" },
  { label: "90 ngày gần nhất", value: "90" },
]

const getTrendIcon = (direction: string) => {
  if (direction === "INCREASING") return TrendingUp
  if (direction === "DECREASING") return TrendingDown
  return Minus
}

export default function TrendsPage() {
  const [timeRange, setTimeRange] = useState("30")
  const [trend, setTrend] = useState<TrendData | null>(null)
  const [topics, setTopics] = useState<TrendingTopic[]>([])
  const [subredditStats, setSubredditStats] = useState<SubredditStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    async function loadTrendData() {
      setLoading(true)
      setError(null)
      try {
        const [trendRes, topicsRes, subsRes] = await Promise.all([
          api.getFakeNewsTrend(Number(timeRange)),
          api.getTrendingFakeTopics(Math.min(Number(timeRange), 30), 20),
          api.getBySubreddit(),
        ])

        if (!mounted) return
        setTrend(trendRes)
        setTopics(topicsRes.trending_topics || [])
        setSubredditStats(subsRes.data || [])
      } catch (err) {
        console.error("Failed to load trend data", err)
        if (mounted) {
          const errorMessage = "Không thể tải dữ liệu xu hướng. Vui lòng đảm bảo backend đang chạy."
          setError(errorMessage)
          showError(err, errorMessage)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadTrendData()
    return () => {
      mounted = false
    }
  }, [timeRange])

  const dailyData = useMemo<DailyChartPoint[]>(() => {
    if (!trend?.daily_data || !Array.isArray(trend.daily_data)) return []
    return trend.daily_data.map((item) => ({
      date: item.date || "",
      fake: item.fake || 0,
      real: item.real || 0,
      total: item.total || 0,
    }))
  }, [trend])

  const peakDay = useMemo(() => {
    if (!dailyData.length) return null
    return dailyData.reduce((max, curr) => {
      const currFake = curr.fake || 0
      const maxFake = max?.fake || 0
      return currFake > maxFake ? curr : max
    }, dailyData[0])
  }, [dailyData])

  const subredditData = useMemo(() => {
    if (!subredditStats.length) return []
    return subredditStats
      .slice(0, 6)
      .map((sub) => ({
        name: sub.subreddit,
        fake_percentage: sub.fake_percentage,
      }))
      .sort((a, b) => b.fake_percentage - a.fake_percentage)
  }, [subredditStats])

  const trendDirection = trend?.trend.direction ?? "STABLE"
  const trendChange = trend?.trend.change_percentage ?? 0
  const avgFakeRate = trend?.current_period.fake_percentage ?? 0

  const TrendIcon = getTrendIcon(trendDirection)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Phân tích xu hướng</h1>
            <p className="text-muted-foreground mt-1">Theo dõi mẫu hình tin giả và các chủ đề nổi lên</p>
          </div>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-40 bg-secondary border-border">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Khoảng thời gian" />
            </SelectTrigger>
            <SelectContent>
              {rangeOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {error && (
          <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg text-warning text-sm">
            {error}
          </div>
        )}

        {/* Trend Summary */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="bg-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
              <p className="text-sm text-muted-foreground">Hướng xu hướng</p>
                  <div className="flex items-center gap-2 mt-1">
                    <TrendIcon
                      className={cn(
                        "h-5 w-5",
                        trendDirection === "DECREASING"
                          ? "text-success"
                          : trendDirection === "INCREASING"
                            ? "text-danger"
                            : "text-muted-foreground",
                      )}
                    />
                    <span className="text-2xl font-bold">{trendDirection}</span>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "border",
                    trendDirection === "DECREASING"
                      ? "bg-success/20 text-success border-success/30"
                      : trendDirection === "INCREASING"
                        ? "bg-danger/20 text-danger border-danger/30"
                        : "bg-muted/40 text-muted-foreground border-border",
                  )}
                >
                  {trendChange > 0 ? "+" : ""}
                  {trendChange.toFixed(1)}%
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Ngày đỉnh điểm</p>
              <div className="mt-1">
                <span className="text-2xl font-bold">
                  {peakDay ? peakDay.date : loading ? "Loading..." : "N/A"}
                </span>
                {peakDay && (
                  <span className="text-sm text-muted-foreground ml-2">
                    {peakDay.fake} fake posts
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Tỷ lệ tin giả trung bình</p>
              <div className="mt-1">
                <span className="text-2xl font-bold">{avgFakeRate.toFixed(1)}%</span>
                <span className="text-sm text-muted-foreground ml-2">of all posts</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Trend Chart */}
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Diễn biến tin giả theo thời gian</CardTitle>
            <CardDescription>Số lượng tin giả vs tin thật được phát hiện theo ngày</CardDescription>
          </CardHeader>
          <CardContent>
            {dailyData.length ? (
              <ChartContainer
                config={{
                  fake: { label: "Fake News", color: "oklch(0.6 0.2 25)" },
                  real: { label: "Real News", color: "oklch(0.7 0.18 145)" },
                }}
                className="h-[350px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dailyData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="gradientFake" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="oklch(0.6 0.2 25)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="oklch(0.6 0.2 25)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradientReal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="oklch(0.7 0.18 145)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="oklch(0.7 0.18 145)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
                    <XAxis dataKey="date" stroke="oklch(0.65 0 0)" fontSize={12} />
                    <YAxis stroke="oklch(0.65 0 0)" fontSize={12} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="fake"
                      stroke="oklch(0.6 0.2 25)"
                      fill="url(#gradientFake)"
                      name="Fake News"
                    />
                    <Area
                      type="monotone"
                      dataKey="real"
                      stroke="oklch(0.7 0.18 145)"
                      fill="url(#gradientReal)"
                      name="Real News"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <div className="h-[350px] flex items-center justify-center text-sm text-muted-foreground">
                {loading ? "Đang tải dữ liệu..." : "Không có dữ liệu cho khoảng thời gian này."}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Subreddit Breakdown & Topics */}
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="bg-card">
            <CardHeader>
              <CardTitle>Tin giả theo subreddit</CardTitle>
              <CardDescription>Phân bố tin giả giữa các cộng đồng</CardDescription>
            </CardHeader>
            <CardContent>
              {subredditData.length ? (
                <ChartContainer
                  config={{
                    percentage: { label: "% tin giả", color: "oklch(0.75 0.15 195)" },
                  }}
                  className="h-[300px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={subredditData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
                      <XAxis type="number" domain={[0, 100]} stroke="oklch(0.65 0 0)" fontSize={12} />
                      <YAxis type="category" dataKey="name" stroke="oklch(0.65 0 0)" fontSize={12} width={120} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="fake_percentage" fill="oklch(0.75 0.15 195)" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
                  {loading ? "Đang tải dữ liệu..." : "Không có dữ liệu subreddit."}
                </div>
              )}
            </CardContent>
          </Card>

          <TopicsCloud
            topics={
              topics.length
                ? topics.map((topic) => ({
                    keyword: topic.keyword,
                    frequency: topic.frequency,
                    sample_titles: topic.sample_titles ?? [],
                  }))
                : []
            }
            title="Chủ đề tin giả đang hot"
            description="Những chủ đề xuất hiện nhiều trong các bài bị phát hiện là tin giả trong giai đoạn này"
          />
        </div>
      </div>
    </DashboardLayout>
  )
}
