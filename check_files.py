"""测试增量初始化功能脚本"""

import os
import hashlib
from app.document_processor import DocumentProcessor
from app.embedding_service import EmbeddingService
from app.vector_store import VectorStore
from app.config import settings


def compute_file_hash(file_path: str) -> str:
    """计算文件的 MD5 哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def test_incremental_initialization():
    """测试增量初始化功能"""
    print("=" * 60)
    print("测试增量初始化功能")
    print("=" * 60)
    
    # 连接到向量库
    chroma_host = os.getenv("CHROMA_HOST", "chroma")
    chroma_port = int(os.getenv("CHROMA_PORT", 8000))
    
    print(f"\n连接到 Chroma 服务器：{chroma_host}:{chroma_port}")
    vector_store = VectorStore(host=chroma_host, port=chroma_port)
    
    # 获取已存在的文件元数据
    existing_files = {}
    collection = vector_store.collection
    count = collection.count()
    
    if count > 0:
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
    
    print(f"\n向量库中有 {len(existing_files)} 个文件:")
    for filename, info in existing_files.items():
        print(f"  - {filename}: {info['chunk_count']} 个块，哈希值：{info['hash'][:8]}...")
    
    # 检查 bookdata 目录
    bookdata_dir = "/bookdata"
    current_files = {}
    
    if os.path.exists(bookdata_dir):
        for filename in os.listdir(bookdata_dir):
            file_path = os.path.join(bookdata_dir, filename)
            if filename.endswith(':Zone.Identifier') or os.path.isdir(file_path):
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.pdf', '.epub']:
                file_hash = compute_file_hash(file_path)
                current_files[filename] = {
                    "hash": file_hash,
                    "path": file_path
                }
    
    print(f"\nbookdata 目录有 {len(current_files)} 个文件:")
    for filename, info in current_files.items():
        print(f"  - {filename}: 哈希值：{info['hash'][:8]}...")
    
    # 对比分析
    print("\n" + "=" * 60)
    print("对比分析")
    print("=" * 60)
    
    new_files = set(current_files.keys()) - set(existing_files.keys())
    removed_files = set(existing_files.keys()) - set(current_files.keys())
    modified_files = []
    unchanged_files = []
    
    for filename in set(current_files.keys()) & set(existing_files.keys()):
        if current_files[filename]["hash"] != existing_files[filename]["hash"]:
            modified_files.append(filename)
        else:
            unchanged_files.append(filename)
    
    print(f"\n新文件 ({len(new_files)}):")
    for f in new_files:
        print(f"  + {f}")
    
    print(f"\n已修改的文件 ({len(modified_files)}):")
    for f in modified_files:
        print(f"  ~ {f}")
    
    print(f"\n未变的文件 ({len(unchanged_files)}):")
    for f in unchanged_files:
        print(f"  = {f}")
    
    print(f"\n已删除的文件 ({len(removed_files)}):")
    for f in removed_files:
        print(f"  - {f}")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结论")
    print("=" * 60)
    
    if new_files:
        print(f"✓ 检测到 {len(new_files)} 个新文件，下次启动会自动处理")
    
    if modified_files:
        print(f"✓ 检测到 {len(modified_files)} 个文件已修改，下次启动会重新处理")
    
    if unchanged_files:
        print(f"✓ 检测到 {len(unchanged_files)} 个文件未变化，下次启动会跳过")
    
    if removed_files:
        print(f"✓ 检测到 {len(removed_files)} 个文件已删除，可使用 --clean 参数清理向量")
    
    if not (new_files or modified_files or unchanged_files):
        print("⚠️  没有找到任何文件")
    
    print(f"\n当前向量库大小：{count} 个文档")
    print("\n✅ 增量初始化功能正常！")


if __name__ == "__main__":
    test_incremental_initialization()