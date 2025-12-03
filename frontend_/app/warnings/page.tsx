"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AlertTriangle, ExternalLink, Shield, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { useEffect, useMemo, useState } from "react"
import { api, SourceCredibility } from "@/lib/api"
import { showError } from "@/lib/toast"

const riskBadgeStyles = {
  VERY_HIGH: "bg-danger/20 text-danger border-danger/30",
  HIGH: "bg-chart-4/20 text-chart-4 border-chart-4/30",
  MEDIUM: "bg-warning/20 text-warning border-warning/30",
  LOW: "bg-success/20 text-success border-success/30",
}

const getFakePercentage = (source: SourceCredibility) => {
  if (typeof source.breakdown?.fake_percentage === "number") {
    return source.breakdown.fake_percentage
  }
  const fake = source.breakdown?.fake_posts ?? 0
  const total = source.breakdown?.total_posts ?? 0
  if (total === 0) return 0
  return (fake / total) * 100
}

export default function WarningsPage() {
  const [sources, setSources] = useState<SourceCredibility[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    async function loadWarningSources() {
      setLoading(true)
      setError(null)
      try {
        const response = await api.getWarningSources(25, 3)
        if (!mounted) return
        setSources(response.warning_sources || [])
      } catch (err) {
        console.error("Failed to load warning sources", err)
        if (mounted) {
          const errorMessage = "Không thể tải danh sách cảnh báo. Vui lòng đảm bảo backend đang chạy."
          setError(errorMessage)
          showError(err, errorMessage)
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadWarningSources()
    return () => {
      mounted = false
    }
  }, [])

  const stats = useMemo(() => {
    if (!sources.length) {
      return {
        total: 0,
        avgFakeRate: 0,
        highRiskCount: 0,
      }
    }

    const avg =
      sources.reduce((sum, src) => sum + getFakePercentage(src), 0) / (sources.length || 1)

    const highRiskCount = sources.filter((src) => {
      const percentage = getFakePercentage(src)
      return (src.risk_level === "VERY_HIGH" || src.risk_level === "HIGH") && percentage >= 60
    }).length

    return {
      total: sources.length,
      avgFakeRate: avg,
      highRiskCount,
    }
  }, [sources])

  const sortedSources = useMemo(() => {
    if (!sources || !Array.isArray(sources)) return []
    return [...sources].sort((a, b) => getFakePercentage(b) - getFakePercentage(a))
  }, [sources])

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-danger/20 rounded-lg">
              <AlertTriangle className="h-6 w-6 text-danger" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Danh sách cảnh báo</h1>
              <p className="text-muted-foreground mt-1">
                Các nguồn có tỷ lệ tin giả cao – hãy kiểm chứng nội dung thật kỹ trước khi tin.
              </p>
            </div>
          </div>
        </div>

        {/* Alert Banner */}
        <Card className="bg-danger/10 border-danger/20">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <AlertTriangle className="h-6 w-6 text-danger shrink-0" />
              <div>
                <p className="font-medium text-danger">Lưu ý quan trọng</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Danh sách này được sinh ra bởi hệ thống phân tích AI, chỉ nên dùng như tài liệu tham khảo.
                  Luôn kiểm chứng thông tin qua nhiều nguồn uy tín trước khi đưa ra kết luận.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg text-sm text-warning">
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="bg-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Tổng số nguồn bị cảnh báo</p>
                  <p className="text-2xl font-bold mt-1 text-danger">
                    {loading ? "..." : stats.total}
                  </p>
                </div>
                <Shield className="h-8 w-8 text-danger" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Tỷ lệ tin giả trung bình</p>
                  <p className="text-2xl font-bold mt-1">
                    {loading ? "..." : `${stats.avgFakeRate.toFixed(1)}%`}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Nguồn rủi ro cao (&gt;= 60% tin giả)</p>
                  <p className="text-2xl font-bold mt-1 text-warning">
                    {loading ? "..." : stats.highRiskCount}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-warning" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Warning Sources Table */}
        <Card className="bg-card">
            <CardHeader>
              <CardTitle>Nguồn bị gắn cờ</CardTitle>
              <CardDescription>Các nguồn được sắp xếp theo tỷ lệ tin giả (cao xuống thấp)</CardDescription>
            </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-12 text-center text-muted-foreground text-sm">Đang tải dữ liệu...</div>
            ) : sortedSources.length ? (
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-muted-foreground">Tên miền</TableHead>
                    <TableHead className="text-muted-foreground text-right">% tin giả</TableHead>
                    <TableHead className="text-muted-foreground text-right">Tổng số bài</TableHead>
                    <TableHead className="text-muted-foreground">Mức rủi ro</TableHead>
                    <TableHead className="text-muted-foreground">Khuyến nghị</TableHead>
                    <TableHead className="text-muted-foreground text-right">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedSources.map((source) => {
                    const fakePercentage = getFakePercentage(source)
                    const riskLevel = (source.risk_level || "HIGH") as keyof typeof riskBadgeStyles
                    const isTrending =
                      riskLevel === "VERY_HIGH" || fakePercentage >= 80
                    return (
                      <TableRow key={source.domain} className="border-border">
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{source.domain}</span>
                            {isTrending && (
                              <Badge
                                variant="outline"
                                className="bg-warning/20 text-warning border-warning/30 text-xs"
                              >
                                <TrendingUp className="h-3 w-3 mr-1" />
                                Đang tăng
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className="font-bold text-danger">{fakePercentage.toFixed(1)}%</span>
                        </TableCell>
                        <TableCell className="text-right">
                          {source.breakdown?.total_posts ?? 0}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn("border", riskBadgeStyles[riskLevel])}>
                            {riskLevel.replace("_", " ")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-[250px]">
                          {source.recommendation || "Cẩn thận khi chia sẻ nội dung từ nguồn này."}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(`https://${source.domain}`, "_blank")}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            ) : (
              <div className="py-12 text-center text-muted-foreground text-sm">
                Không có nguồn nào trong danh sách cảnh báo.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
