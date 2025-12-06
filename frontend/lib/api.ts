/**
 * API Client for Fake News Detector Backend
 * Production-ready với retry logic, timeout, error handling
 * Connects to FastAPI backend endpoints
 */

// Base URL - Được config từ environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://puu14-fake-news-backend.hf.space"

// ========================
// CONFIGURATION
// ========================

interface ApiConfig {
  timeout: number
  retryAttempts: number
  retryDelay: number
  retryableStatusCodes: number[]
}

const API_CONFIG: ApiConfig = {
  timeout: 30000, // 30 seconds
  retryAttempts: 3,
  retryDelay: 1000, // 1 second base delay
  // Danh sách status code có thể retry được (4xx/5xx tạm thời)
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
}

// ========================
// ERROR TYPES
// ========================

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public endpoint?: string,
    public originalError?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export class NetworkError extends Error {
  constructor(message: string, public originalError?: unknown) {
    super(message)
    this.name = "NetworkError"
  }
}

export class TimeoutError extends Error {
  constructor(message: string = "Request timeout") {
    super(message)
    this.name = "TimeoutError"
  }
}

// ========================
// TYPE DEFINITIONS
// ========================

export interface SourceCredibility {
  domain: string
  credibility_score: number | null
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH"
  risk_color?: string
  breakdown: {
    total_posts: number
    fake_posts: number
    real_posts: number
    fake_ratio: number  // Ratio 0-1
    fake_percentage: number  // Percentage 0-100
    avg_fake_confidence: number
    fake_avg_score: number
    real_avg_score: number
  }
  recommendation: string
  message?: string
}

export interface TrendData {
  period: {
    start: string
    end: string
    days: number
  }
  trend: {
    direction: "INCREASING" | "DECREASING" | "STABLE"
    emoji: string
    change_percentage: number
    interpretation: string
  }
  current_period: {
    total_posts: number
    fake_posts: number
    real_posts: number
    fake_percentage: number
    daily_avg_fake: number
  }
  previous_period: {
    total_posts: number
    fake_posts: number
    fake_percentage: number
  }
  peak_day: {
    date: string
    fake: number
    real: number
    total: number
    fake_percentage: number
  } | null
  daily_data: Array<{
    date: string
    fake: number
    real: number
    total: number
    fake_percentage: number
  }>
  subreddit: string | null
}

export interface TrendingTopic {
  keyword: string
  frequency: number
  trending_score?: number  // Optional - not always present
  sample_titles: string[]
}

export interface RiskAssessment {
  risk_score: number
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  color: string
  period_days: number
  subreddit: string
  contributing_factors: Array<{
    factor: string
    value: string
    impact: "LOW" | "MEDIUM" | "HIGH"
  }>
  recommendation: string
  evaluated_at: string
}

export interface RiskIndicator {
  type: string
  description: string
  severity: "LOW" | "MEDIUM" | "HIGH"
}

export interface UserAnalysisResult {
  prediction: {
    label: "FAKE" | "REAL" | "UNCERTAIN"
    confidence: number
    confidence_percentage: number
    model: string
    is_fake: boolean
  }
  risk_indicators: RiskIndicator[]
  recommendation: string
  analyzed_at: string
  // Enhanced prediction results (Workflow 2.0)
  enhanced?: {
    workflow_version: string
    hf: {
      label: "FAKE" | "REAL"
      confidence: number
      scores: {
        fake: number
        real: number
      }
      predicted_at: string
      model: string
      method: "local" | "api"
    }
    gemini_classifier: {
      label: "fake" | "real" | "uncertain"
      confidence: number
      reason: string
      model: string
      classified_at: string
    }
    analysis: string  // Giải thích và cảnh báo từ Gemini (tiếng Việt)
  }
}

// Enhanced Prediction Result (Workflow 2.0)
export interface EnhancedPredictionResult {
  post_id: string
  status: "success" | "already_predicted"
  title: string
  prediction: {
    label: "FAKE" | "REAL" | "UNCERTAIN"
    confidence: number
    hf?: {
      label: "FAKE" | "REAL"
      confidence: number
      scores: {
        fake: number
        real: number
      }
      predicted_at: string
      model: string
      method: "local" | "api"
    }
    gemini_classifier?: {
      label: "fake" | "real" | "uncertain"
      confidence: number
      reason: string
      model: string
      classified_at: string
    }
    analysis?: string  // Giải thích và cảnh báo từ Gemini (tiếng Việt)
    analyzed_at: string
    workflow_version?: string
  }
  full_result?: {
    hf: any
    gemini_classifier: any
    analysis: string
    analyzed_at: string
    workflow_version: string
  }
}

export interface RedditAnalysisResult extends UserAnalysisResult {
  post_info: {
    post_id: string
    title: string
    selftext: string
    author: string
    subreddit: string
    score: number
    upvote_ratio: number
    num_comments: number
    url: string
    domain: string
    created_utc: string
    permalink: string
  }
  // Enhanced prediction results (Workflow 2.0) - inherited from UserAnalysisResult
}

export interface QuickAnalysisResult {
  is_fake: boolean
  label: "FAKE" | "REAL"
  confidence: number
  confidence_percentage: number
  warning: string | null
  analyzed_at: string
}

export interface ComprehensiveReport {
  report_period: {
    start: string
    end: string
    days: number
  }
  summary: {
    total_analyzed: number
    fake_news_count: number
    real_news_count: number
    fake_percentage: number
  }
  fake_news_stats: {
    count: number
    avg_confidence: number
    avg_score: number
    avg_comments: number
  }
  real_news_stats: {
    count: number
    avg_confidence: number
    avg_score: number
    avg_comments: number
  }
  trend_analysis: {
    direction: string
    change_percentage: number
    interpretation: string
  }
  top_credible_sources: SourceCredibility[]
  warning_sources: SourceCredibility[]
  trending_fake_topics: TrendingTopic[]
  recommendations: string[]
  generated_at: string
}

export interface HealthStatus {
  status: "healthy" | "unhealthy"
  timestamp: string
  environment: string
  components: {
    database: {
      status: string
      healthy: boolean
      total_posts: number
    }
    scheduler: {
      status: string
      healthy: boolean
      next_run: string | null
    }
  }
}

export interface SystemStats {
  database: {
    total_posts: number
    posts_with_prediction: number
    posts_without_prediction: number
    prediction_coverage: number
  }
  predictions: {
    fake_news: number
    real_news: number
    fake_percentage: number
  }
  crawler: {
    subreddits: string[]
    crawl_interval_minutes: number
    status: any
  }
}

// ========================
// UTILITY FUNCTIONS
// ========================

/**
 * Sleep utility cho retry delay
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Exponential backoff delay
 */
function getRetryDelay(attempt: number): number {
  return API_CONFIG.retryDelay * Math.pow(2, attempt)
}

/**
 * Kiểm tra xem error có thể retry được không
 */
function isRetryableError(statusCode?: number, error?: unknown): boolean {
  if (statusCode && API_CONFIG.retryableStatusCodes.includes(statusCode)) {
    return true
  }
  // Network errors cũng có thể retry
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return true
  }
  return false
}

/**
 * Tạo AbortSignal với timeout
 * Sử dụng AbortSignal.timeout() nếu có, fallback về manual timeout
 */
function createTimeoutSignal(timeoutMs: number): AbortSignal {
  // Sử dụng native AbortSignal.timeout() nếu có (Node.js 17.3+ / modern browsers)
  // TypeScript type checking: kiểm tra runtime
  if (
    typeof AbortSignal !== "undefined" &&
    typeof (AbortSignal as any).timeout === "function"
  ) {
    return (AbortSignal as any).timeout(timeoutMs)
  }
  
  // Fallback cho older environments
  const controller = new AbortController()
  setTimeout(() => controller.abort(), timeoutMs)
  // Note: timeout sẽ tự clear khi request hoàn thành hoặc abort
  return controller.signal
}

// ========================
// API CLIENT CLASS
// ========================

class ApiClient {
  private baseUrl: string
  private healthCheckCache: { status: boolean; timestamp: number } | null = null
  private readonly HEALTH_CHECK_CACHE_TTL = 60000 // 1 minute

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "") // Remove trailing slash
  }

  /**
   * Kiểm tra health của backend API
   */
  async checkHealth(): Promise<boolean> {
    // Sử dụng cache để tránh quá nhiều health checks
    if (
      this.healthCheckCache &&
      Date.now() - this.healthCheckCache.timestamp < this.HEALTH_CHECK_CACHE_TTL
    ) {
      return this.healthCheckCache.status
    }

    try {
      const healthCheckSignal = createTimeoutSignal(5000) // 5 second timeout cho health check
      const response = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        signal: healthCheckSignal,
      })
      const isHealthy = response.ok
      this.healthCheckCache = {
        status: isHealthy,
        timestamp: Date.now(),
      }
      return isHealthy
    } catch (error) {
      this.healthCheckCache = {
        status: false,
        timestamp: Date.now(),
      }
      return false
    }
  }

  /**
   * Core fetch method với retry logic, timeout, và error handling
   */
  private async fetch<T>(
    endpoint: string,
    options?: RequestInit,
    retryCount = 0
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const timeoutSignal = createTimeoutSignal(API_CONFIG.timeout)
    
    // Merge signals nếu có signal trong options
    let finalSignal = timeoutSignal
    if (options?.signal) {
      const controller = new AbortController()
      const signals = [timeoutSignal, options.signal]
      signals.forEach((signal) => {
        if (signal.aborted) {
          controller.abort()
        } else {
          signal.addEventListener("abort", () => controller.abort())
        }
      })
      finalSignal = controller.signal
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: finalSignal,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...options?.headers,
        },
      })

      // Parse response
      let data: any
      const contentType = response.headers.get("content-type")
      if (contentType?.includes("application/json")) {
        data = await response.json()
      } else {
        const text = await response.text()
        try {
          data = JSON.parse(text)
        } catch {
          data = { detail: text || `HTTP ${response.status}` }
        }
      }

      // Handle non-OK responses
      if (!response.ok) {
        const errorMessage =
          data?.detail || data?.message || `API Error: ${response.status} ${response.statusText}`

        // Retry logic cho retryable errors
        if (
          retryCount < API_CONFIG.retryAttempts &&
          isRetryableError(response.status)
        ) {
          const delay = getRetryDelay(retryCount)
          console.warn(
            `API request failed (${response.status}), retrying in ${delay}ms... (attempt ${retryCount + 1}/${API_CONFIG.retryAttempts})`
          )
          await sleep(delay)
          return this.fetch<T>(endpoint, options, retryCount + 1)
        }

        throw new ApiError(
          errorMessage,
          response.status,
          endpoint,
          data
        )
      }

      return data as T
    } catch (error) {
      // Handle AbortError (timeout)
      if (error instanceof Error && error.name === "AbortError") {
        // Retry timeout errors
        if (retryCount < API_CONFIG.retryAttempts) {
          const delay = getRetryDelay(retryCount)
          console.warn(
            `Request timeout, retrying in ${delay}ms... (attempt ${retryCount + 1}/${API_CONFIG.retryAttempts})`
          )
          await sleep(delay)
          return this.fetch<T>(endpoint, options, retryCount + 1)
        }
        throw new TimeoutError(`Request timeout after ${API_CONFIG.timeout}ms`)
      }

      // Handle network errors
      if (error instanceof TypeError && error.message.includes("fetch")) {
        // Retry network errors
        if (retryCount < API_CONFIG.retryAttempts) {
          const delay = getRetryDelay(retryCount)
          console.warn(
            `Network error, retrying in ${delay}ms... (attempt ${retryCount + 1}/${API_CONFIG.retryAttempts})`
          )
          await sleep(delay)
          return this.fetch<T>(endpoint, options, retryCount + 1)
        }
        throw new NetworkError(
          "Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng hoặc đảm bảo backend đang chạy.",
          error
        )
      }

      // Re-throw ApiError và các errors khác
      if (error instanceof ApiError || error instanceof NetworkError || error instanceof TimeoutError) {
        throw error
      }

      // Unknown error
      throw new ApiError(
        error instanceof Error ? error.message : "Unknown error occurred",
        undefined,
        endpoint,
        error
      )
    }
  }

  // ========================
  // HEALTH & STATS
  // ========================

  async getHealth(): Promise<HealthStatus> {
    return this.fetch("/health")
  }

  async getStats(): Promise<SystemStats> {
    return this.fetch("/stats")
  }

  // ========================
  // USER ANALYSIS (NEW!)
  // ========================

  async analyzeText(title: string, content?: string, sourceUrl?: string): Promise<UserAnalysisResult> {
    return this.fetch("/analyze/text", {
      method: "POST",
      body: JSON.stringify({ title, content, source_url: sourceUrl }),
    })
  }

  async analyzeRedditUrl(url: string): Promise<RedditAnalysisResult> {
    return this.fetch("/analyze/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    })
  }

  async quickAnalyze(title: string, content?: string): Promise<QuickAnalysisResult> {
    const params = new URLSearchParams({ title })
    if (content) params.set("content", content)
    return this.fetch(`/analyze/quick?${params.toString()}`, {
      method: "POST",
    })
  }

  // ========================
  // ADVANCED ANALYSIS
  // ========================

  async getSourceCredibility(domain: string, minPosts = 5): Promise<SourceCredibility> {
    // Validate domain format (basic validation)
    if (!domain || typeof domain !== "string") {
      throw new ApiError("Domain must be a non-empty string", 400, "/analysis/source")
    }
    
    // Basic domain format validation (allow alphanumeric, dots, hyphens)
    const domainPattern = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$/
    if (!domainPattern.test(domain.trim())) {
      throw new ApiError("Invalid domain format", 400, "/analysis/source")
    }
    
    const sanitizedDomain = domain.trim().toLowerCase()
    return this.fetch(`/analysis/source/${encodeURIComponent(sanitizedDomain)}?min_posts=${minPosts}`)
  }

  async getTopCredibleSources(limit = 20, minPosts = 10): Promise<{ sources: SourceCredibility[]; total: number }> {
    return this.fetch(`/analysis/sources/top-credible?limit=${limit}&min_posts=${minPosts}`)
  }

  async getWarningSources(limit = 20, minPosts = 5): Promise<{ warning_sources: SourceCredibility[]; total: number }> {
    return this.fetch(`/analysis/sources/warning-list?limit=${limit}&min_posts=${minPosts}`)
  }

  async getFakeNewsTrend(days = 30, subreddit?: string): Promise<TrendData> {
    const params = new URLSearchParams({ days: days.toString() })
    if (subreddit) params.set("subreddit", subreddit)
    return this.fetch(`/analysis/trend?${params.toString()}`)
  }

  async getTrendingFakeTopics(days = 7, topN = 20): Promise<{ trending_topics: TrendingTopic[]; total: number; note: string }> {
    return this.fetch(`/analysis/trending-topics?days=${days}&top_n=${topN}`)
  }

  async getRiskAssessment(days = 7, subreddit?: string): Promise<RiskAssessment> {
    const params = new URLSearchParams({ days: days.toString() })
    if (subreddit) params.set("subreddit", subreddit)
    return this.fetch(`/analysis/risk-assessment?${params.toString()}`)
  }

  async getComprehensiveReport(days = 30): Promise<ComprehensiveReport> {
    return this.fetch(`/analysis/report?days=${days}`)
  }

  // ========================
  // ANALYTICS
  // ========================

  async getFakeVsReal(minConfidence = 0.5): Promise<{
    fake_count: number
    real_count: number
    total_count: number
    fake_percentage: number
    real_percentage: number
  }> {
    return this.fetch(`/analytics/fake-vs-real?min_confidence=${minConfidence}`)
  }

  async getTimeline(granularity = "daily", minConfidence = 0.5): Promise<{
    data: Array<{ date: string; fake_count: number; real_count: number; total_count: number }>
    granularity: string
    start_date: string
    end_date: string
  }> {
    return this.fetch(`/analytics/timeline?granularity=${granularity}&min_confidence=${minConfidence}`)
  }

  async getBySubreddit(): Promise<{
    data: Array<{
      subreddit: string
      fake_count: number
      real_count: number
      total_count: number
      fake_percentage: number
    }>
    total_subreddits: number
  }> {
    return this.fetch("/analytics/by-subreddit")
  }

  async getByDomain(topN = 20): Promise<{
    data: Array<{
      domain: string
      fake_count: number
      real_count: number
      total_count: number
      fake_percentage: number
    }>
    total_domains: number
  }> {
    return this.fetch(`/analytics/by-domain?top_n=${topN}`)
  }

  async getKeywords(topN = 50): Promise<{
    fake_keywords: Array<{ word: string; frequency: number; percentage: number }>
    real_keywords: Array<{ word: string; frequency: number; percentage: number }>
    top_n: number
  }> {
    return this.fetch(`/analytics/keywords?top_n=${topN}`)
  }

  async getSummary(): Promise<any> {
    return this.fetch("/analytics/summary")
  }

  // ========================
  // PREDICTION
  // ========================

  async getPredictionStats(): Promise<{
    total_posts: number
    posts_with_prediction: number
    posts_without_prediction: number
    fake_news_count: number
    real_news_count: number
    prediction_coverage: number
  }> {
    return this.fetch("/prediction/stats")
  }

  async getFakePosts(limit = 20, skip = 0, minConfidence = 0.5): Promise<{
    count: number
    posts: any[]
  }> {
    return this.fetch(`/prediction/posts/fake?limit=${limit}&skip=${skip}&min_confidence=${minConfidence}`)
  }

  async getRealPosts(limit = 20, skip = 0, minConfidence = 0.5): Promise<{
    count: number
    posts: any[]
  }> {
    return this.fetch(`/prediction/posts/real?limit=${limit}&skip=${skip}&min_confidence=${minConfidence}`)
  }

  async predictSinglePost(postId: string, enhanced = true): Promise<EnhancedPredictionResult> {
    return this.fetch(`/prediction/single/${postId}?enhanced=${enhanced}`, {
      method: "POST",
    })
  }

  // ========================
  // CRAWLER
  // ========================

  async getCrawlerStatus(): Promise<any> {
    return this.fetch("/crawler/status")
  }

  async triggerCrawl(): Promise<any> {
    return this.fetch("/crawler/run", { method: "POST" })
  }

  async getRecentPosts(limit = 20): Promise<any> {
    return this.fetch(`/crawler/posts/recent?limit=${limit}`)
  }
}

// Export singleton instance
export const api = new ApiClient(API_BASE_URL)

// Export individual functions for backwards compatibility
export const getSourceCredibility = (domain: string, minPosts = 5) => api.getSourceCredibility(domain, minPosts)
export const getTopCredibleSources = (limit = 20, minPosts = 10) => api.getTopCredibleSources(limit, minPosts)
export const getWarningSources = (limit = 20, minPosts = 5) => api.getWarningSources(limit, minPosts)
export const getFakeNewsTrend = (days = 30, subreddit?: string) => api.getFakeNewsTrend(days, subreddit)
export const getTrendingFakeTopics = (days = 7, topN = 20) => api.getTrendingFakeTopics(days, topN)
export const getRiskAssessment = (days = 7, subreddit?: string) => api.getRiskAssessment(days, subreddit)
export const getComprehensiveReport = (days = 30) => api.getComprehensiveReport(days)
export const getBySubreddit = () => api.getBySubreddit()
export const analyzeText = (title: string, content?: string, sourceUrl?: string) => api.analyzeText(title, content, sourceUrl)
export const analyzeRedditUrl = (url: string) => api.analyzeRedditUrl(url)
export const quickAnalyze = (title: string, content?: string) => api.quickAnalyze(title, content)
