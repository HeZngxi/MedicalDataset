# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装构建必要的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 使用 BuildKit 缓存挂载并预编译 Wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir /app/wheels \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    -r requirements.txt


# Stage 2: Final
FROM python:3.10-slim

WORKDIR /app

# 生产环境不需要编译工具
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# 直接安装编译好的包，极大缩短构建时间
RUN pip install --no-cache /wheels/*

# 复制业务代码
COPY app/ ./app/
COPY initialize_vector_store.py .

# 创建数据目录并设置正确权限
RUN mkdir -p /chroma_data && chmod 755 /chroma_data

# 服务端口配置
EXPOSE 8011

# 健康检查（使用 bash 内置 TCP 检测）
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8011/health')" 2>/dev/null || exit 1

# 启动命令：先执行增量初始化，然后启动服务
CMD ["sh", "-c", "python initialize_vector_store.py && uvicorn app.main:app --host 0.0.0.0 --port 8011"]
