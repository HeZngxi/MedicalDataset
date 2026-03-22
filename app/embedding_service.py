from llama_index.embeddings.dashscope import DashScopeEmbedding
from typing import List, Optional
from app.config import settings


class EmbeddingService:
    """千问 Embedding 服务 - 基于 LlamaIndex"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.model_name = settings.qwen_embedding_model
        
        if not self.api_key:
            print("警告：未设置 DASHSCOPE_API_KEY，无法使用向量化服务")
            return
        
        # 初始化 Embedding 模型
        self.embedder = DashScopeEmbedding(
            model_name=self.model_name,
            api_key=self.api_key
        )
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取单段文本的向量"""
        if not self.api_key:
            return None
        
        try:
            embedding = self.embedder.get_text_embedding(text)
            return embedding
        except Exception as e:
            print(f"获取向量失败：{str(e)}")
            return None
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
        """批量获取向量"""
        if not self.api_key:
            return [None] * len(texts)
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_embeddings = self.embedder.get_text_embedding_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"批量获取向量失败：{str(e)}")
                all_embeddings.extend([None] * len(batch))
        
        return all_embeddings
