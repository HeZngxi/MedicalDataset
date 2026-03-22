"""初始化向量库脚本 - 支持增量索引和文件变更检测"""

import os
import asyncio
import hashlib
from app.document_processor import DocumentProcessor
from app.embedding_service import EmbeddingService
from app.vector_store import VectorStore
from app.config import settings


def compute_file_hash(file_path: str) -> str:
    """计算文件的 MD5 哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        MD5 哈希字符串
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_existing_files_metadata(vector_store: VectorStore) -> dict:
    """从向量库中获取已存在文件的元数据
    
    Args:
        vector_store: 向量存储实例
        
    Returns:
        字典 {filename: {'hash': hash_value, 'chunk_count': count}}
    """
    existing_files = {}
    
    try:
        # 获取集合中的所有元数据
        collection = vector_store.collection
        count = collection.count()
        
        if count == 0:
            return existing_files
        
        # 分批获取元数据（避免一次性加载过多）
        batch_size = 1000
        offset = 0
        
        while offset < count:
            results = collection.get(
                include=["metadatas"],
                limit=batch_size,
                offset=offset
            )
            
            for metadata in results["metadatas"]:
                source = metadata.get("source", "")
                file_hash = metadata.get("file_hash", "")
                
                if source and source not in existing_files:
                    existing_files[source] = {
                        "hash": file_hash,
                        "chunk_count": 0
                    }
                
                if source:
                    existing_files[source]["chunk_count"] += 1
            
            offset += batch_size
        
        print(f"✓ 从向量库中加载了 {len(existing_files)} 个已存在文件的元数据")
        
    except Exception as e:
        print(f"⚠️  读取已存在文件元数据失败：{e}")
    
    return existing_files


def should_process_file(filename: str, file_path: str, 
                       existing_files: dict) -> tuple[bool, str]:
    """判断是否需要处理文件
    
    Args:
        filename: 文件名
        file_path: 文件完整路径
        existing_files: 已存在文件的元数据
        
    Returns:
        (是否需要处理，原因说明)
    """
    # 如果是新文件，需要处理
    if filename not in existing_files:
        return True, "新文件"
    
    # 计算当前文件的哈希值
    current_hash = compute_file_hash(file_path)
    stored_hash = existing_files[filename].get("hash", "")
    
    # 如果哈希值不同，说明文件被修改过，需要重新处理
    if current_hash != stored_hash:
        return True, "文件已修改"
    
    # 文件未变化，跳过
    return False, "文件未变化"


def delete_old_vectors(vector_store: VectorStore, filename: str):
    """删除旧文件对应的所有向量
    
    Args:
        vector_store: 向量存储实例
        filename: 要删除的文件名
    """
    try:
        collection = vector_store.collection
        
        # 获取所有该文件的文档 ID
        results = collection.get(
            where={"source": filename},
            include=[]
        )
        
        if results["ids"]:
            collection.delete(ids=results["ids"])
            print(f"✓ 删除了 {len(results['ids'])} 个旧向量")
    
    except Exception as e:
        print(f"⚠️  删除旧向量失败：{e}")



def initialize_vector_store(force: bool = False, clean_removed: bool = False):
    """初始化向量库（支持增量更新）
    
    Args:
        force: 是否强制重新初始化所有文件
        clean_removed: 是否清理已删除文件的向量
    """
    print("=" * 60)
    print("开始初始化向量库...")
    print("=" * 60)
    
    # 1. 检查 API Key
    if not settings.dashscope_api_key:
        print("错误：未设置 DASHSCOPE_API_KEY 环境变量")
        print("请在 .env文件中配置 API Key")
        return False
    
    print(f"✓ API Key 已配置")
    
    # 2. 初始化服务
    embedding_service = EmbeddingService()
    
    # ✅ 关键修改：使用 HTTP 连接到 Chroma 容器
    # 从环境变量中读取配置，如果没有则使用默认值
    chroma_host = os.getenv("CHROMA_HOST", "chroma")
    chroma_port = int(os.getenv("CHROMA_PORT", 8000))
    
    print(f"\n正在连接 Chroma 服务器：{chroma_host}:{chroma_port}")
    vector_store = VectorStore(host=chroma_host, port=chroma_port)
    print(f"✓ Chroma 向量库已连接")
    
    # 3. 查找所有书籍文件
    bookdata_dir = "/bookdata"
    if not os.path.exists(bookdata_dir):
        print(f"错误：书籍目录 {bookdata_dir} 不存在")
        return False
    
    supported_extensions = ['.pdf', '.epub']
    book_files = []
    
    for filename in os.listdir(bookdata_dir):
        file_path = os.path.join(bookdata_dir, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        # 跳过 Zone.Identifier 文件和目录
        if filename.endswith(':Zone.Identifier') or os.path.isdir(file_path):
            continue
        
        if ext in supported_extensions:
            book_files.append(file_path)
            print(f"✓ 找到书籍文件：{filename}")
    
    if not book_files:
        print(f"错误：在 {bookdata_dir} 目录下没有找到支持的书籍文件")
        return False
    
    print(f"\n共找到 {len(book_files)} 个书籍文件")
    
    # 4. 获取已存在的文件元数据
    existing_files = get_existing_files_metadata(vector_store)
    
    # 5. 分类处理文件
    files_to_process = []
    files_to_skip = []
    
    for file_path in book_files:
        filename = os.path.basename(file_path)
        
        if force:
            # 强制模式：全部重新处理
            files_to_process.append((file_path, "强制重新处理"))
        else:
            # 增量模式：智能判断
            should_process, reason = should_process_file(
                filename, file_path, existing_files
            )
            
            if should_process:
                files_to_process.append((file_path, reason))
            else:
                files_to_skip.append((file_path, reason))
                print(f"⊘ 跳过：{filename} ({reason})")
    
    # 6. 处理需要更新的书籍
    total_chunks = 0
    total_valid_embeddings = 0
    processed_count = 0
    skipped_count = len(files_to_skip)
    
    for file_path, reason in files_to_process:
        filename = os.path.basename(file_path)
        print(f"\n{'='*60}")
        print(f"[{processed_count + 1}/{len(files_to_process)}] 正在处理：{filename}")
        print(f"原因：{reason}")
        print(f"{'='*60}")
        
        try:
            # 如果是重新处理，先删除旧向量
            if not force and filename in existing_files:
                print(f"检测到文件变更，删除旧向量...")
                delete_old_vectors(vector_store, filename)
            
            # 处理文档
            documents = DocumentProcessor.process_file(
                file_path,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap
            )
            
            if not documents:
                print(f"警告：{filename} 没有提取到有效文本")
                continue
            
            print(f"✓ 提取了 {len(documents)} 个文本块")
            total_chunks += len(documents)
            
            # 计算文件哈希并添加到元数据
            file_hash = compute_file_hash(file_path)
            for doc in documents:
                doc["metadata"]["file_hash"] = file_hash
            
            # 批量获取向量
            print("正在调用千问 API 进行向量化...")
            texts = [doc['content'] for doc in documents]
            
            # 批量获取向量
            embeddings = embedding_service.get_embeddings_batch(texts, batch_size=10)
            
            valid_count = sum(1 for emb in embeddings if emb is not None)
            print(f"✓ 成功生成 {valid_count}/{len(embeddings)} 个向量")
            total_valid_embeddings += valid_count
            
            # 添加到向量库
            vector_store.add_documents(documents, embeddings)
            processed_count += 1
            
        except Exception as e:
            print(f"处理 {filename} 时出错：{str(e)}")
            continue
    
    # 7. 清理已删除的文件（可选）
    if clean_removed and not force:
        print(f"\n{'='*60}")
        print("检查已删除的文件...")
        print(f"{'='*60}")
        
        current_filenames = {os.path.basename(f) for f in book_files}
        removed_files = set(existing_files.keys()) - current_filenames
        
        if removed_files:
            print(f"发现 {len(removed_files)} 个已删除的文件:")
            for filename in removed_files:
                print(f"  - {filename}")
                delete_old_vectors(vector_store, filename)
        else:
            print("✓ 没有已删除的文件")
    
    # 8. 统计信息
    print(f"\n{'='*60}")
    print("初始化完成！")
    print(f"{'='*60}")
    print(f"新处理文件：{processed_count} 个")
    print(f"跳过文件：{skipped_count} 个")
    print(f"总文本块数：{total_chunks}")
    print(f"成功向量化：{total_valid_embeddings}")
    print(f"向量库大小：{vector_store.get_count()} 个文档")
    print(f"\n✅ 向量数据已持久化到 Chroma 数据库，Docker 关闭后不会丢失！")
    
    return True


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    force_init = "--force" in sys.argv or "-f" in sys.argv
    clean_removed = "--clean" in sys.argv or "-c" in sys.argv
    
    success = initialize_vector_store(
        force=force_init, 
        clean_removed=clean_removed
    )
    
    if success:
        print("\n✓ 向量库构建成功！")
    else:
        print("\n✗ 向量库构建失败！")
        exit(1)
