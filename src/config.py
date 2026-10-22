"""
全局配置中心。

所有可调参数（模型选择、温度、token 预算等）集中管理，
便于审计和统一调整。
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """静态配置命名空间 —— 不实例化。"""

    # ------------------------------------------------------------------
    # LLM 供应商（兼容 OpenAI 协议）
    # ------------------------------------------------------------------
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "")

    # ------------------------------------------------------------------
    # Java 业务后端
    # ------------------------------------------------------------------
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8080/api")

    # ------------------------------------------------------------------
    # 生成参数
    # ------------------------------------------------------------------
    TEMPERATURE = 0.7
    MAX_TOKENS = 1024

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    @classmethod
    def validate(cls) -> None:
        """检查必需的环境变量是否已配置，缺失则抛出 RuntimeError。"""
        missing = []
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not cls.LLM_BASE_URL:
            missing.append("LLM_BASE_URL")
        if not cls.LLM_MODEL_ID:
            missing.append("LLM_MODEL_ID")
        if missing:
            raise RuntimeError(
                f"缺少必需的环境变量: {', '.join(missing)}。"
                "请将 .env.example 复制为 .env 并填入你的配置值。"
            )
