# 🔍 Fake News Detector - Backend API

API backend cho hệ thống phát hiện tin giả từ Reddit sử dụng AI.

## 📋 Mục lục

- [Tính năng](#-tính-năng)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#️-cấu-hình)
- [Chạy ứng dụng](#-chạy-ứng-dụng)
- [API Endpoints](#-api-endpoints)
- [Deployment](#-deployment)

## ✨ Tính năng

- 🤖 **AI Detection**: Sử dụng Hugging Face model (Pulk17/Fake-News-Detection) để phát hiện fake news
- 📊 **Analytics**: 10+ endpoints cho visualization và thống kê
- 🔄 **Auto Crawler**: Tự động crawl Reddit posts định kỳ
- 📈 **Advanced Analysis**: Phân tích xu hướng, source credibility, risk assessment
- 🌐 **Cloud Ready**: Docker support cho cloud deployment

## 🚀 Cài đặt

### Yêu cầu

- Python 3.11+
- MongoDB Atlas account
- Reddit API credentials
- HuggingFace API key

### Cài đặt dependencies

```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
.\venv\Scripts\activate  # Windows

# Cài đặt packages
pip install -r requirements.txt
```

## ⚙️ Cấu hình

1. Copy file env.example thành .env:

```bash
cp env.example .env
```

2. Điền các thông tin cần thiết:

```env
# MongoDB Atlas
MONGODB_ATLAS_URI=mongodb+srv://...
MONGODB_DB_NAME=fake_news_detector

# Reddit API (https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=FakeNewsDetector/2.0

# HuggingFace (https://huggingface.co/settings/tokens)
HUGGINGFACE_API_KEY=your_api_key
```

## 🏃 Chạy ứng dụng

### Development

```bash
python main.py
```

Hoặc với uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```bash
docker build -t fake-news-backend .
docker run -p 8000:8000 --env-file .env fake-news-backend
```

## 📚 API Endpoints

### Root Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/stats` | GET | System statistics |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |

### Prediction API (`/prediction`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prediction/single/{post_id}` | POST | Predict single post |
| `/prediction/batch` | POST | Batch prediction |
| `/prediction/status` | GET | Batch prediction status |
| `/prediction/stats` | GET | Prediction statistics |
| `/prediction/posts/fake` | GET | Get fake news posts |
| `/prediction/posts/real` | GET | Get real news posts |

### Analytics API (`/analytics`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/fake-vs-real` | GET | Fake vs Real distribution |
| `/analytics/timeline` | GET | Timeline data |
| `/analytics/by-subreddit` | GET | Stats by subreddit |
| `/analytics/by-domain` | GET | Stats by domain |
| `/analytics/engagement-comparison` | GET | Engagement metrics |
| `/analytics/time-distribution` | GET | Heatmap data |
| `/analytics/keywords` | GET | Keywords frequency |
| `/analytics/confidence-distribution` | GET | Confidence histogram |
| `/analytics/by-flair` | GET | Stats by flair |
| `/analytics/author-credibility` | GET | Author analysis |
| `/analytics/summary` | GET | Summary dashboard |

### Advanced Analysis API (`/analysis`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analysis/source/{domain}` | GET | Source credibility score |
| `/analysis/sources/top-credible` | GET | Most credible sources |
| `/analysis/sources/warning-list` | GET | Least credible sources |
| `/analysis/trend` | GET | Fake news trend analysis |
| `/analysis/trending-topics` | GET | Trending fake topics |
| `/analysis/post/{post_id}` | GET | Detailed post analysis |
| `/analysis/report` | GET | Comprehensive report |
| `/analysis/risk-assessment` | GET | Risk assessment |

### User Analysis API (`/analyze`) ⭐ NEW

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/text` | POST | Phân tích bài viết từ title + content |
| `/analyze/url` | POST | Phân tích từ Reddit URL |
| `/analyze/quick` | POST | Phân tích nhanh (chỉ cần title) |

**Ví dụ sử dụng:**

```bash
# Phân tích từ text
curl -X POST "http://localhost:8000/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{"title": "Breaking: Scientists discover...", "content": "..."}'

# Phân tích từ Reddit URL
curl -X POST "http://localhost:8000/analyze/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://reddit.com/r/news/comments/abc123/..."}'

# Phân tích nhanh
curl -X POST "http://localhost:8000/analyze/quick?title=Breaking news..."
```

### Crawler API (`/crawler`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/crawler/status` | GET | Crawler status |
| `/crawler/run` | POST | Trigger manual crawl |
| `/crawler/start` | POST | Start scheduler |
| `/crawler/stop` | POST | Stop scheduler |
| `/crawler/config` | GET | Crawler configuration |
| `/crawler/stats` | GET | Crawler statistics |
| `/crawler/posts/recent` | GET | Recent posts |

## 🐳 Deployment

### Docker Compose

```bash
# Development
docker-compose -f docker-compose.dev.yml up

# Production
docker-compose up -d
```

### Cloud Platforms

#### Railway

1. Connect GitHub repository
2. Add environment variables
3. Deploy

#### Render

1. Create new Web Service
2. Connect repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### AWS/GCP/Azure

Use Docker image hoặc deploy trực tiếp với uvicorn.

## 📝 License

MIT License

## 🤝 Contributing

Pull requests are welcome!
