"""MCP Server - 封装 LangChain RAG 工具为 MCP 服务

使用 FastMCP 框架将 LangChain RAG 服务封装为 MCP Server，
使 HelloAgents 可以通过 MCP 协议调用 LangChain RAG 工具。
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from pydantic import BaseModel

# 导入 RAG 服务
import sys
from pathlib import Path

# 将 backend/app 添加到路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.rag_service import get_rag_service, init_knowledge_base, RAGService

# 创建 MCP Server
mcp = FastMCP("LangChain RAG Tools")

# ============ MCP 工具定义 ============

@mcp.tool()
def rag_knowledge_search(
    query: str,
    user_preferences: Optional[List[str]] = None,
    top_k: int = 3
) -> str:
    """从知识库中搜索相关信息，用于增强旅行规划。

    Args:
        query: 搜索查询，例如"北京三日游推荐"
        user_preferences: 用户偏好列表，例如["历史文化", "美食"]
        top_k: 返回结果数量

    Returns:
        知识库检索结果
    """
    rag_service = get_rag_service()

    result = rag_service.query(
        question=query,
        user_preferences=user_preferences,
        top_k=top_k
    )

    if result.get("answer"):
        return result["answer"]
    return "未找到相关信息"


@mcp.tool()
def rag_similarity_search(
    query: str,
    top_k: int = 5
) -> str:
    """执行向量相似度搜索。

    Args:
        query: 搜索查询
        top_k: 返回结果数量

    Returns:
        相似文档列表
    """
    rag_service = get_rag_service()
    docs = rag_service.similarity_search(query=query, top_k=top_k)

    if not docs:
        return "未找到相似文档"

    results = []
    for i, doc in enumerate(docs, 1):
        results.append(f"--- 文档 {i} ---\n{doc.page_content[:300]}...")

    return "\n\n".join(results)


@mcp.tool()
def rag_get_collection_info() -> str:
    """获取知识库集合信息。

    Returns:
        知识库状态信息
    """
    rag_service = get_rag_service()
    info = rag_service.get_collection_info()

    if "error" in info:
        return f"知识库错误: {info.get('message', info.get('error'))}"

    return f"""知识库信息:
- 集合名称: {info.get('name')}
- 向量数量: {info.get('vectors_count', 0)}
- 文档数量: {info.get('points_count', 0)}
- 状态: {info.get('status')}
"""


@mcp.tool()
def rag_rebuild_knowledge_base(
    excel_path: Optional[str] = None,
    force: bool = True
) -> str:
    """重建知识库。

    Args:
        excel_path: Excel 文件路径（可选）
        force: 是否强制重建

    Returns:
        重建结果
    """
    success = init_knowledge_base(excel_path=excel_path, force_rebuild=force)

    if success:
        return "知识库重建成功"
    return "知识库重建失败"


# ============ 主程序 ============

if __name__ == "__main__":
    import sys

    # 检查是否指定了端口
    port = 8001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    print(f"🚀 启动 LangChain RAG MCP Server...")
    print(f"   端口: {port}")
    print(f"   工具: rag_knowledge_search, rag_similarity_search, rag_get_collection_info, rag_rebuild_knowledge_base")

    # 尝试初始化知识库
    try:
        print("\n📚 初始化知识库...")
        init_knowledge_base()
        print("✅ 知识库初始化完成")
    except Exception as e:
        print(f"⚠️  知识库初始化失败: {str(e)}")
        print("   请确保 Qdrant 服务已启动")

    # 运行 MCP Server
    mcp.run(transport="stdio")
