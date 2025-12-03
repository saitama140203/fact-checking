"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { StatsCard } from "@/components/stats-card"
import { RiskGauge } from "@/components/risk-gauge"
import { TrendChart } from "@/components/trend-chart"
import { SourceTable } from "@/components/source-table"
import { TopicsCloud } from "@/components/topics-cloud"
import { FileText, AlertTriangle, Shield, Activity, RefreshCw } from "lucide-react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { showError } from "@/lib/toast"

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Dashboard data
  const [stats, setStats] = useState<any>(null)
  const [riskAssessment, setRiskAssessment] = useState<any>(null)
  const [trendData, setTrendData] = useState<any[]>([])
  const [credibleSources, setCredibleSources] = useState<any[]>([])
  const [warningSources, setWarningSources] = useState<any[]>([])
  const [trendingTopics, setTrendingTopics] = useState<any[]>([])

  const fetchDashboardData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch all data in parallel
      const [
        statsData,
        riskData,
        trend,
        credible,
        warnings,
        topics
      ] = await Promise.allSettled([
        api.getStats(),
        api.getRiskAssessment(7),
        api.getFakeNewsTrend(30),
        api.getTopCredibleSources(5, 5),
        api.getWarningSources(5, 3),
        api.getTrendingFakeTopics(7, 10)
      ])

      // Process stats
      if (statsData.status === "fulfilled") {
        setStats(statsData.value)
      }

      // Process risk assessment
      if (riskData.status === "fulfilled") {
        setRiskAssessment(riskData.value)
      }

      // Process trend data
      if (trend.status === "fulfilled") {
        const trendResult = trend.value
        if (trendResult?.daily_data && Array.isArray(trendResult.daily_data)) {
          setTrendData(trendResult.daily_data.map((d: any) => ({
            date: d.date || "",
            fake_count: d.fake || 0,
            real_count: d.real || 0,
            total: d.total || 0,
            fake_percentage: d.fake_percentage || 0
          })))
        }
      }

      // Process credible sources
      if (credible.status === "fulfilled") {
        setCredibleSources(credible.value.sources || [])
      }

      // Process warning sources
      if (warnings.status === "fulfilled") {
        setWarningSources(warnings.value.warning_sources || [])
      }

      // Process trending topics
      if (topics.status === "fulfilled") {
        setTrendingTopics(topics.value.trending_topics || [])
      }

    } catch (err) {
      console.error("Error fetching dashboard data:", err)
      const errorMessage = "Không thể tải dữ liệu. Vui lòng kiểm tra kết nối backend."
      setError(errorMessage)
      showError(err, errorMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  // Calculate stats for display
  const totalPosts = stats?.database?.total_posts || 0
  const fakeNews = stats?.predictions?.fake_news || 0
  const realNews = stats?.predictions?.real_news || 0
  const fakePercentage = stats?.predictions?.fake_percentage || 0
  const predictionCoverage = stats?.database?.prediction_coverage || 0

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Tổng Quan Dashboard</h1>
            <p className="text-muted-foreground mt-1">Phát hiện tin giả thời gian thực từ Reddit</p>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={fetchDashboardData}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Làm mới
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <p className="text-sm text-yellow-500">{error}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Đang hiển thị dữ liệu mẫu. Đảm bảo backend đang chạy tại http://localhost:8000
            </p>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard 
            title="Tổng Bài Đã Phân Tích" 
            value={totalPosts.toLocaleString()} 
            description="Trong database" 
            icon={FileText} 
          />
          <StatsCard
            title="Tin Giả Phát Hiện"
            value={fakeNews.toLocaleString()}
            description={`${fakePercentage.toFixed(1)}% tổng số`}
            icon={AlertTriangle}
            variant="warning"
          />
          <StatsCard 
            title="Tin Thật" 
            value={realNews.toLocaleString()} 
            description="Đã xác minh" 
            icon={Shield} 
          />
          <StatsCard
            title="Độ Phủ Phân Tích"
            value={`${predictionCoverage.toFixed(1)}%`}
            description="Đã có prediction"
            icon={Activity}
            variant="success"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Risk Gauge */}
          <div className="lg:col-span-1">
            <RiskGauge 
              score={riskAssessment?.risk_score || 0} 
              level={riskAssessment?.risk_level || "LOW"} 
              title="Mức Độ Rủi Ro Hiện Tại" 
            />
          </div>

          {/* Trend Chart */}
          <div className="lg:col-span-2">
            <TrendChart
              data={trendData.length > 0 ? trendData : [
                { date: "N/A", fake_count: 0, real_count: 0, total: 0, fake_percentage: 0 }
              ]}
              title="Xu Hướng Tin Giả"
              description="Phân bố tin giả vs tin thật theo ngày trong 30 ngày qua"
            />
          </div>
        </div>

        {/* Sources Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          <SourceTable
            sources={credibleSources.length > 0 ? credibleSources : []}
            title="Nguồn Tin Đáng Tin Cậy"
            description="Các nguồn có tỷ lệ tin thật cao nhất"
            type="credible"
          />
          <SourceTable
            sources={warningSources.length > 0 ? warningSources : []}
            title="Danh Sách Cảnh Báo"
            description="Các nguồn có nhiều tin giả - cần kiểm chứng kỹ"
            type="warning"
          />
        </div>

        {/* Trending Topics */}
        <TopicsCloud
          topics={trendingTopics.length > 0 ? trendingTopics : []}
          title="Chủ Đề Tin Giả Hot"
          description="Các chủ đề đang có nhiều thông tin sai lệch trong tuần này"
        />
      </div>
    </DashboardLayout>
  )
}
