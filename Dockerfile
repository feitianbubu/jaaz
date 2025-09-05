# Build stage - Build React frontend (following README steps)
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY react/ ./react/
WORKDIR /app/react
RUN npm install --force
RUN npx vite build

# Production stage - Run application (following README steps)
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for media processing
RUN apt-get update && apt-get install -y \
    libmediainfo0v5 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY server/requirements.txt ./server/
WORKDIR /app/server

# Install Python dependencies (following README steps)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy server application after dependencies
COPY server/ ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/react/dist ./ui/

# 移除此行，让用户数据目录由程序运行时自动创建

# Set environment variables
ENV UI_DIST_DIR=/app/server/ui
ENV USER_DATA_DIR=/app/server/user_data
ENV PYTHONUNBUFFERED=1

EXPOSE 57988

# Run the FastAPI application (following README: python main.py)
CMD ["python", "main.py"]