"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Search, RefreshCw } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, PieChart, Pie } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { cn } from "@/lib/utils"
import { api, SourceCredibility } from "@/lib/api"
import { showError, showSuccess } from "@/lib/toast"

// Màu sắc rõ ràng cho từng mức rủi ro (tránh bị chìm với nền tối)
const riskColors = {
  LOW: "#22c55e",        // green-500
  MEDIUM: "#eab308",     // yellow-500
  HIGH: "#f97316",       // orange-500
  VERY_HIGH: "#ef4444",  // red-500
} as const

const riskBadgeStyles = {
  LOW: "bg-success/20 text-success border-success/30",
  MEDIUM: "bg-warning/20 text-warning border-warning/30",
  HIGH: "bg-chart-4/20 text-chart-4 border-chart-4/30",
  VERY_HIGH: "bg-danger/20 text-danger border-danger/30",
} as const

type SourceChartData = {
  domain: string
  score: number
  posts: number
  fake: number
  risk: keyof typeof riskColors
  raw: SourceCredibility
}

export default function SourcesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSource, setSelectedSource] = useState<SourceCredibility | null>(null)
  const [warningSources, setWarningSources] = useState<SourceCredibility[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSources = async () => {
    setLoading(true)
    setError(null)
    try {
      const [warningRes] = await Promise.all([
        api.getWarningSources(10, 3),
      ])

      setWarningSources(warningRes.warning_sources || [])

      if (!selectedSource && warningRes.warning_sources?.length) {
        setSelectedSource(warningRes.warning_sources[0])
      }
    } catch (err) {
      console.error("Failed to load sources", err)
      const errorMessage = "Không thể tải dữ liệu nguồn tin. Vui lòng kiểm tra backend."
      setError(errorMessage)
      showError(err, errorMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSources()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const analyzeSource = async () => {
    if (!searchQuery.trim()) {
      setError("Vui lòng nhập domain để phân tích")
      return
    }

    setAnalyzing(true)
    setError(null)
    try {
      const data = await api.getSourceCredibility(searchQuery.trim(), 1)
      setSelectedSource(data)
      
      showSuccess("Phân tích nguồn tin thành công", `Domain: ${data.domain}`)
    } catch (err) {
      console.error("Failed to analyze source", err)
      const errorMessage = "Không thể phân tích nguồn. Đảm bảo domain hợp lệ và backend đang chạy."
      setError(errorMessage)
      showError(err, errorMessage)
    } finally {
      setAnalyzing(false)
    }
  }

  const combinedSources: SourceChartData[] = useMemo(() => {
    const mapper = (source: SourceCredibility): SourceChartData => {
      const breakdown = source.breakdown

      // Ưu tiên dùng credibility_score nếu backend đã tính
      let credibility = source.credibility_score

      // Nếu credibility_score null/undefined, fallback dựa trên fake_percentage/fake_ratio
      if ((credibility === null || credibility === undefined) && breakdown) {
        let fakePct: number | null = null

        if (typeof breakdown.fake_percentage === "number") {
          fakePct = breakdown.fake_percentage
        } else if (typeof breakdown.fake_ratio === "number") {
          fakePct = breakdown.fake_ratio * 100
        }

        if (fakePct !== null) {
          // Định nghĩa: credibility ≈ 100 - fake%
          const rawScore = 100 - fakePct
          credibility = Math.max(0, Math.min(100, rawScore))
        }
      }

      return {
        domain: source.domain,
        score: credibility ?? 0,
        posts: breakdown?.total_posts ?? 0,
        fake: breakdown?.fake_posts ?? 0,
        risk: (source.risk_level || "MEDIUM") as keyof typeof riskColors,
        raw: source,
      }
    }

    const warning = warningSources.map(mapper)

    // Chỉ dùng warning sources cho chart (bỏ top-credible)
    return [...warning].sort((a, b) => b.score - a.score)
  }, [warningSources])

  const filteredSources = combinedSources.filter((s) =>
    s.domain.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const pieData = useMemo(() => {
    if (!selectedSource?.breakdown) return []
    const fakePosts = selectedSource.breakdown.fake_posts ?? 0
    const totalPosts = selectedSource.breakdown.total_posts ?? 0
    const realPosts = Math.max(totalPosts - fakePosts, 0)
    
    return [
      {
        name: "Fake",
        value: fakePosts,
        fill: "oklch(0.6 0.2 25)",
      },
      {
        name: "Real",
        value: realPosts,
        fill: "oklch(0.7 0.18 145)",
      },
    ]
  }, [selectedSource])

  // Tính toán chiều cao động dựa trên số lượng sources
  const chartHeight = Math.max(400, filteredSources.length * 40)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Độ tin cậy nguồn tin</h1>
          <p className="text-muted-foreground mt-1">Phân tích và so sánh độ tin cậy của các nguồn tin</p>
        </div>

        {/* Search */}
        <Card className="bg-card">
          <CardContent className="pt-6">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Tìm kiếm domain (ví dụ: reuters.com)"
                  className="pl-10 bg-secondary border-border"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Button variant="outline" onClick={fetchSources} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                Làm mới
              </Button>
              <Button onClick={analyzeSource} disabled={analyzing || !searchQuery.trim()}>
                {analyzing ? "Đang phân tích..." : "Phân tích"}
              </Button>
            </div>
            {error && <p className="text-sm text-warning mt-2">{error}</p>}
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Sources Chart */}
          <div className="lg:col-span-2">
            <Card className="bg-card">
              <CardHeader>
                <CardTitle>Điểm tin cậy</CardTitle>
                <CardDescription>Nhấn vào từng cột để xem chi tiết</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="w-full overflow-auto" style={{ maxHeight: '600px' }}>
                  <ChartContainer
                    config={{
                      score: { label: "Credibility Score", color: "oklch(0.75 0.15 195)" },
                    }}
                    style={{ height: `${chartHeight}px`, minHeight: '400px' }}
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={filteredSources}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="oklch(0.28 0.01 260)"
                          horizontal
                          vertical={false}
                        />
                        <XAxis 
                          type="number" 
                          domain={[0, 100]}
                          stroke="oklch(0.65 0 0)" 
                          fontSize={12}
                          tickFormatter={(value) => `${value}`}
                        />
                        <YAxis 
                          type="category" 
                          dataKey="domain" 
                          stroke="oklch(0.65 0 0)" 
                          fontSize={11} 
                          width={130}
                          tick={{ fill: "oklch(0.65 0 0)" }}
                        />
                        <ChartTooltip 
                          content={<ChartTooltipContent />}
                          formatter={(value: number) => [`${value.toFixed(1)}`, "Score"]}
                        />
                        <Bar
                          dataKey="score"
                          radius={[0, 4, 4, 0]}
                          cursor="pointer"
                          onClick={(data) => setSelectedSource((data as SourceChartData).raw)}
                          minPointSize={5}
                        >
                          {filteredSources.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={riskColors[entry.risk]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </div>

                {!filteredSources.length && !loading && (
                  <p className="text-center text-sm text-muted-foreground mt-4">
                    Không tìm thấy nguồn phù hợp.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Selected Source Details */}
          <div className="space-y-6">
            {selectedSource ? (
              <>
                <Card className="bg-card">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{selectedSource.domain}</CardTitle>
                      {(() => {
                        const fallbackLevel = "MEDIUM" as const
                        const level =
                          (selectedSource.risk_level as keyof typeof riskBadgeStyles) || fallbackLevel
                        return (
                          <Badge
                            variant="outline"
                            className={cn(
                              "border",
                              riskBadgeStyles[level] ?? riskBadgeStyles[fallbackLevel],
                            )}
                          >
                            {selectedSource.risk_level || fallbackLevel}
                          </Badge>
                        )
                      })()}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="text-center">
                      <div className="text-5xl font-bold text-primary">
                        {(selectedSource.credibility_score ?? 0).toFixed(1)}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">Điểm tin cậy</div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                      <div className="text-center">
                        <div className="text-2xl font-semibold">
                          {selectedSource.breakdown?.total_posts ?? 0}
                        </div>
                        <div className="text-xs text-muted-foreground">Tổng số bài</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-semibold text-danger">
                          {selectedSource.breakdown?.fake_posts ?? 0}
                        </div>
                        <div className="text-xs text-muted-foreground">Bài bị đánh giá giả</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card">
                  <CardHeader>
                    <CardTitle className="text-sm">Phân bố nội dung</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer
                      config={{
                        fake: { label: "Fake", color: "oklch(0.6 0.2 25)" },
                        real: { label: "Real", color: "oklch(0.7 0.18 145)" },
                      }}
                      className="h-[200px]"
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={80}
                            paddingAngle={2}
                            dataKey="value"
                          />
                          <ChartTooltip content={<ChartTooltipContent />} />
                        </PieChart>
                      </ResponsiveContainer>
                    </ChartContainer>
                    <div className="flex justify-center gap-6 mt-4">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-success" />
                        <span className="text-sm text-muted-foreground">Real</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-danger" />
                        <span className="text-sm text-muted-foreground">Fake</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-card">
                <CardContent className="pt-6">
                  <div className="text-center text-muted-foreground py-12">
                    <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Select a source from the chart to see details</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}