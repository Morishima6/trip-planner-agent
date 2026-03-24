@echo off
REM HelloAgents Trip Planner - 部署脚本 (Windows)

echo =========================================
echo HelloAgents Trip Planner 部署脚本
echo =========================================

REM 检查 Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker 未安装，请先安装 Docker
    exit /b 1
)

REM 检查 Docker Compose
docker compose version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    exit /b 1
)

echo ✅ Docker 和 Docker Compose 已安装

REM 检查环境变量文件
if not exist ".env" (
    echo ⚠️  .env 文件不存在，正在从模板创建...
    if exist ".env.example" (
        copy .env.example .env
        echo ✅ 已创建 .env 文件，请编辑并填入实际配置
        exit /b 1
    ) else (
        echo ❌ .env.example 不存在
        exit /b 1
    )
)

echo ✅ 环境变量文件已存在

REM 停止并移除旧容器
echo.
echo =========================================
echo 清理旧容器...
echo =========================================
docker compose down --remove-orphans 2>nul

REM 构建并启动服务
echo.
echo =========================================
echo 构建并启动服务...
echo =========================================
docker compose up --build -d

REM 等待服务启动
echo.
echo =========================================
echo 等待服务启动...
echo =========================================
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo =========================================
echo 检查服务状态...
echo =========================================
docker compose ps

REM 显示访问地址
echo.
echo =========================================
echo ✅ 部署完成!
echo =========================================
echo 访问地址:
echo   - 前端: http://localhost
echo   - 后端 API: http://localhost:8000
echo   - API 文档: http://localhost:8000/docs
echo   - Qdrant Dashboard: http://localhost:6333/dashboard
echo.
echo 查看日志:
echo   docker compose logs -f
echo.
echo 停止服务:
echo   docker compose down
