# ===========================
# FAKE NEWS DETECTOR BACKEND
# Production Dockerfile (FIXED)
# ===========================

# --- Stage 1: Builder ---
    FROM python:3.11-slim as builder

    WORKDIR /app
    
    # Cài đặt các công cụ cần thiết để build (gcc,...)
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*
    
    # 1. Tạo môi trường ảo (Virtual Environment) ở thư mục chung /opt
    #    Điều này giúp tránh lỗi quyền hạn của thư mục /root
    RUN python -m venv /opt/venv
    
    # 2. Kích hoạt môi trường ảo cho các lệnh tiếp theo
    ENV PATH="/opt/venv/bin:$PATH"
    
    COPY requirements.txt .
    
    # 3. Cài đặt thư viện VÀO TRONG môi trường ảo
    RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt
    
    # --- Stage 2: Production ---
    FROM python:3.11-slim
    
    WORKDIR /app
    
    # Cài curl cho healthcheck
    RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/*
    
    # 4. Copy toàn bộ môi trường ảo từ builder sang
    #    Lúc này thư viện nằm ở /opt/venv, ai cũng đọc được
    COPY --from=builder /opt/venv /opt/venv
    
    # 5. Thiết lập biến môi trường để hệ thống tự nhận diện lệnh python, uvicorn...
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Copy source code
    COPY . .
    
    # Tạo user thường để chạy app (Bảo mật)
    RUN useradd -m -u 1000 appuser && \
        chown -R appuser:appuser /app
        # Không cần chown /root nữa vì ta không dùng nó
    
    USER appuser
    
    # Expose port
    EXPOSE 8000
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
        CMD curl -f http://localhost:8000/health || exit 1
    
    # Environment variables
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        ENVIRONMENT=production \
        port=8000
    
    # 6. Chạy app
    #    Lưu ý: "app.main:app" hay "main:app" phụ thuộc vào cấu trúc thư mục của bạn.
    #    Nếu file main.py nằm ngay ngoài cùng thư mục backend, dùng "main:app"
    #    Nếu file main.py nằm trong folder app/, dùng "app.main:app"
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
