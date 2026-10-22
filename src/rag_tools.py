"""
Lightweight LangChain tool wrappers for the sibling local-rag project.

Importing src.nodes happens in both CLI and eval paths. Keep the expensive
local-rag imports lazy so eval startup does not load embedding/RAG dependencies
unless the private-document tool is actually called.
"""

from __future__ import annotations

from langchain_core.tools import tool

from src.local_rag_path import ensure_local_rag_path


@tool
def local_document_search(query: str) -> str:
    """
    搜索本地内部文档知识库（产品手册、技术白皮书、FAQ、内部规范等）。

    调用此工具时，你的任务是：
    - 将用户问题的核心内容提取为搜索查询
    - 工具会返回基于内部文档生成的答案
    - 将答案自然地呈现给用户

    何时使用：
    - 用户询问需要查阅内部文档才能回答的问题
    - 产品手册中才有的详细规格、兼容性信息
    - 内部规范、流程说明
    - 技术白皮书中的深度内容

    不要使用：
    - 一般商品咨询（使用 search_product_specs）
    - 订单查询或售后（使用对应工具）

    参数:
        query: 搜索查询字符串，用中文提取用户问题的核心关键词
    """
    ensure_local_rag_path()
    from agent.rag_tool import local_document_search as _local_document_search

    return _local_document_search.invoke({"query": query})
