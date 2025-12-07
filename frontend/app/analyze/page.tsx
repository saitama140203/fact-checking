"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, AlertTriangle, CheckCircle, Link2, FileText, Loader2, ExternalLink, User, MessageSquare, ThumbsUp, Brain, Sparkles, Info, Shield, TrendingUp, Clock, ArrowRight, ShieldCheck, ShieldAlert } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { api, UserAnalysisResult, RedditAnalysisResult, RiskIndicator, DeepSeekAnalysisData } from "@/lib/api"
import { showError, showSuccess } from "@/lib/toast"

type AnalysisResult = (UserAnalysisResult | RedditAnalysisResult) & {
  post_info?: RedditAnalysisResult["post_info"]
}

// Animated gradient background component
const AnimatedGradient = ({ isFake }: { isFake: boolean }) => (
  <div className={cn(
    "absolute inset-0 opacity-20 rounded-lg transition-all duration-500",
    isFake 
      ? "bg-gradient-to-br from-red-500/30 via-orange-500/20 to-transparent" 
      : "bg-gradient-to-br from-green-500/30 via-emerald-500/20 to-transparent"
  )} />
)

export default function AnalyzePage() {
  const [postUrl, setPostUrl] = useState("")
  const [postTitle, setPostTitle] = useState("")
  const [postContent, setPostContent] = useState("")
  const [sourceUrl, setSourceUrl] = useState("")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("url")

  const handleAnalyzeUrl = async () => {
    if (!postUrl.trim()) {
      const errorMsg = "Vui lòng nhập URL Reddit"
      setError(errorMsg)
      showError(new Error(errorMsg))
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const data = await api.analyzeRedditUrl(postUrl)
      setResult(data)
      showSuccess(
        "Phân tích hoàn tất",
        `Kết quả: ${data.prediction.label === "FAKE" ? "Tin giả" : "Tin thật"}`
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Có lỗi xảy ra khi phân tích"
      setError(errorMsg)
      showError(err, errorMsg)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleAnalyzeText = async () => {
    if (!postTitle.trim() || postTitle.length < 10) {
      const errorMsg = "Tiêu đề phải có ít nhất 10 ký tự"
      setError(errorMsg)
      showError(new Error(errorMsg))
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const data = await api.analyzeText(
        postTitle,
        postContent || undefined,
        sourceUrl || undefined
      )
      setResult(data)
      showSuccess(
        "Phân tích hoàn tất",
        `Kết quả: ${data.prediction.label === "FAKE" ? "Tin giả" : "Tin thật"}`
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Có lỗi xảy ra khi phân tích"
      setError(errorMsg)
      showError(err, errorMsg)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleAnalyze = () => {
    if (activeTab === "url") {
      handleAnalyzeUrl()
    } else {
      handleAnalyzeText()
    }
  }

  const clearResult = () => {
    setResult(null)
    setError(null)
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Phân tích bài viết</h1>
          <p className="text-muted-foreground mt-1">
            Kiểm tra một bài viết có khả năng là tin giả hay tin thật. Phân tích chi tiết dùng HuggingFace + DeepSeek.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Input Section */}
          <Card className="bg-card">
            <CardHeader>
              <CardTitle>Gửi bài viết để phân tích</CardTitle>
              <CardDescription>Nhập URL Reddit hoặc dán nội dung bài viết</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs 
                defaultValue="url" 
                className="space-y-4"
                onValueChange={(value) => {
                  setActiveTab(value)
                  clearResult()
                }}
              >
                <TabsList className="bg-secondary">
                  <TabsTrigger value="url" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <Link2 className="h-4 w-4 mr-2" /> URL Reddit
                  </TabsTrigger>
                  <TabsTrigger value="content" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <FileText className="h-4 w-4 mr-2" /> Nhập nội dung
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="url" className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">URL bài viết Reddit</label>
                    <div className="relative">
                      <Link2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="https://reddit.com/r/news/comments/..."
                        className="pl-10 bg-secondary border-border"
                        value={postUrl}
                        onChange={(e) => setPostUrl(e.target.value)}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">Hỗ trợ: reddit.com, old.reddit.com, redd.it</p>
                  </div>
                </TabsContent>

                <TabsContent value="content" className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Tiêu đề bài viết *</label>
                    <Input 
                      placeholder="Nhập tiêu đề bài viết (tối thiểu 10 ký tự)" 
                      className="bg-secondary border-border"
                      value={postTitle}
                      onChange={(e) => setPostTitle(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Nội dung (không bắt buộc)</label>
                    <Textarea
                      placeholder="Paste article content here..."
                      className="min-h-[120px] bg-secondary border-border"
                      value={postContent}
                      onChange={(e) => setPostContent(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">URL nguồn (không bắt buộc)</label>
                    <Input 
                      placeholder="https://example.com/article" 
                      className="bg-secondary border-border"
                      value={sourceUrl}
                      onChange={(e) => setSourceUrl(e.target.value)}
                    />
                  </div>
                </TabsContent>

                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-sm text-red-500">{error}</p>
                  </div>
                )}

                <Button className="w-full" onClick={handleAnalyze} disabled={isAnalyzing}>
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Đang Phân Tích...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" /> Phân tích bài viết
                    </>
                  )}
                </Button>
              </Tabs>
            </CardContent>
          </Card>

          {/* Results Section */}
          {result ? (
            <Card className="bg-card relative overflow-hidden">
              <AnimatedGradient isFake={result.prediction.is_fake} />
              <CardHeader className="relative z-10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "p-3 rounded-xl",
                      result.prediction.is_fake 
                        ? "bg-red-500/20 ring-2 ring-red-500/30" 
                        : "bg-green-500/20 ring-2 ring-green-500/30"
                    )}>
                      {result.prediction.is_fake ? (
                        <ShieldAlert className="h-6 w-6 text-red-500" />
                      ) : (
                        <ShieldCheck className="h-6 w-6 text-green-500" />
                      )}
                    </div>
                    <div>
                      <CardTitle className="text-xl">Kết quả phân tích</CardTitle>
                      <p className="text-sm text-muted-foreground mt-0.5">Phân tích tin giả sử dụng AI</p>
                    </div>
                  </div>
                  <Badge
                    className={cn(
                      "text-sm px-4 py-2 font-semibold shadow-lg",
                      result.prediction.is_fake
                        ? "bg-gradient-to-r from-red-500 to-orange-500 text-white border-0"
                        : "bg-gradient-to-r from-green-500 to-emerald-500 text-white border-0",
                    )}
                  >
                    {result.prediction.is_fake ? (
                      <AlertTriangle className="h-4 w-4 mr-2" />
                    ) : (
                      <CheckCircle className="h-4 w-4 mr-2" />
                    )}
                    {result.prediction.label === "FAKE" ? "TIN GIẢ" : "TIN THẬT"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6 relative z-10">
                {result.enhanced ? (
                  <Tabs defaultValue="summary" className="w-full">
                    <TabsList className="grid w-full grid-cols-3 bg-secondary/50 p-1">
                      <TabsTrigger value="summary">
                        <TrendingUp className="h-4 w-4 mr-2" /> Tổng quan
                      </TabsTrigger>
                      <TabsTrigger value="models">
                        <Brain className="h-4 w-4 mr-2" /> Chi tiết AI
                      </TabsTrigger>
                      <TabsTrigger value="analysis">
                        <Info className="h-4 w-4 mr-2" /> Phân tích
                      </TabsTrigger>
                    </TabsList>

                    {/* Summary Tab */}
                    <TabsContent value="summary" className="space-y-5 pt-2">
                      <div className={cn(
                        "p-6 rounded-xl text-center relative overflow-hidden",
                        result.prediction.is_fake 
                          ? "bg-gradient-to-br from-red-500/10 to-orange-500/5 border border-red-500/20"
                          : "bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/20"
                      )}>
                        <div className="relative z-10">
                          <div className={cn(
                            "text-5xl font-bold",
                            result.prediction.is_fake ? "text-red-500" : "text-green-500"
                          )}>
                            {result.prediction.confidence_percentage.toFixed(1)}%
                          </div>
                          <div className="text-sm text-muted-foreground mt-2 font-medium">Độ tin cậy tổng hợp</div>
                          <div className="mt-4 h-3 bg-secondary/50 rounded-full overflow-hidden max-w-xs mx-auto">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all duration-1000 ease-out",
                                result.prediction.is_fake 
                                  ? "bg-gradient-to-r from-red-500 to-orange-500" 
                                  : "bg-gradient-to-r from-green-500 to-emerald-500",
                              )}
                              style={{ width: `${result.prediction.confidence_percentage}%` }}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-gradient-to-br from-blue-500/10 to-cyan-500/5 rounded-xl border border-blue-500/20 hover:border-blue-500/40 transition-colors">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="p-2 bg-blue-500/20 rounded-lg">
                              <Brain className="h-4 w-4 text-blue-400" />
                            </div>
                            <div>
                              <span className="text-xs font-semibold text-blue-400">HuggingFace</span>
                              <span className="text-xs text-muted-foreground block">Mô hình ML</span>
                            </div>
                          </div>
                          <div className={cn(
                            "text-2xl font-bold",
                            result.enhanced.hf?.label === "FAKE" ? "text-red-400" : "text-green-400"
                          )}>
                            {result.enhanced.hf?.label || "N/A"}
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {((result.enhanced.hf?.confidence || 0) * 100).toFixed(1)}% độ tin cậy
                          </div>
                        </div>
                        <div className="p-4 bg-gradient-to-br from-purple-500/10 to-pink-500/5 rounded-xl border border-purple-500/20 hover:border-purple-500/40 transition-colors">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="p-2 bg-purple-500/20 rounded-lg">
                              <Sparkles className="h-4 w-4 text-purple-400" />
                            </div>
                            <div>
                              <span className="text-xs font-semibold text-purple-400">DeepSeek AI</span>
                              <span className="text-xs text-muted-foreground block">LLM Analysis</span>
                            </div>
                          </div>
                          <div className={cn(
                            "text-2xl font-bold capitalize",
                            result.enhanced.gemini_classifier?.label === "fake" ? "text-red-400" : "text-green-400"
                          )}>
                            {result.enhanced.gemini_classifier?.label?.toUpperCase() || "N/A"}
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {((result.enhanced.gemini_classifier?.confidence || 0) * 100).toFixed(1)}% confidence
                          </div>
                        </div>
                      </div>
                    </TabsContent>

                    {/* Analysis Tab - ĐÃ SỬA LOGIC HIỂN THỊ */}
                    <TabsContent value="analysis" className="space-y-4 pt-2">
                      {result.enhanced?.analysis ? (
                        <div className={cn(
                          "p-5 rounded-xl border",
                          result.prediction.is_fake 
                            ? "bg-gradient-to-br from-amber-500/5 to-orange-500/5 border-amber-500/20" 
                            : "bg-gradient-to-br from-blue-500/5 to-cyan-500/5 border-blue-500/20"
                        )}>
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className={cn(
                                "p-2.5 rounded-xl",
                                result.prediction.is_fake ? "bg-amber-500/20" : "bg-blue-500/20"
                              )}>
                                <Shield className={cn(
                                  "h-5 w-5",
                                  result.prediction.is_fake ? "text-amber-400" : "text-blue-400"
                                )} />
                              </div>
                              <div>
                                <span className={cn(
                                  "font-semibold",
                                  result.prediction.is_fake ? "text-amber-400" : "text-blue-400"
                                )}>
                                  Phân tích chi tiết
                                </span>
                                <p className="text-xs text-muted-foreground">Powered by DeepSeek</p>
                              </div>
                            </div>
                            <Badge variant="outline" className="bg-secondary/50 border-border">
                              <Clock className="h-3 w-3 mr-1" />
                              v{result.enhanced.workflow_version}
                            </Badge>
                          </div>
                          
                          {typeof result.enhanced.analysis === 'object' ? (
                            <div className="space-y-5">
                              {/* Summary */}
                              <div className="p-3 bg-secondary/30 rounded-lg">
                                <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
                                  <Sparkles className="h-3 w-3 text-purple-400" /> Tóm tắt
                                </h4>
                                <p className="text-sm text-muted-foreground italic">
                                  "{(result.enhanced.analysis as DeepSeekAnalysisData).summary}"
                                </p>
                              </div>

                              {/* Key Issues */}
                              {(result.enhanced.analysis as DeepSeekAnalysisData).key_issues?.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-semibold mb-2 flex items-center gap-2 text-red-400">
                                    <ShieldAlert className="h-4 w-4" /> Vấn đề chính cần lưu ý
                                  </h4>
                                  <ul className="space-y-2">
                                    {(result.enhanced.analysis as DeepSeekAnalysisData).key_issues.map((issue: string, idx: number) => (
                                      <li key={idx} className="text-sm flex items-start gap-2 bg-red-500/5 p-2 rounded border border-red-500/10">
                                        <span className="text-red-400 mt-0.5">•</span>
                                        <span className="text-foreground/90">{issue}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {/* Deep Dive Analysis */}
                              <div>
                                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2 text-blue-400">
                                  <FileText className="h-4 w-4" /> Chi tiết phân tích
                                </h4>
                                <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line">
                                  {(result.enhanced.analysis as DeepSeekAnalysisData).analysis}
                                </p>
                              </div>

                              {/* Recommendation */}
                              {(result.enhanced.analysis as DeepSeekAnalysisData).recommendation && (
                                <div className={cn(
                                  "mt-4 p-3 rounded-lg border flex items-start gap-3",
                                  result.prediction.is_fake ? "bg-red-500/10 border-red-500/20" : "bg-green-500/10 border-green-500/20"
                                )}>
                                  <CheckCircle className={cn(
                                    "h-5 w-5 shrink-0",
                                    result.prediction.is_fake ? "text-red-400" : "text-green-400"
                                  )} />
                                  <div>
                                    <span className="text-sm font-semibold block mb-1">Khuyến nghị hành động</span>
                                    <p className="text-sm text-muted-foreground">{(result.enhanced.analysis as DeepSeekAnalysisData).recommendation}</p>
                                  </div>
                                </div>
                              )}
                            </div>
                          ) : (
                            // Fallback cho String
                            <div 
                              className="prose prose-sm max-w-none text-sm leading-relaxed p-4 bg-secondary/30 rounded-lg"
                              dangerouslySetInnerHTML={{
                                __html: (result.enhanced.analysis as string)
                                  .replace(/\n/g, "<br />")
                                  .replace(/\*\*(.*?)\*\*/g, "<strong class='text-primary'>$1</strong>")
                              }}
                            />
                          )}
                        </div>
                      ) : (
                        <div className="p-8 border border-dashed rounded-xl text-center text-muted-foreground bg-secondary/20">
                          <Info className="h-8 w-8 mx-auto mb-3 opacity-50" />
                          <p className="font-medium">Không có phân tích chi tiết</p>
                          <p className="text-xs mt-1">AI chưa tạo phân tích cho bài viết này</p>
                        </div>
                      )}
                    </TabsContent>

                    {/* Models Tab */}
                    <TabsContent value="models" className="space-y-4 pt-2">
                      {result.enhanced.hf && (
                        <div className="p-5 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 rounded-xl border border-blue-500/20">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className="p-2.5 bg-blue-500/20 rounded-xl">
                                <Brain className="h-5 w-5 text-blue-400" />
                              </div>
                              <div>
                                <span className="font-semibold text-blue-400">Mô hình HuggingFace</span>
                                <p className="text-xs text-muted-foreground">Phân loại bằng Deep Learning</p>
                              </div>
                            </div>
                            <Badge variant="outline" className="bg-blue-500/10 border-blue-500/30 text-blue-400">
                              {result.enhanced.hf.method === "local" ? "🖥️ Local" : "☁️ API"}
                            </Badge>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div className="p-3 bg-secondary/30 rounded-lg text-center">
                              <div className={cn(
                                "text-xl font-bold",
                                result.enhanced.hf.label === "FAKE" ? "text-red-400" : "text-green-400"
                              )}>
                                {result.enhanced.hf.label}
                              </div>
                              <div className="text-xs text-muted-foreground">Dự đoán</div>
                            </div>
                            <div className="p-3 bg-secondary/30 rounded-lg text-center">
                              <div className="text-xl font-bold text-blue-400">
                                {(result.enhanced.hf.confidence * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-muted-foreground">Độ tin cậy</div>
                            </div>
                          </div>
                        </div>
                      )}
                    </TabsContent>
                  </Tabs>
                ) : (
                  // Legacy view
                  <div className="p-4">
                    <p className="text-center text-muted-foreground">Không có dữ liệu nâng cao.</p>
                  </div>
                )}

                {/* Post Info */}
                {result.post_info && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4 text-orange-400" />
                      <span className="text-sm font-medium">Thông Tin Bài Viết Reddit</span>
                    </div>
                    <div className="p-4 bg-gradient-to-br from-orange-500/5 to-red-500/5 rounded-xl border border-orange-500/20 space-y-3">
                      <p className="font-medium leading-relaxed">{result.post_info.title}</p>
                      {result.post_info.selftext && (
                        <p className="text-sm text-muted-foreground line-clamp-3 italic">
                          &ldquo;{result.post_info.selftext}&rdquo;
                        </p>
                      )}
                      <div className="flex flex-wrap gap-2 pt-2">
                        <Badge variant="outline" className="bg-secondary/30 border-orange-500/20">
                          <User className="h-3 w-3 mr-1 text-orange-400" /> u/{result.post_info.author}
                        </Badge>
                        <Badge variant="outline" className="bg-secondary/30 border-blue-500/20">
                          r/{result.post_info.subreddit}
                        </Badge>
                        <Badge variant="outline" className="bg-secondary/30 border-green-500/20">
                          <ThumbsUp className="h-3 w-3 mr-1 text-green-400" /> {result.post_info.score}
                        </Badge>
                      </div>
                      <div className="pt-2 border-t border-orange-500/10">
                        <a href={result.post_info.permalink} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 px-3 py-1.5 bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 rounded-lg text-xs font-medium transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" /> Xem trên Reddit <ArrowRight className="h-3 w-3" />
                        </a>
                      </div>
                    </div>
                  </div>
                )}

                <Button variant="outline" className="w-full py-6 text-base font-medium" onClick={clearResult}>
                  <Search className="h-4 w-4 mr-2" /> Analyse another article <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-gradient-to-br from-card to-secondary/20 border-dashed">
              <CardContent className="pt-6">
                <div className="text-center text-muted-foreground py-12">
                  <div className="relative inline-block mb-6">
                    <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
                    <div className="relative p-6 bg-secondary/50 rounded-full">
                      <Shield className="h-12 w-12 opacity-50" />
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">Chưa có phân tích nào</h3>
                  <p className="text-sm max-w-xs mx-auto">Nhập URL Reddit hoặc nội dung bài viết bên trái để kiểm tra tin giả với AI</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
