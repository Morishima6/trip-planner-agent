"""LangChain Agent 模块 - 使用 ReAct 模式替代部分 HelloAgents Agent

使用 LangChain 的 Agent 框架（ReAct 模式）构建智能旅行规划 Agent，
可以统一调用 MCP 工具、RAG 工具和 Memory 工具。
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# LangChain Agent
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.schema import AgentAction, AgentFinish

# LangChain LLM
from langchain_openai import ChatOpenAI

from ..config import get_settings
from ..services.rag_service import get_rag_service
from ..services.memory_service import get_memory_service


# ============ LangChain Tools 定义 ============

def create_langchain_tools(
    amap_mcp_tools: Optional[List] = None,
    rag_service=None,
    memory_service=None
) -> List[Tool]:
    """创建 LangChain Tools 列表

    Args:
        amap_mcp_tools: HelloAgents MCP 工具列表
        rag_service: RAG 服务实例
        memory_service: 记忆服务实例

    Returns:
        LangChain Tool 列表
    """
    tools = []

    # ============ RAG 工具 ============
    if rag_service:
        @Tool(name="knowledge_search", description="从知识库中搜索旅行相关信息，包括景点推荐、美食、交通、安全注意事项等")
        def knowledge_search_func(query: str) -> str:
            """搜索知识库"""
            result = rag_service.query(question=query, top_k=3)
            if result.get("answer"):
                return result["answer"]
            return "未找到相关信息"

        tools.append(knowledge_search_func)

        @Tool(name="similarity_search", description="执行向量相似度搜索，找到与查询最相似的文档")
        def similarity_search_func(query: str) -> str:
            """相似度搜索"""
            docs = rag_service.similarity_search(query=query, top_k=3)
            if not docs:
                return "未找到相似文档"
            results = []
            for i, doc in enumerate(docs, 1):
                results.append(f"文档 {i}: {doc.page_content[:200]}...")
            return "\n\n".join(results)

        tools.append(similarity_search_func)

    # ============ Memory 工具 ============
    if memory_service:
        @Tool(name="get_user_preference", description="获取用户的偏好信息，包括喜欢的城市、交通方式、住宿类型等")
        def get_preference_func(user_id: str = "default") -> str:
            """获取用户偏好"""
            prefs = memory_service.get_user_preference(user_id)
            return prefs.model_dump_json(ensure_ascii=False, indent=2)

        tools.append(get_preference_func)

        @Tool(name="get_trip_history", description="获取用户的历史行程记录，用于参考之前的旅行计划")
        def get_history_func(user_id: str = "default", limit: int = 5) -> str:
            """获取行程历史"""
            history = memory_service.get_user_trip_history(user_id, limit)
            return json.dumps([t.model_dump() for t in history], ensure_ascii=False, indent=2)

        tools.append(get_history_func)

        @Tool(name="get_recommendations", description="基于用户历史获取个性化推荐")
        def get_recommendations_func(user_id: str = "default") -> str:
            """获取推荐"""
            recs = memory_service.get_recommended_preferences(user_id)
            return json.dumps(recs, ensure_ascii=False, indent=2)

        tools.append(get_recommendations_func)

        @Tool(name="update_preference", description="更新用户偏好信息")
        def update_preference_func(user_id: str, preference_type: str, value: str) -> str:
            """更新偏好"""
            if preference_type == "city":
                memory_service.add_preferred_city(user_id, value)
            elif preference_type == "travel_style":
                memory_service.add_travel_style(user_id, value)
            return f"已更新用户 {user_id} 的 {preference_type} 为 {value}"

        tools.append(update_preference_func)

    # ============ 预留：地图工具（需要 MCP 转换）============
    # 如果有 HelloAgents MCP 工具，可以在这里转换

    return tools


# ============ ReAct Agent Prompt ============

REACT_AGENT_PROMPT = """你是一个专业的旅行规划助手。你的任务是根据用户的需求，使用可用的工具来规划旅行。

## 可用工具

{tools}

## 工具描述

{tool_descriptions}

## 上下文信息

{intermediate_steps}

## 用户需求

{input}

## 输出要求

请按照以下格式输出：

1. 首先思考用户需要什么信息
2. 如果需要查询工具，使用以下格式：
   - Thought: 你需要思考接下来应该做什么
   - Action: 工具名称
   - Action Input: 传递给工具的参数
3. 获得工具返回结果后，继续思考下一步
4. 最终给出完整的旅行规划

请开始规划：
"""


class LangChainTripAgent:
    """LangChain ReAct 旅行规划 Agent

    使用 LangChain ReAct 模式，可以统一调用：
    - RAG 知识库工具
    - Memory 记忆工具
    - MCP 地图工具（通过转换）
    """

    def __init__(
        self,
        llm_model: str = "gpt-4",
        amap_mcp_tools: Optional[List] = None,
        use_rag: bool = True,
        use_memory: bool = True
    ):
        """初始化 LangChain Agent

        Args:
            llm_model: LLM 模型名称
            amap_mcp_tools: HelloAgents MCP 工具列表
            use_rag: 是否启用 RAG
            use_memory: 是否启用 Memory
        """
        self.settings = get_settings()

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=llm_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0.7,
            request_timeout=60
        )

        # 获取服务实例
        self.rag_service = get_rag_service() if use_rag else None
        self.memory_service = get_memory_service() if use_memory else None

        # 创建工具列表
        self.tools = create_langchain_tools(
            amap_mcp_tools=amap_mcp_tools,
            rag_service=self.rag_service,
            memory_service=self.memory_service
        )

        # 创建 Agent
        self._create_agent()

    def _create_agent(self):
        """创建 ReAct Agent"""
        # 构建工具描述
        tool_descriptions = "\n".join(
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        )

        # 构建 prompt
        prompt = PromptTemplate.from_template(REACT_AGENT_PROMPT)
        prompt = prompt.partial(
            tools="\n".join([f"{t.name}: {t.description}" for t in self.tools]),
            tool_descriptions=tool_descriptions
        )

        # 创建 ReAct Agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # 创建 Agent Executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors="请检查输出格式并重试",
            return_intermediate_steps=True
        )

        print(f"✅ LangChain ReAct Agent 初始化完成")
        print(f"   工具数量: {len(self.tools)}")
        print(f"   工具列表: {[t.name for t in self.tools]}")

    def run(self, user_input: str, user_id: str = "default") -> Dict[str, Any]:
        """运行 Agent

        Args:
            user_input: 用户输入
            user_id: 用户 ID

        Returns:
            包含结果和中间步骤的字典
        """
        # 构建完整输入（包含用户偏好上下文）
        full_input = user_input

        if self.memory_service:
            # 添加用户偏好上下文
            context = self.memory_service.build_context_for_agent(user_id)
            full_input = f"{context}\n\n## 当前需求\n{user_input}"

        try:
            result = self.agent_executor.invoke({"input": full_input})

            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True
            }

        except Exception as e:
            print(f"❌ Agent 执行失败: {str(e)}")
            return {
                "output": f"执行失败: {str(e)}",
                "intermediate_steps": [],
                "success": False,
                "error": str(e)
            }

    def add_tool(self, tool: Tool):
        """添加工具"""
        self.tools.append(tool)
        # 重新创建 Agent
        self._create_agent()


# ============ 混合 Agent（LangChain + HelloAgents）============

class HybridTripPlanner:
    """混合旅行规划器 - 同时使用 LangChain Agent 和 HelloAgents Agent

    策略：
    - 简单查询：使用 LangChain ReAct Agent（快速响应）
    - 复杂规划：使用 HelloAgents MultiAgent（深度思考）
    - RAG + Memory：两者共享
    """

    def __init__(self):
        """初始化混合规划器"""
        self.settings = get_settings()

        # 初始化服务
        from ..services.llm_service import get_llm
        from hello_agents import SimpleAgent
        from hello_agents.tools import MCPTool

        self.llm = get_llm()

        # HelloAgents 模式（保留原有实现）
        print("🔄 初始化 HelloAgents 模式...")
        # ... 原有代码 ...

        # LangChain 模式（新实现）
        print("🔄 初始化 LangChain 模式...")
        self.langchain_agent = LangChainTripAgent(
            use_rag=True,
            use_memory=True
        )

    def plan_trip(
        self,
        user_input: str,
        use_langchain: bool = False,
        user_id: str = "default"
    ) -> str:
        """规划旅行

        Args:
            user_input: 用户输入
            use_langchain: 是否使用 LangChain Agent
            user_id: 用户 ID

        Returns:
            旅行计划
        """
        if use_langchain:
            result = self.langchain_agent.run(user_input, user_id)
            return result.get("output", "")
        else:
            # 使用 HelloAgents
            # ... 原有逻辑 ...
            return "请使用 HelloAgents 模式"


# 全局实例
_langchain_agent: Optional[LangChainTripAgent] = None


def get_langchain_agent(
    use_rag: bool = True,
    use_memory: bool = True
) -> LangChainTripAgent:
    """获取 LangChain Agent 单例"""
    global _langchain_agent

    if _langchain_agent is None:
        _langchain_agent = LangChainTripAgent(
            use_rag=use_rag,
            use_memory=use_memory
        )

    return _langchain_agent
