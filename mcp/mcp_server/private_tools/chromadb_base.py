import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional, Union
import uuid
import requests
from chromadb import Documents, EmbeddingFunction, Embeddings


class OllamaEmbeddingFunction(EmbeddingFunction):
    """
    使用Ollama API的嵌入函数
    """
    def __init__(self, model: str = "mxbai-embed-large", host: str = "http://localhost:11434"):
        self.model = model
        self.url = f"{host}/api/embed"
    
    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]
        response = requests.post(self.url, json={
            "model": self.model,
            "input": input
        })
        response.raise_for_status()
        data = response.json()
        return data["embeddings"]


class ChromaDBWrapper:
    """
    ChromaDB操作封装类，提供简单易用的接口来操作ChromaDB
    支持本地持久化和HTTP连接两种模式
    """

    def __init__(self, 
                 collection_name: str = "default_collection",
                 embedding_function_name: str = "default",
                 client_type: str = "persistent",
                 persist_directory: str = "./chroma_db",
                 host: str = "localhost", 
                 port: int = 8000,
                 ollama_model: str = "mxbai-embed-large",
                 ollama_host: str = "http://localhost:11434"):
        """
        初始化ChromaDB客户端和集合
        
        参数:
            collection_name: 集合名称
            embedding_function_name: 嵌入函数名称，可选值："default", "openai", "cohere", "huggingface", "ollama"
            client_type: 客户端类型，可选值："persistent"（本地持久化）, "http"（HTTP连接）
            persist_directory: 数据持久化目录（仅persistent模式使用）
            host: ChromaDB服务器主机（仅http模式使用）
            port: ChromaDB服务器端口（仅http模式使用）
            ollama_model: Ollama嵌入模型名称（仅当embedding_function_name="ollama"时使用）
            ollama_host: Ollama服务器URL（仅当embedding_function_name="ollama"时使用）
        """
        # 初始化客户端
        if client_type == "http":
            self.client = chromadb.HttpClient(host=host, port=port)
            print(f"已连接到ChromaDB服务器: {host}:{port}")
        else:
            self.client = chromadb.PersistentClient(path=persist_directory)
            print(f"已创建本地持久化客户端: {persist_directory}")
        
        # 设置embedding函数
        if embedding_function_name == "openai":
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key="your_openai_api_key",
                model_name="text-embedding-ada-002"
            )
        elif embedding_function_name == "cohere":
            self.embedding_function = embedding_functions.CohereEmbeddingFunction(
                api_key="your_cohere_api_key",
                model_name="embed-multilingual-v2.0"
            )
        elif embedding_function_name == "huggingface":
            self.embedding_function = embedding_functions.HuggingFaceEmbeddingFunction(
                api_key="your_huggingface_api_key",
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        elif embedding_function_name == "ollama":
            self.embedding_function = OllamaEmbeddingFunction(
                model=ollama_model,
                host=ollama_host
            )
        else:
            self.embedding_function = None
        
        # 创建或获取集合
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"已连接到集合: {collection_name}")
        except :
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"已创建新集合: {collection_name}")
    
    def add_documents(self, 
                      documents: List[str], 
                      metadatas: Optional[List[Dict[str, Any]]] = None,
                      ids: Optional[List[str]] = None,
                      embeddings: Optional[List[List[float]]] = None) -> List[str]:
        """
        添加文档到集合
        
        参数:
            documents: 文档内容列表
            metadatas: 元数据列表（可选）
            ids: ID列表（可选，如不提供将自动生成）
            embeddings: 预计算的嵌入向量（可选）
        
        返回:
            添加的文档ID列表
        """
        # 如果未提供ID，则自动生成
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]
        
        # 如果未提供元数据，则创建空元数据
        if metadatas is None:
            metadatas = [{} for _ in range(len(documents))]
        
        # 添加文档
        if embeddings:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        print(f"已添加 {len(documents)} 条文档")
        return ids
    
    def search(self, 
               query: str = None, 
               query_embeddings: List[float] = None,
               n_results: int = 5, 
               where: Optional[Dict[str, Any]] = None,
               where_document: Optional[Dict[str, Any]] = None,
               include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        搜索与查询相似的文档
        
        参数:
            query: 查询文本
            query_embeddings: 预计算的查询嵌入向量（可选）
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            include: 要包含在结果中的项目（"documents", "embeddings", "metadatas", "distances"）
        
        返回:
            搜索结果字典
        """
        if not include:
            include = ["documents", "metadatas", "distances"]
            
        if query_embeddings:
            results = self.collection.query(
                query_embeddings=[query_embeddings],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include
            )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include
            )
        
        return results
    
    def get_by_ids(self, ids: List[str], include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        通过ID获取文档
        
        参数:
            ids: 要获取的文档ID列表
            include: 要包含在结果中的项目（"documents", "embeddings", "metadatas"）
        
        返回:
            获取的文档字典
        """
        if not include:
            include = ["documents", "metadatas"]
            
        return self.collection.get(ids=ids, include=include)
    
    def get_all(self, 
                limit: Optional[int] = None, 
                where: Optional[Dict[str, Any]] = None,
                where_document: Optional[Dict[str, Any]] = None,
                include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取所有文档
        
        参数:
            limit: 限制返回数量（可选）
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            include: 要包含在结果中的项目（"documents", "embeddings", "metadatas"）
        
        返回:
            所有文档字典
        """
        if not include:
            include = ["documents", "metadatas"]
            
        return self.collection.get(
            limit=limit,
            where=where,
            where_document=where_document,
            include=include
        )
    
    def update_documents(self, 
                         ids: List[str], 
                         documents: Optional[List[str]] = None, 
                         metadatas: Optional[List[Dict[str, Any]]] = None,
                         embeddings: Optional[List[List[float]]] = None) -> None:
        """
        更新文档
        
        参数:
            ids: 要更新的文档ID列表
            documents: 新的文档内容列表（可选）
            metadatas: 新的元数据列表（可选）
            embeddings: 预计算的嵌入向量（可选）
        """
        update_args = {"ids": ids}
        
        if documents:
            update_args["documents"] = documents
        
        if metadatas:
            update_args["metadatas"] = metadatas
            
        if embeddings:
            update_args["embeddings"] = embeddings
            
        self.collection.update(**update_args)
        print(f"已更新 {len(ids)} 条文档")
    
    def upsert_documents(self, 
                        documents: List[str], 
                        ids: List[str],
                        metadatas: Optional[List[Dict[str, Any]]] = None,
                        embeddings: Optional[List[List[float]]] = None) -> None:
        """
        更新或插入文档（如果ID存在则更新，不存在则插入）
        
        参数:
            documents: 文档内容列表
            ids: ID列表
            metadatas: 元数据列表（可选）
            embeddings: 预计算的嵌入向量（可选）
        """
        upsert_args = {"ids": ids, "documents": documents}
        
        if metadatas:
            upsert_args["metadatas"] = metadatas
            
        if embeddings:
            upsert_args["embeddings"] = embeddings
            
        self.collection.upsert(**upsert_args)
        print(f"已更新或插入 {len(ids)} 条文档")
    
    def delete_by_ids(self, ids: List[str]) -> None:
        """
        通过ID删除文档
        
        参数:
            ids: 要删除的文档ID列表
        """
        self.collection.delete(ids=ids)
        print(f"已删除 {len(ids)} 条文档")
    
    def delete_by_filter(self, 
                        where: Optional[Dict[str, Any]] = None,
                        where_document: Optional[Dict[str, Any]] = None) -> None:
        """
        通过过滤条件删除文档
        
        参数:
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
        """
        self.collection.delete(where=where, where_document=where_document)
        print("已删除符合条件的文档")
    
    def delete_collection(self) -> None:
        """
        删除整个集合
        """
        collection_name = self.collection.name
        self.client.delete_collection(collection_name)
        print(f"已删除集合: {collection_name}")
    
    def count(self) -> int:
        """
        获取集合中文档的数量
        
        返回:
            文档数量
        """
        return self.collection.count()
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        
        返回:
            集合信息字典
        """
        return {
            "name": self.collection.name,
            "count": self.collection.count()
        }
    
    def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        返回:
            集合名称列表
        """
        return self.client.list_collections()
    
    def modify_collection_name(self, new_name: str) -> None:
        """
        修改集合名称
        
        参数:
            new_name: 新的集合名称
        """
        collection_name = self.collection.name
        self.collection.modify(name=new_name)
        print(f"已将集合从 '{collection_name}' 重命名为 '{new_name}'")


# 使用示例
# if __name__ == "__main__":
#     # 初始化 - 使用Ollama嵌入函数
#     db = ChromaDBWrapper(
#         client_type="http",
#         port=8080,
#         collection_name="my_ollama_documents",
#         embedding_function_name="ollama",
#         ollama_model="mxbai-embed-large",
#         ollama_host="http://localhost:11434"
#     )
    
#     # 添加文档
#     docs = [
#         "这是第一个文档",
#         "这是第二个文档",
#         "这是第三个文档，有一些额外的信息"
#     ]
    
#     metadata = [
#         {"source": "book", "author": "张三"},
#         {"source": "article", "author": "李四"},
#         {"source": "web", "author": "王五"}
#     ]
    
#     ids = db.add_documents(documents=docs, metadatas=metadata)
#     print(f"添加的文档ID: {ids}")
    
#     # 查询文档
#     search_results = db.search("额外的信息", n_results=2)
#     print("\n搜索结果:")
#     for i, doc in enumerate(search_results["documents"][0]):
#         print(f"ID: {search_results['ids'][0][i]}")
#         print(f"文档: {doc}")
#         print(f"元数据: {search_results['metadatas'][0][i]}")
#         print(f"距离: {search_results['distances'][0][i]}")
#         print("-" * 30)