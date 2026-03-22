import chromadb
from typing import List, Dict, Optional
from app.config import settings


class VectorStore:
    """Chroma 向量存储"""
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """初始化向量存储
        
        Args:
            host: Chroma 服务器地址 (例如 'chroma')，用于 Docker 容器间通信
            port: Chroma 服务器端口 (例如 8000)
        """
        if host and port:
            # ✅ 服务器模式：通过 HTTP 连接到专用的 Chroma 容器
            print(f"正在连接到 Chroma 服务器：{host}:{port}")
            self.client = chromadb.HttpClient(
                host=host,
                port=port
            )
        else:
            # ⚠️ 备选：本地内存模式 (仅用于本地快速调试，不推荐生产环境)
            print("⚠️  使用本地内存模式（数据不会持久化）")
            self.client = chromadb.Client()
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
    
    def add_documents(self, documents: List[Dict], embeddings: List[List[float]]):
        """添加文档到向量库
        
        Args:
            documents: 文档列表，每个文档包含 content 和 metadata
            embeddings: 对应的向量列表
        """
        if len(documents) != len(embeddings):
            raise ValueError("文档数量和向量数量不匹配")
        
        ids = []
        contents = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = f"{doc['metadata']['source']}_{doc['metadata']['chunk_id']}"
            ids.append(doc_id)
            contents.append(doc['content'])
            metadatas.append(doc['metadata'])
            
            # 过滤掉 None 值的向量
            if embeddings[i] is None:
                print(f"警告：文档 {doc_id} 的向量为 None，跳过")
                continue
        
        # 批量添加到 Chroma
        valid_indices = [i for i, emb in enumerate(embeddings) if emb is not None]
        if valid_indices:
            self.collection.add(
                ids=[ids[i] for i in valid_indices],
                documents=[contents[i] for i in valid_indices],
                embeddings=[embeddings[i] for i in valid_indices],
                metadatas=[metadatas[i] for i in valid_indices]
            )
            print(f"成功添加 {len(valid_indices)} 个文档到向量库")
    
    def search(self, query_embedding: List[float], n_results: int = 5) -> Dict:
        """搜索相似文档
        
        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量
            
        Returns:
            搜索结果，包含 documents、metadatas、distances 等
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 返回扁平化的结果
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }
    
    def get_count(self) -> int:
        """获取向量库中文档总数"""
        return self.collection.count()
    
    def delete_collection(self):
        """删除集合（用于重置）"""
        self.client.delete_collection(name=settings.collection_name)
