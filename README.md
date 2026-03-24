# HelloAgents智能旅行助手 🌍✈️

基于HelloAgents框架构建的智能旅行规划助手,集成高德地图MCP服务、LangChain RAG知识库,提供个性化的旅行计划生成。

## ✨ 功能特点

- 🤖 **AI驱动的旅行规划**: 基于HelloAgents框架的SimpleAgent,智能生成详细的多日旅程
- 🗺️ **高德地图集成**: 通过MCP协议接入高德地图服务,支持景点搜索、路线规划、天气查询
- 🧠 **智能工具调用**: Agent自动调用高德地图MCP工具,获取实时POI、路线和天气信息
- 📚 **RAG知识库增强**: 基于LangChain + Qdrant向量数据库,整合旅行攻略数据提供本地化建议
- 🎨 **现代化前端**: Vue3 + TypeScript + Vite,响应式设计,流畅的用户体验
- 📱 **完整功能**: 包含住宿、交通、餐饮和景点游览时间推荐

## 🏗️ 技术栈

### 后端
- **框架**: HelloAgents (基于SimpleAgent)
- **RAG框架**: LangChain + LangChain-Qdrant
- **向量数据库**: Qdrant
- **嵌入模型**: sentence-transformers (all-MiniLM-L6-v2)
- **API**: FastAPI
- **MCP工具**: amap-mcp-server (高德地图)
- **LLM**: 支持多种LLM提供商(OpenAI, DeepSeek等)

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **地图服务**: 高德地图 JavaScript API
- **HTTP客户端**: Axios

## 📁 项目结构

```
helloagents-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent实现
│   │   │   ├── trip_planner_agent.py       # HelloAgents 多智能体
│   │   │   └── langchain_agent.py          # LangChain ReAct Agent
│   │   ├── api/               # FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── trip.py
│   │   │       └── map.py
│   │   ├── services/          # 服务层
│   │   │   ├── amap_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── rag_service.py            # RAG 知识库服务
│   │   │   └── memory_service.py         # 记忆服务
│   │   ├── models/            # 数据模型
│   │   │   └── schemas.py
│   │   └── config.py          # 配置管理
│   ├── mcp/                   # MCP Server
│   │   └── langchain_tools_mcp.py        # LangChain RAG MCP
│   ├── kb/                        # 知识库文件
│   │   └── travel_knowledge.md
│   ├── memory/                    # 用户记忆存储
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # Vue组件
│   │   ├── services/          # API服务
│   │   ├── types/             # TypeScript类型
│   │   └── views/             # 页面视图
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 🚀 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- 高德地图API密钥 (Web服务API和Web端(JS API))
- LLM API密钥 (OpenAI/DeepSeek等)

### 后端安装

1. 进入后端目录
```bash
cd backend
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件,填入你的API密钥
```

5. 启动后端服务
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 配置环境变量
```bash
# 创建.env文件, 填入高德地图Web API Key 和 Web端JS API Key
cp .env.example .env
```

4. 启动开发服务器
```bash
npm run dev
```

5. 打开浏览器访问 `http://localhost:5173`

## 📝 使用指南

1. 在首页填写旅行信息:
   - 目的地城市
   - 旅行日期和天数
   - 交通方式偏好
   - 住宿偏好
   - 旅行风格标签

2. 点击"生成旅行计划"按钮

3. 系统将:
   - 调用HelloAgents Agent生成初步计划
   - Agent自动调用高德地图MCP工具搜索景点
   - Agent获取天气信息和路线规划
   - 整合所有信息生成完整行程

4. 查看结果:
   - 每日详细行程
   - 景点信息与地图标记
   - 交通路线规划
   - 天气预报
   - 餐饮推荐

## 🔧 核心实现

### HelloAgents Agent集成

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

# 创建高德地图MCP工具
amap_tool = MCPTool(
    name="amap",
    server_command=["uvx", "amap-mcp-server"],
    env={"AMAP_MAPS_API_KEY": "your_api_key"},
    auto_expand=True
)

# 创建旅行规划Agent
agent = SimpleAgent(
    name="旅行规划助手",
    llm=HelloAgentsLLM(),
    system_prompt="你是一个专业的旅行规划助手..."
)

# 添加工具
agent.add_tool(amap_tool)
```

### MCP工具调用

Agent可以自动调用以下高德地图MCP工具:
- `maps_text_search`: 搜索景点POI
- `maps_weather`: 查询天气
- `maps_direction_walking_by_address`: 步行路线规划
- `maps_direction_driving_by_address`: 驾车路线规划
- `maps_direction_transit_integrated_by_address`: 公共交通路线规划

### LangChain RAG MCP Server

将 LangChain RAG 工具封装为 MCP Server，实现跨框架工具调用：

```bash
# 启动 RAG MCP Server
python backend/mcp/langchain_tools_mcp.py
```

**可用 MCP 工具：**
- `rag_knowledge_search`: 知识库搜索
- `rag_similarity_search`: 向量相似度搜索
- `rag_get_collection_info`: 获取知识库信息
- `rag_rebuild_knowledge_base`: 重建知识库

### RAG 知识库集成

系统集成了基于 LangChain + Qdrant 的 RAG 知识库检索增强功能:

```python
from app.services.rag_service import RAGService, init_knowledge_base

# 初始化 RAG 服务
rag_service = RAGService()

# 从 Excel 构建知识库（可选）
init_knowledge_base(excel_path="path/to/your/travel_data.xlsx")

# 查询知识库
result = rag_service.query(
    question="北京3日游推荐",
    user_preferences=["历史文化", "美食"],
    top_k=3
)
```

**知识库支持:**
- 从 Markdown 文件加载旅行攻略
- 从 Excel 文件批量导入旅行数据
- 向量相似度检索
- 结合用户偏好的增强查询

### 记忆服务集成

系统集成了 LangChain Memory + HelloAgents MemoryTool 双写记忆服务：

```python
from app.services.memory_service import MemoryService, get_memory_service

# 获取记忆服务
memory_service = get_memory_service()

# 获取用户偏好
prefs = memory_service.get_user_preference(user_id="user123")

# 更新偏好
memory_service.add_preferred_city(user_id="user123", city="北京")
memory_service.add_travel_style(user_id="user123", style="历史文化")

# 获取行程历史
history = memory_service.get_user_trip_history(user_id="user123", limit=10)

# 获取推荐
recommendations = memory_service.get_recommended_preferences(user_id="user123")
```

### LangChain ReAct Agent

系统支持使用 LangChain ReAct Agent 替代部分 HelloAgents Agent：

```python
from app.agents.langchain_agent import LangChainTripAgent, get_langchain_agent

# 获取 LangChain Agent
agent = get_langchain_agent(use_rag=True, use_memory=True)

# 运行 Agent
result = agent.run(
    user_input="帮我规划一个北京3日游",
    user_id="user123"
)

print(result["output"])
```

**Agent 特性：**
- ReAct 推理模式
- 统一工具调用（MCP + RAG + Memory）
- 可动态添加工具
- 支持中间步骤返回

## 📄 API文档

启动后端服务后,访问 `http://localhost:8000/docs` 查看完整的API文档。

主要端点:
- `POST /api/trip/plan` - 生成旅行计划
- `GET /api/map/poi` - 搜索POI
- `GET /api/map/weather` - 查询天气
- `POST /api/map/route` - 规划路线

## 🤝 贡献指南

欢迎提交Pull Request或Issue!

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents) - 智能体教程
- [HelloAgents框架](https://github.com/jjyaoao/HelloAgents) - 智能体框架
- [高德地图开放平台](https://lbs.amap.com/) - 地图服务
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) - 高德地图MCP服务器

---

**HelloAgents智能旅行助手** - 让旅行计划变得简单而智能 🌈

