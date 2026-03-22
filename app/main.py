import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from app.config import settings
from app.vector_store import VectorStore
from app.embedding_service import EmbeddingService


app = FastAPI(
    title="医学书籍向量库 API",
    description="基于 Chroma + 千问 Embedding 的医学书籍检索系统",
    version="1.0.0"
)


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    n_results: int = 5


class SearchResult(BaseModel):
    """搜索结果"""
    content: str
    source: str
    chunk_id: int
    distance: float


class QueryResponse(BaseModel):
    """查询响应"""
    results: List[SearchResult]
    total: int


# 全局变量
vector_store: Optional[VectorStore] = None
embedding_service: Optional[EmbeddingService] = None


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global vector_store, embedding_service
    
    print("正在初始化向量库服务...")
    
    # ✅ 关键修改：使用 HTTP 连接到 Chroma 容器
    chroma_host = os.getenv("CHROMA_HOST", "chroma")
    chroma_port = int(os.getenv("CHROMA_PORT", 8010))
    
    print(f"正在连接 Chroma 服务器：{chroma_host}:{chroma_port}")
    vector_store = VectorStore(host=chroma_host, port=chroma_port)
    
    # 初始化嵌入服务
    embedding_service = EmbeddingService()
    
    count = vector_store.get_count()
    print(f"✓ 向量库已加载，包含 {count} 个文档")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "医学书籍向量库 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量库未初始化")
    
    return {
        "status": "healthy",
        "vector_store_count": vector_store.get_count()
    }


@app.post("/search", response_model=QueryResponse)
async def search(request: QueryRequest):
    """搜索相似文档
    
    Args:
        request: 查询请求，包含查询文本和返回结果数量
        
    Returns:
        搜索结果列表
    """
    if not embedding_service or not vector_store:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    try:
        # 获取查询向量 (同步方法，不需要 await)
        query_embedding = embedding_service.get_embedding(request.query)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="无法获取查询向量")
        
        # 搜索相似文档
        results = vector_store.search(
            query_embedding=query_embedding,
            n_results=request.n_results
        )
        
        # 格式化结果
        search_results = []
        for i, content in enumerate(results["documents"]):
            metadata = results["metadatas"][i]
            distance = results["distances"][i] if i < len(results["distances"]) else 0.0
            
            search_results.append(SearchResult(
                content=content,
                source=metadata.get("source", "unknown"),
                chunk_id=metadata.get("chunk_id", 0),
                distance=float(distance)
            ))
        
        return QueryResponse(
            results=search_results,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量库未初始化")
    
    chroma_host = os.getenv("CHROMA_HOST", "chroma")
    chroma_port = int(os.getenv("CHROMA_PORT", 8010))
    
    return {
        "total_documents": vector_store.get_count(),
        "collection_name": settings.collection_name,
        "chroma_server": f"{chroma_host}:{chroma_port}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
