"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FileText, Download, Calendar, TrendingDown, TrendingUp, Minus, AlertTriangle, CheckCircle } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { api, ComprehensiveReport } from "@/lib/api"
import { showError } from "@/lib/toast"

type SubredditStat = {
  subreddit: string
  fake_count: number
  real_count: number
  total_count: number
  fake_percentage: number
}

const FALLBACK_RECOMMENDATIONS = [
  {
    type: "info",
    title: "Chưa có khuyến nghị",
    description: "Backend chưa cung cấp dữ liệu khuyến nghị. Vui lòng kiểm tra lại sau.",
  },
]

export default function ReportsPage() {
  const [period, setPeriod] = useState("30")
  const [report, setReport] = useState<ComprehensiveReport | null>(null)
  const [subredditStats, setSubredditStats] = useState<SubredditStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    async function fetchReport() {
      setLoading(true)
      setError(null)

      try {
        const [reportRes, subredditRes] = await Promise.all([
          api.getComprehensiveReport(Number(period)),
          api.getBySubreddit(),
        ])

        if (!isMounted) return

        setReport(reportRes)
        setSubredditStats(subredditRes.data || [])
      } catch (err) {
        console.error("Failed to load report", err)
        if (isMounted) {
          const errorMessage = "Không thể tải dữ liệu báo cáo. Vui lòng đảm bảo backend đang chạy."
          setError(errorMessage)
          showError(err, errorMessage)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    fetchReport()

    return () => {
      isMounted = false
    }
  }, [period])

  const summaryData = useMemo(() => {
    if (!report?.summary) {
      return {
        totalPosts: 0,
        fakeCount: 0,
        fakePercentage: 0,
        trendDirection: "STABLE" as const,
        changePercentage: 0,
      }
    }

    return {
      totalPosts: report.summary.total_analyzed || 0,
      fakeCount: report.summary.fake_news_count || 0,
      fakePercentage: report.summary.fake_percentage || 0,
      trendDirection: (report.trend_analysis?.direction?.toUpperCase() || "STABLE") as "INCREASING" | "DECREASING" | "STABLE",
      changePercentage: report.trend_analysis?.change_percentage || 0,
    }
  }, [report])

  const distributionData = useMemo(() => {
    if (!report?.summary) return []
    const real = report.summary.real_news_count || 0
    const fake = report.summary.fake_news_count || 0
    const total = real + fake
    if (total === 0) return []
    return [
      { name: "Real News", value: real, fill: "oklch(0.7 0.18 145)" },
      { name: "Fake News", value: fake, fill: "oklch(0.6 0.2 25)" },
    ]
  }, [report])

  const categoryData = useMemo(() => {
    if (!subredditStats.length) return []
    return subredditStats.slice(0, 5).map((item) => ({
      category: item.subreddit,
      fake: item.fake_count,
      real: item.real_count,
    }))
  }, [subredditStats])

  const recommendationItems = useMemo(() => {
    if (report?.recommendations?.length) {
      return report.recommendations.map((rec, index) => ({
        type: "info",
        title: rec.split(":")[0] || `Recommendation ${index + 1}`,
        description: rec,
      }))
    }
    return FALLBACK_RECOMMENDATIONS
  }, [report])

  const TrendIcon = summaryData.trendDirection === "DECREASING" ? TrendingDown : summaryData.trendDirection === "INCREASING" ? TrendingUp : Minus

  const hasAnyData = summaryData.totalPosts > 0

  const renderSummaryCard = () => {
    if (loading) {
      return (
        <Card className="bg-card animate-pulse">
          <CardContent className="pt-6 h-24" />
        </Card>
      )
    }

    return null
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Báo cáo tổng hợp</h1>
            <p className="text-muted-foreground mt-1">Báo cáo phân tích tin giả toàn diện</p>
          </div>
          <div className="flex items-center gap-4">
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="w-40 bg-secondary border-border">
                <Calendar className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Period" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7 ngày gần nhất</SelectItem>
                <SelectItem value="30">30 ngày gần nhất</SelectItem>
                <SelectItem value="90">90 ngày gần nhất</SelectItem>
              </SelectContent>
            </Select>
            <Button disabled={loading || !report}>
              <Download className="h-4 w-4 mr-2" />
              Xuất PDF
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        {error && (
          <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg text-sm text-warning">
            {error}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          {loading ? (
            <>
              {renderSummaryCard()}
              {renderSummaryCard()}
              {renderSummaryCard()}
              {renderSummaryCard()}
            </>
          ) : (
            <>
              <Card className="bg-card">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Tổng số bài đã phân tích</p>
                      <p className="text-2xl font-bold mt-1">{summaryData.totalPosts.toLocaleString()}</p>
                    </div>
                    <FileText className="h-8 w-8 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-l-4 border-l-danger">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Tin giả phát hiện</p>
                      <p className="text-2xl font-bold mt-1 text-danger">{summaryData.fakeCount.toLocaleString()}</p>
                    </div>
                    <AlertTriangle className="h-8 w-8 text-danger" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Tỷ lệ tin giả</p>
                      <p className="text-2xl font-bold mt-1">{summaryData.fakePercentage.toFixed(1)}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-l-4 border-l-success">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Xu hướng</p>
                      <div className={cn("flex items-center gap-2 mt-1", summaryData.trendDirection === "DECREASING" ? "text-success" : summaryData.trendDirection === "INCREASING" ? "text-danger" : "text-muted-foreground")}>
                        {TrendIcon && <TrendIcon className="h-5 w-5" />}
                        <span className="text-2xl font-bold">
                          {summaryData.changePercentage > 0 ? "+" : ""}
                          {summaryData.changePercentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Distribution Pie */}
          <Card className="bg-card">
            <CardHeader>
              <CardTitle>Phân bố nội dung</CardTitle>
              <CardDescription>Tỷ lệ tin thật vs tin giả</CardDescription>
            </CardHeader>
            <CardContent>
              {distributionData.length ? (
                <ChartContainer
                  config={{
                    real: { label: "Tin thật", color: "oklch(0.7 0.18 145)" },
                    fake: { label: "Tin giả", color: "oklch(0.6 0.2 25)" },
                  }}
                  className="h-[300px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={distributionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={110}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                        labelLine={false}
                      >
                        {distributionData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <ChartTooltip content={<ChartTooltipContent />} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
                  {loading
                    ? "Đang tải dữ liệu..."
                    : "Không có dữ liệu phân phối cho khoảng thời gian đã chọn."}
                </div>
              )}
              {report && distributionData.length > 0 && hasAnyData && (
                <div className="flex justify-center gap-8 mt-4">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-success" />
                    <span className="text-sm">
                      Tin thật ({(100 - summaryData.fakePercentage).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-danger" />
                    <span className="text-sm">Tin giả ({summaryData.fakePercentage.toFixed(1)}%)</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Category Breakdown */}
          <Card className="bg-card">
            <CardHeader>
              <CardTitle>Theo subreddit</CardTitle>
              <CardDescription>Phân bố tin giả theo subreddit</CardDescription>
            </CardHeader>
            <CardContent>
              {categoryData.length ? (
                <ChartContainer
                  config={{
                    fake: { label: "Tin giả", color: "oklch(0.6 0.2 25)" },
                    real: { label: "Tin thật", color: "oklch(0.7 0.18 145)" },
                  }}
                  className="h-[300px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={categoryData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
                      <XAxis dataKey="category" stroke="oklch(0.65 0 0)" fontSize={12} />
                      <YAxis stroke="oklch(0.65 0 0)" fontSize={12} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="real" stackId="a" fill="oklch(0.7 0.18 145)" name="Real" />
                      <Bar dataKey="fake" stackId="a" fill="oklch(0.6 0.2 25)" name="Fake" />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
                  {loading ? "Đang tải dữ liệu..." : "Không có dữ liệu subreddit"}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sources summary from report (top credible & warning) */}
        {report && (report.top_credible_sources?.length || report.warning_sources?.length) && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Nguồn đáng tin cậy (theo điểm)</CardTitle>
                <CardDescription>
                  Các nguồn được backend đánh giá có điểm tin cậy tương đối cao.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {report.top_credible_sources?.length ? (
                  <div className="space-y-2">
                    {report.top_credible_sources.slice(0, 5).map((src) => (
                      <div
                        key={src.domain}
                        className="flex items-center justify-between py-2 border-b last:border-b-0 border-border/40"
                      >
                        <div>
                          <p className="font-medium">{src.domain}</p>
                          <p className="text-xs text-muted-foreground">
                            {src.recommendation || "Nguồn được đánh giá có độ tin cậy tương đối."}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold">
                            {(src.credibility_score ?? 0).toFixed(1)}
                          </p>
                          <p className="text-xs text-muted-foreground">Điểm tin cậy</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Không có dữ liệu nguồn đáng tin cậy cho khoảng thời gian này.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Nguồn cảnh báo (tỷ lệ tin giả cao)</CardTitle>
                <CardDescription>
                  Các nguồn có tỷ lệ tin giả cao nhất trong báo cáo tổng hợp.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {report.warning_sources?.length ? (
                  <div className="space-y-2">
                    {report.warning_sources.slice(0, 5).map((src) => {
                      const fakePct =
                        typeof src.breakdown?.fake_percentage === "number"
                          ? src.breakdown.fake_percentage
                          : typeof src.breakdown?.fake_ratio === "number"
                          ? src.breakdown.fake_ratio * 100
                          : 0
                      return (
                        <div
                          key={src.domain}
                          className="flex items-center justify-between py-2 border-b last:border-b-0 border-border/40"
                        >
                          <div>
                            <p className="font-medium">{src.domain}</p>
                            <p className="text-xs text-muted-foreground">
                              {src.recommendation ||
                                "⚠️ Nguồn này có tỷ lệ fake news cao. Cần kiểm chứng kỹ thông tin."}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-semibold text-danger">
                              {fakePct.toFixed(1)}%
                            </p>
                            <p className="text-xs text-muted-foreground">Tỷ lệ tin giả</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Không có nguồn nào trong warning list cho khoảng thời gian này.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Recommendations */}
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Nhận định & khuyến nghị chính</CardTitle>
            <CardDescription>Nhận định do AI đưa ra dựa trên kết quả phân tích</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recommendationItems.map((rec, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex items-start gap-4 p-4 rounded-lg border",
                    rec.type === "success" && "bg-success/10 border-success/20",
                    rec.type === "warning" && "bg-warning/10 border-warning/20",
                    rec.type === "info" && "bg-primary/10 border-primary/20",
                  )}
                >
                  {rec.type === "success" ? (
                    <CheckCircle className="h-5 w-5 text-success shrink-0 mt-0.5" />
                  ) : rec.type === "warning" ? (
                    <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                  ) : (
                    <FileText className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium">{rec.title}</p>
                    <p className="text-sm text-muted-foreground mt-1">{rec.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
