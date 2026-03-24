"""记忆服务模块 - 集成 LangChain Memory + HelloAgents MemoryTool

实现用户长期偏好记忆，支持跨会话历史行程复用。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

# LangChain Memory
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import (
    ChatMessageHistory,
    FileChatMessageHistory,
    RedisChatMessageHistory
)
from langchain.schema import HumanMessage, AIMessage, SystemMessage

# HelloAgents MemoryTool
from hello_agents.tools import Tool

from ..config import get_settings

# 记忆存储目录
MEMORY_DIR = Path(__file__).parent.parent.parent / "memory"


class UserPreference(BaseModel):
    """用户偏好模型"""
    user_id: str
    preferred_cities: List[str] = []           # 偏好城市
    preferred_seasons: List[str] = []           # 偏好季节
    preferred_transportations: List[str] = []  # 偏好交通方式
    accommodation_type: str = "经济型"          # 住宿类型
    budget_level: str = "中等"                  # 预算等级
    food_preferences: List[str] = []            # 美食偏好
    travel_styles: List[str] = []              # 旅行风格
    updated_at: str = ""


class TripHistory(BaseModel):
    """行程历史模型"""
    trip_id: str
    user_id: str
    city: str
    start_date: str
    end_date: str
    travel_days: int
    preferences: List[str] = []
    plan_summary: str = ""                     # 行程摘要
    feedback: Optional[str] = None              # 用户反馈
    created_at: str = ""


class MemoryService:
    """记忆服务 - LangChain Memory + HelloAgents MemoryTool 双写"""

    def __init__(self):
        """初始化记忆服务"""
        self.settings = get_settings()

        # 确保记忆目录存在
        MEMORY_DIR.mkdir(exist_ok=True)

        # 初始化 LangChain Memory（会话级）
        self.conversation_memory = ConversationBufferMemory(
            return_messages=True,
            output_key="output",
            input_key="input"
        )

        # 用户偏好存储路径
        self.preferences_file = MEMORY_DIR / "preferences.json"
        self.trip_history_file = MEMORY_DIR / "trip_history.json"

        # 加载已有偏好
        self.user_preferences: Dict[str, UserPreference] = {}
        self._load_preferences()

    def _load_preferences(self):
        """从文件加载用户偏好"""
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, prefs in data.items():
                        self.user_preferences[user_id] = UserPreference(**prefs)
            except Exception as e:
                print(f"⚠️  加载偏好失败: {str(e)}")

    def _save_preferences(self):
        """保存用户偏好到文件"""
        try:
            data = {
                user_id: prefs.model_dump()
                for user_id, prefs in self.user_preferences.items()
            }
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存偏好失败: {str(e)}")

    # ============ 用户偏好管理 ============

    def get_user_preference(self, user_id: str) -> UserPreference:
        """获取用户偏好"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreference(user_id=user_id)
        return self.user_preferences[user_id]

    def update_user_preference(self, user_id: str, **kwargs):
        """更新用户偏好"""
        prefs = self.get_user_preference(user_id)
        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.updated_at = datetime.now().isoformat()
        self.user_preferences[user_id] = prefs
        self._save_preferences()

    def add_preferred_city(self, user_id: str, city: str):
        """添加偏好城市"""
        prefs = self.get_user_preference(user_id)
        if city not in prefs.preferred_cities:
            prefs.preferred_cities.append(city)
            prefs.updated_at = datetime.now().isoformat()
            self._save_preferences()

    def add_travel_style(self, user_id: str, style: str):
        """添加旅行风格"""
        prefs = self.get_user_preference(user_id)
        if style not in prefs.travel_styles:
            prefs.travel_styles.append(style)
            prefs.updated_at = datetime.now().isoformat()
            self._save_preferences()

    # ============ LangChain Memory 接口 ============

    def add_message(self, role: str, content: str):
        """添加消息到会话记忆"""
        if role == "user":
            self.conversation_memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            self.conversation_memory.chat_memory.add_ai_message(content)
        elif role == "system":
            self.conversation_memory.chat_memory.add_message(
                SystemMessage(content=content)
            )

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取会话历史"""
        messages = self.conversation_memory.chat_memory.messages
        return [
            {
                "type": type(msg).__name__,
                "content": msg.content
            }
            for msg in messages
        ]

    def clear_conversation(self):
        """清空会话记忆"""
        self.conversation_memory.clear()

    def get_memory_variables(self) -> Dict[str, Any]:
        """获取记忆变量（用于 Agent）"""
        return self.conversation_memory.load_memory_variables({})

    # ============ 行程历史管理 ============

    def save_trip_history(self, trip: TripHistory):
        """保存行程历史"""
        trip_history = self._load_trip_history()

        # 检查是否已存在
        existing = [t for t in trip_history if t.trip_id == trip.trip_id]
        if existing:
            # 更新
            trip_history = [t if t.trip_id != trip.trip_id else trip for t in trip_history]
        else:
            # 新增
            trip_history.append(trip)

        # 保存
        try:
            data = [t.model_dump() for t in trip_history]
            with open(self.trip_history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存行程历史失败: {str(e)}")

    def _load_trip_history(self) -> List[TripHistory]:
        """加载行程历史"""
        if not self.trip_history_file.exists():
            return []

        try:
            with open(self.trip_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [TripHistory(**t) for t in data]
        except Exception as e:
            print(f"⚠️  加载行程历史失败: {str(e)}")
            return []

    def get_user_trip_history(self, user_id: str, limit: int = 10) -> List[TripHistory]:
        """获取用户的行程历史"""
        all_history = self._load_trip_history()
        user_history = [t for t in all_history if t.user_id == user_id]
        return user_history[:limit]

    def get_similar_trips(self, user_id: str, city: str, travel_days: int) -> List[TripHistory]:
        """获取相似行程推荐"""
        all_history = self.get_user_trip_history(user_id)
        similar = [
            t for t in all_history
            if t.city == city and t.travel_days == travel_days
        ]
        return similar

    # ============ 偏好推荐 ============

    def get_recommended_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取基于历史推荐的偏好"""
        prefs = self.get_user_preference(user_id)
        history = self.get_user_trip_history(user_id)

        # 统计最常去的城市
        city_counts = {}
        for trip in history:
            city_counts[trip.city] = city_counts.get(trip.city, 0) + 1

        most_visited_city = max(city_counts, key=city_counts.get) if city_counts else None

        return {
            "preferred_cities": prefs.preferred_cities,
            "most_visited_city": most_visited_city,
            "preferred_seasons": prefs.preferred_seasons,
            "travel_styles": prefs.travel_styles,
            "accommodation_type": prefs.accommodation_type,
            "budget_level": prefs.budget_level,
            "total_trips": len(history)
        }

    # ============ 构建 Agent Prompt 上下文 ============

    def build_context_for_agent(self, user_id: str) -> str:
        """为 Agent 构建上下文提示"""
        prefs = self.get_user_preference(user_id)
        history = self.get_user_trip_history(user_id, limit=5)

        context = f"""## 用户历史偏好信息

**偏好城市**: {', '.join(prefs.preferred_cities) if prefs.preferred_cities else '暂无'}
**偏好季节**: {', '.join(prefs.preferred_seasons) if prefs.preferred_seasons else '暂无'}
**交通偏好**: {', '.join(prefs.preferred_transportations) if prefs.preferred_transportations else '暂无'}
**住宿类型**: {prefs.accommodation_type}
**预算等级**: {prefs.budget_level}
**美食偏好**: {', '.join(prefs.food_preferences) if prefs.food_preferences else '暂无'}
**旅行风格**: {', '.join(prefs.travel_styles) if prefs.travel_styles else '暂无'}
"""

        if history:
            context += f"""
## 用户历史行程

"""
            for trip in history:
                context += f"""- {trip.city} ({trip.start_date} ~ {trip.end_date}, {trip.travel_days}天)
"""

        return context


# ============ HelloAgents MemoryTool ============

class MemoryTool(Tool):
    """HelloAgents MemoryTool - 用于在 Agent 中访问记忆服务"""

    name = "memory_tool"
    description = "用于管理用户偏好和行程历史的记忆工具"

    def __init__(self, memory_service: Optional[MemoryService] = None):
        super().__init__()
        self.memory_service = memory_service or MemoryService()

    def get_user_preference(self, user_id: str) -> str:
        """获取用户偏好"""
        prefs = self.memory_service.get_user_preference(user_id)
        return prefs.model_dump_json(ensure_ascii=False)

    def update_user_preference(self, user_id: str, preference_type: str, value: str) -> str:
        """更新用户偏好

        Args:
            user_id: 用户ID
            preference_type: 偏好类型 (city/season/transportation/food/travel_style)
            value: 偏好值
        """
        if preference_type == "city":
            self.memory_service.add_preferred_city(user_id, value)
        elif preference_type == "travel_style":
            self.memory_service.add_travel_style(user_id, value)
        else:
            self.memory_service.update_user_preference(
                user_id,
                **{preference_type + "s": [value]}
            )
        return f"已更新用户 {user_id} 的偏好: {preference_type} = {value}"

    def get_trip_history(self, user_id: str, limit: int = 5) -> str:
        """获取行程历史"""
        history = self.memory_service.get_user_trip_history(user_id, limit)
        return json.dumps(
            [t.model_dump() for t in history],
            ensure_ascii=False,
            indent=2
        )

    def get_recommendations(self, user_id: str) -> str:
        """获取推荐信息"""
        recs = self.memory_service.get_recommended_preferences(user_id)
        return json.dumps(recs, ensure_ascii=False, indent=2)

    def _run(self, operation: str, user_id: str, **kwargs) -> str:
        """执行记忆操作"""
        if operation == "get_preference":
            return self.get_user_preference(user_id)
        elif operation == "update_preference":
            return self.update_user_preference(
                user_id,
                kwargs.get("preference_type", ""),
                kwargs.get("value", "")
            )
        elif operation == "get_history":
            return self.get_trip_history(user_id, kwargs.get("limit", 5))
        elif operation == "get_recommendations":
            return self.get_recommendations(user_id)
        else:
            return f"未知操作: {operation}"


# 全局记忆服务实例
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """获取记忆服务单例"""
    global _memory_service

    if _memory_service is None:
        _memory_service = MemoryService()

    return _memory_service


def get_memory_tool() -> MemoryTool:
    """获取 HelloAgents MemoryTool"""
    return MemoryTool(get_memory_service())
