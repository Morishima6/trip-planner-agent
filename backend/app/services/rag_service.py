"""RAG 服务模块 - 基于 LangChain + Qdrant 实现知识检索增强"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# LangChain 核心
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.schema.output_parser import StrOutputParser

# LangChain 向量存储
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings

# LangChain LLM
from langchain_openai import ChatOpenAI

# Qdrant 客户端
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import ResponseHandlingException

from ..config import get_settings


# ============ 知识库目录 ============
KB_DIR = Path(__file__).parent.parent.parent / "kb"


class RAGService:
    """RAG 检索增强服务 - 使用 LangChain + Qdrant"""

    def __init__(
        self,
        collection_name: str = "travel_knowledge",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model: str = "qwen-plus"
    ):
        """初始化 RAG 服务

        Args:
            collection_name: Qdrant 集合名称
            embedding_model: 嵌入模型名称
            llm_model: LLM 模型名称
        """
        self.settings = get_settings()
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.llm_model = llm_model

        # 初始化嵌入模型
        print(f"🔄 初始化嵌入模型: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'}
        )

        # 初始化 Qdrant 客户端
        self.qdrant_client = QdrantClient(
            host="localhost",
            port=6333,
            timeout=10
        )

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=llm_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0.7,
            request_timeout=60
        )

        # QA 链
        self.qa_chain = None
        self._init_qa_chain()

    def _init_qa_chain(self):
        """初始化 QA 链"""
        # 定义 QA prompt
        qa_prompt_template = """你是一个专业的旅行顾问助手。根据以下知识库中的相关信息，回答用户的问题。

        知识库内容:
        {context}

        用户问题: {question}

        请基于知识库内容给出准确的回答。如果知识库中没有相关信息，请如实说明。
        """

        qa_prompt = PromptTemplate(
            template=qa_prompt_template,
            input_variables=["context", "question"]
        )

        # 创建检索器
        try:
            vectorstore = Qdrant(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )
            retriever = vectorstore.as_retriever(
                search_kwargs={"k": 5}
            )

            # 创建 QA 链
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={
                    "prompt": qa_prompt,
                    "output_parser": StrOutputParser()
                },
                return_source_documents=True
            )
            print(f"✅ QA 链初始化成功")
        except Exception as e:
            print(f"⚠️  QA 链初始化失败: {str(e)}")
            print(f"   可能是 Qdrant 服务未启动或集合不存在")
            self.qa_chain = None

    def build_knowledge_base(
        self,
        documents: Optional[List[Document]] = None,
        excel_path: Optional[str] = None
    ) -> bool:
        """构建知识库

        Args:
            documents: LangChain Document 列表
            excel_path: Excel 文件路径（可选，用于从 Excel 导入）

        Returns:
            构建是否成功
        """
        try:
            # 如果提供了 Excel 文件，先转换为文档
            if excel_path:
                documents = self._load_from_excel(excel_path)

            if not documents:
                # 尝试从 kb 目录加载 markdown 文件
                documents = self._load_from_markdown()

            if not documents:
                print("⚠️  没有找到任何文档可供导入")
                return False

            print(f"📚 开始构建知识库，共 {len(documents)} 个文档...")

            # 创建 Qdrant 集合
            self._create_collection_if_not_exists()

            # 加载到 Qdrant
            vectorstore = Qdrant.from_documents(
                client=self.qdrant_client,
                documents=documents,
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )

            print(f"✅ 知识库构建成功，共导入 {len(documents)} 个文档")
            # 重新初始化 QA 链
            self._init_qa_chain()
            return True

        except Exception as e:
            print(f"❌ 知识库构建失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _load_from_excel(self, excel_path: str) -> List[Document]:
        """从 Excel 文件加载数据并转换为文档

        Args:
            excel_path: Excel 文件路径

        Returns:
            Document 列表
        """
        try:
            import pandas as pd

            # 读取 Excel
            df = pd.read_excel(excel_path)
            print(f"📊 从 Excel 读取了 {len(df)} 条数据")

            documents = []
            for idx, row in df.iterrows():
                # 将每行转换为文本
                content_parts = []
                for col, value in row.items():
                    if pd.notna(value):
                        content_parts.append(f"{col}: {value}")

                content = "\n".join(content_parts)

                doc = Document(
                    page_content=content,
                    metadata={
                        "source": excel_path,
                        "row_index": idx,
                        "type": "travel_guide",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"⚠️  加载 Excel 失败: {str(e)}")
            return []

    def _load_from_markdown(self) -> List[Document]:
        """从 kb 目录加载 Markdown 文件

        Returns:
            Document 列表
        """
        if not KB_DIR.exists():
            print(f"⚠️  知识库目录不存在: {KB_DIR}")
            return []

        documents = []
        for md_file in KB_DIR.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(md_file.relative_to(KB_DIR)),
                        "type": "markdown",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                documents.append(doc)
                print(f"   加载: {md_file.name}")
            except Exception as e:
                print(f"   ⚠️  加载失败: {md_file.name} - {str(e)}")

        return documents

    def _create_collection_if_not_exists(self):
        """创建 Qdrant 集合（如果不存在）"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # 获取嵌入向量维度
                sample_embedding = self.embeddings.embed_query("test")
                vector_size = len(sample_embedding)

                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ 创建 Qdrant 集合: {self.collection_name}")
            else:
                print(f"📂 使用已有集合: {self.collection_name}")

        except ResponseHandlingException as e:
            print(f"⚠️  Qdrant 服务可能未启动: {str(e)}")
            print(f"   请确保 Qdrant 服务正在运行 (docker run -p 6333:6333 qdrant/qdrant)")
        except Exception as e:
            print(f"⚠️  创建集合失败: {str(e)}")

    def query(
        self,
        question: str,
        user_preferences: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """查询知识库

        Args:
            question: 用户问题
            user_preferences: 用户偏好列表
            top_k: 返回结果数量

        Returns:
            包含答案和来源的字典
        """
        # 增强查询：加入用户偏好
        enhanced_query = question
        if user_preferences:
            enhanced_query = f"{question}，用户偏好: {', '.join(user_preferences)}"

        # 如果 QA 链未初始化，尝试重新初始化
        if self.qa_chain is None:
            self._init_qa_chain()

        if self.qa_chain is None:
            return {
                "answer": "知识库服务暂不可用，请确保 Qdrant 服务已启动",
                "sources": [],
                "error": "QA chain not initialized"
            }

        try:
            result = self.qa_chain.invoke({"query": enhanced_query})

            # 提取来源文档
            sources = []
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    sources.append({
                        "content": doc.page_content[:200] + "...",
                        "metadata": doc.metadata
                    })

            return {
                "answer": result["result"],
                "sources": sources,
                "query": enhanced_query
            }

        except Exception as e:
            print(f"❌ RAG 查询失败: {str(e)}")
            return {
                "answer": f"查询失败: {str(e)}",
                "sources": [],
                "error": str(e)
            }

    def similarity_search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Document]:
        """相似度搜索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            文档列表
        """
        try:
            vectorstore = Qdrant(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )

            docs = vectorstore.similarity_search(
                query=query,
                k=top_k
            )

            return docs

        except Exception as e:
            print(f"❌ 相似度搜索失败: {str(e)}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息

        Returns:
            集合信息字典
        """
        try:
            collection_info = self.qdrant_client.get_collection(
                collection_name=self.collection_name
            )
            return {
                "name": collection_info.name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status.name
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "集合可能不存在或 Qdrant 服务未启动"
            }


# 全局 RAG 服务实例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取 RAG 服务单例"""
    global _rag_service

    if _rag_service is None:
        _rag_service = RAGService()

    return _rag_service


def init_knowledge_base(
    excel_path: Optional[str] = None,
    force_rebuild: bool = False
) -> bool:
    """初始化知识库

    Args:
        excel_path: Excel 文件路径
        force_rebuild: 是否强制重建

    Returns:
        是否成功
    """
    rag_service = get_rag_service()

    # 检查是否需要重建
    if not force_rebuild:
        info = rag_service.get_collection_info()
        if "vectors_count" in info and info["vectors_count"] > 0:
            print(f"📂 知识库已存在，共 {info['vectors_count']} 个向量")
            return True

    # 重建知识库
    return rag_service.build_knowledge_base(excel_path=excel_path)
