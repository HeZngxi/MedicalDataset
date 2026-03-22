"""
向量库检索测试脚本
用于验证 Chroma 向量库中的数据并测试检索功能
"""

import requests
import json


def test_health_check():
    """健康检查接口测试"""
    print("\n" + "="*60)
    print("1. 健康检查测试")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:8011/health", timeout=5)
        print(f"✓ 健康检查状态码：{response.status_code}")
        print(f"✓ 响应内容：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"✗ 健康检查失败：{e}")
        return False


def test_vector_store_info():
    """查看向量库信息"""
    print("\n" + "="*60)
    print("2. 向量库信息查看")
    print("="*60)
    
    try:
        # 使用 /stats 接口
        response = requests.get("http://localhost:8011/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 向量库集合名称：{data.get('collection_name', 'N/A')}")
            print(f"✓ 文档总数：{data.get('total_documents', 0)}")
            print(f"✓ Chroma 服务器：{data.get('chroma_server', 'N/A')}")
            return True
        else:
            print(f"✗ 获取向量库信息失败：{response.status_code}")
            print(f"响应内容：{response.text}")
            return False
    except Exception as e:
        print(f"✗ 请求失败：{e}")
        return False


def test_search(query="经十二指肠、胃扫查周围结构", top_k=5):
    """语义搜索测试"""
    print("\n" + "="*60)
    print(f"3. 语义搜索测试")
    print("="*60)
    print(f"查询语句：'{query}'")
    print(f"返回数量：top-{top_k}")
    
    try:
        payload = {
            "query": query,
            "n_results": top_k  # 修改为 n_results
        }
        
        response = requests.post(
            "http://localhost:8011/search",  # 移除 /api 前缀
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"\n✓ 搜索成功！找到 {len(results.get('results', []))} 条结果\n")
            
            for i, result in enumerate(results.get('results', []), 1):
                print(f"--- 结果 {i} ---")
                print(f"来源文件：{result.get('source', 'N/A')}")
                print(f"距离分数：{result.get('distance', 0):.4f}")
                print(f"文本内容：{result.get('content', '')[:200]}...")
                print()
            
            return True
        else:
            print(f"✗ 搜索失败：{response.status_code}")
            print(f"响应内容：{response.text}")
            return False
    except Exception as e:
        print(f"✗ 请求失败：{e}")
        return False


def test_multiple_queries():
    """多查询测试"""
    print("\n" + "="*60)
    print("4. 多查询测试")
    print("="*60)
    
    queries = [
        ("医学成像技术", 3),
        ("深度学习算法", 3),
        ("数据处理方法", 3)
    ]
    
    for query, top_k in queries:
        test_search(query, top_k)


def main():
    """主测试函数"""
    print("\n" + "🚀"*30)
    print("向量库数据验证与检索测试")
    print("🚀"*30)
    
    # 1. 健康检查
    health_ok = test_health_check()
    
    if not health_ok:
        print("\n⚠️  服务未正常运行，请检查容器状态")
        return
    
    # 2. 查看向量库信息
    info_ok = test_vector_store_info()
    
    if not info_ok:
        print("\n⚠️  无法获取向量库信息")
        return
    
    # 3. 单个查询测试
    test_search("经十二指肠、胃扫查周围结构", 5)
    
    # 4. 多个查询测试（可选）
    # test_multiple_queries()
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)


if __name__ == "__main__":
    main()
