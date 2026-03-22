import fitz  # PyMuPDF
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict
import os


class DocumentProcessor:
    """文档处理器 - 支持 PDF 和 EPUB"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """从 PDF 文件提取文本"""
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"读取 PDF 失败：{str(e)}")
            return ""
    
    @staticmethod
    def extract_text_from_epub(file_path: str) -> str:
        """从 EPUB 文件提取文本"""
        text = ""
        try:
            book = epub.read_epub(file_path)
            for item in book.get_items():
                if item.get_type() == 9:  # XHTML 类型
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text += soup.get_text() + "\n"
            return text
        except Exception as e:
            print(f"读取 EPUB 失败：{str(e)}")
            return ""
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """将文本分块"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            # 如果不是最后一块，尝试在句子边界处切分
            if end < text_length:
                # 查找最近的句子结束符
                for sep in ['。', '！', '？', '!', '?', '.', '\n']:
                    last_sep = chunk.rfind(sep)
                    if last_sep > chunk_size * 0.5:  # 至少在中间位置之后
                        end = start + last_sep + 1
                        chunk = text[start:end]
                        break
            
            chunks.append(chunk.strip())
            start = end - chunk_overlap
        
        return chunks
    
    @staticmethod
    def process_file(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict]:
        """处理单个文件，返回文本块列表"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        # 根据扩展名选择处理方式
        if ext == '.pdf':
            text = DocumentProcessor.extract_text_from_pdf(file_path)
        elif ext == '.epub':
            text = DocumentProcessor.extract_text_from_epub(file_path)
        else:
            print(f"不支持的文件格式：{ext}")
            return []
        
        # 分块
        chunks = DocumentProcessor.chunk_text(text, chunk_size, chunk_overlap)
        
        # 添加元数据
        documents = []
        for i, chunk in enumerate(chunks):
            if chunk:  # 跳过空块
                documents.append({
                    "content": chunk,
                    "metadata": {
                        "source": filename,
                        "chunk_id": i,
                        "file_path": file_path
                    }
                })
        
        return documents
