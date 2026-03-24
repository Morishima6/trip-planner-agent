# 基础镜像 - 使用更小的 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（用于运行 MCP）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app ./app
COPY kb ./kb
COPY mcp ./mcp

# 创建必要的目录
RUN mkdir -p /app/memory /app/logs

# 如果有本地的 .env 文件，复制到容器中
# 注意：生产环境请使用 docker compose 的环境变量挂载

# 暴露端口
EXPOSE 8000

# 启动命令
# 默认启动 FastAPI
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
