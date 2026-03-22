# EmbeddingBook - 医学书籍向量检索系统

基于 FastAPI + Chroma + 千问 Embedding 的医学文献语义搜索系统。

## 🎯 功能特性

- ✅ **PDF/EPUB 支持**：自动解析两种格式的医学电子书
- ✅ **智能分块**：使用 LangChain 进行文本分割
- ✅ **中文优化**：采用千问 text-embedding-v2 模型，专为中文医学文本优化
- ✅ **向量检索**：基于 Chroma 数据库的余弦相似度搜索
- ✅ **数据持久化**：向量数据保存在宿主机，容器重启不丢失
- ✅ **增量索引**：自动检测文件变更，只处理新文件或修改过的文件
- ✅ **文件哈希追踪**：使用 MD5 哈希值识别文件变化，避免重复处理
- ✅ **RESTful API**：提供完整的 HTTP 接口和 Swagger UI
- ✅ **Docker 部署**：一键启动，开箱即用

## 🚀 快速开始

### 方式一：一键部署脚本（推荐）

```bash
# 1. 配置 API Key
echo "DASHSCOPE_API_KEY=your_key_here" > .env

# 2. 添加书籍到 bookdata/ 目录
cp your_medical_book.pdf ./bookdata/

# 3. 运行部署脚本
./deploy.sh
```

### 方式二：手动部署

```bash
# 1. 创建 .env文件
cat > .env << EOF
DASHSCOPE_API_KEY=your_api_key_here
EOF

# 2. 启动服务（自动执行增量初始化）
docker-compose up -d --build

# 3. 查看初始化日志
docker-compose logs -f backend

# 4. 测试
curl http://localhost:8011/health
```

💡 **提示**：容器启动时会自动执行增量初始化脚本，无需手动运行！

## 📖 API 使用

### 1. 健康检查
```bash
curl http://localhost:8011/health
```

### 2. 获取统计信息
```bash
curl http://localhost:8011/stats
```

### 3. 搜索文档
```bash
curl -X POST "http://localhost:8011/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "高血压的治疗方法",
    "n_results": 5
  }'
```

### 4. Swagger UI
访问 http://localhost:8011/docs 查看交互式 API 文档

## 🏗️ 架构说明

```
┌─────────────────┐
│   bookdata/     │  医学书籍 (PDF/EPUB)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  initialize_vector_store.py │  初始化脚本
└────────┬────────────────────┘
         │
         ▼
┌─────────────────┐           ┌──────────────────┐
│  Backend 容器   │ ──HTTP──▶ │  Chroma 容器     │
│  (FastAPI)      │  8000     │  (向量数据库)     │
└────────┬────────┘           └────┬─────────────┘
         │                        │
         │                        ▼
         │                 ┌──────────────┐
         └────────────────▶│ chroma_data/ │
                           │ (持久化存储)  │
                           └──────────────┘
```

### 核心组件

| 组件 | 端口 | 说明 |
|------|------|------|
| FastAPI Backend | 8011 | 提供 REST API（主机访问） |
| Chroma DB | 8000 | 向量数据库服务（容器内部） |
| bookdata/ | - | 书籍输入目录 |
| chroma_data/ | - | 向量数据持久化目录 |

**端口映射说明：**
- Chroma：容器内 8000 → 主机 8010（外部访问）
- FastAPI：容器内 8011 → 主机 8011（外部访问）
- 容器间通信：使用容器内端口（Chroma: 8000, FastAPI: 8011）

## 🔧 配置文件

### .env文件
```bash
# 必需：千问 API Key
DASHSCOPE_API_KEY=sk-xxxxxxxx

# 可选：Chroma 配置（容器内部端口）
CHROMA_HOST=chroma
CHROMA_PORT=8000
```

### docker-compose.yml
```yaml
services:
  chroma:
    image: chromadb/chroma:latest
    volumes:
      - ./chroma_data:/chroma_db
  
  backend:
    build: .
    environment:
      - CHROMA_HOST=chroma
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
```

## 📊 工作流程

### 初始化流程
1. 读取 `bookdata/` 目录下的 PDF/EPUB 文件
2. 使用 PyMuPDF/Ebooklib 提取文本
3. 按 500 字符窗口、50 重叠度进行分块
4. 调用千问 API 生成 1536 维向量
5. 通过 HTTP 写入 Chroma 容器
6. Chroma 将向量持久化到 `chroma_data/`

### 查询流程
1. 接收用户查询文本
2. 调用千问 API 生成查询向量
3. 在 Chroma 中搜索最相似的 K 个文档
4. 返回带距离分数的结果

## 🛠️ 常用命令

```bash
# 查看日志（观察初始化过程）
docker-compose logs -f backend
docker-compose logs -f chroma

# 进入容器调试
docker-compose exec backend bash
docker-compose exec chroma bash

# 重新初始化向量库（强制处理所有文件）
docker-compose exec backend python initialize_vector_store.py --force

# 添加新书后重新初始化（增量模式，只处理新书）
docker-compose exec backend python initialize_vector_store.py

# 清理已删除文件的向量
docker-compose exec backend python initialize_vector_store.py --clean

# 重启服务
docker-compose restart

# 完全清理并重建
docker-compose down
rm -rf ./chroma_data/*
docker-compose up -d --build

# 运行测试脚本
./test_deployment.sh
```

## ❓ 常见问题

### Q: 第一次启动很慢？
A: 正常现象。每本书需要：
- 文本提取（PDF 解析）
- 分块处理
- 调用外部 API 生成向量（网络延迟）

预计每本书 1-3 分钟。**但后续启动会非常快**，因为系统会自动跳过已处理的文件！

### Q: 如何添加新书？
A: 
```bash
# 1. 复制新书到 bookdata/
cp new_book.pdf ./bookdata/

# 2. 重启容器或手动执行增量初始化
docker-compose restart
# 或者
docker-compose exec backend python initialize_vector_store.py
```

系统会自动检测并只处理新添加的文件！

### Q: 数据会丢失吗？
A: 不会。向量数据持久化在宿主机的 `./chroma_data/` 目录，容器删除不影响数据。

### Q: 可以在本地测试吗？
A: 可以，但不推荐。如需本地调试：
```python
from app.vector_store import VectorStore
vs = VectorStore()  # 内存模式，不传参数
```

## 📝 技术栈

- **后端框架**: FastAPI 0.104.1
- **向量数据库**: Chroma DB 0.4.18
- **文本处理**: PyMuPDF, Ebooklib, LangChain
- **向量化**: 千问 DashScope Embedding (text-embedding-v2)
- **容器化**: Docker + Docker Compose
- **Python**: 3.10-slim

## 📄 许可证

MIT License

## 🔗 相关链接

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Chroma 文档](https://docs.trychroma.com/)
- [千问 Embedding](https://help.aliyun.com/zh/dashscope/)
- [Swagger UI](http://localhost:8011/docs)

---

**详细部署指南**: 参见 [`README_DEPLOYMENT.md`](README_DEPLOYMENT.md)
