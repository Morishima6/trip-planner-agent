#!/bin/bash
# HelloAgents Trip Planner - 部署脚本

set -e

echo "========================================="
echo "HelloAgents Trip Planner 部署脚本"
echo "========================================="

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 和 Docker Compose 已安装"

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，正在从模板创建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已创建 .env 文件，请编辑并填入实际配置"
        exit 1
    else
        echo "❌ .env.example 不存在"
        exit 1
    fi
fi

echo "✅ 环境变量文件已存在"

# 停止并移除旧容器（如果存在）
echo ""
echo "========================================="
echo "清理旧容器..."
echo "========================================="
docker compose down --remove-orphans 2>/dev/null || true

# 构建并启动服务
echo ""
echo "========================================="
echo "构建并启动服务..."
echo "========================================="
docker compose up --build -d

# 等待服务启动
echo ""
echo "========================================="
echo "等待服务启动..."
echo "========================================="
sleep 10

# 检查服务状态
echo ""
echo "========================================="
echo "检查服务状态..."
echo "========================================="
docker compose ps

# 显示访问地址
echo ""
echo "========================================="
echo "✅ 部署完成!"
echo "========================================="
echo "访问地址:"
echo "  - 前端: http://localhost"
echo "  - 后端 API: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""
echo "查看日志:"
echo "  docker compose logs -f"
echo ""
echo "停止服务:"
echo "  docker compose down"
