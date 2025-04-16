from mcp.server.fastmcp import FastMCP
import sys
import uvicorn
import argparse
from typing import List, Dict, Optional, Any
import json

sys.path.append('/oper/ch/code')
# Import ChromaDBWrapper
from chromadb_base import ChromaDBWrapper
import os 



def create_parser():
    """Create and return the argument parser for MCP Server with ChromaDB and Ollama integration."""
    parser = argparse.ArgumentParser(description='FastMCP server for ChromaDB with Ollama embedding')

    parser.add_argument('--collection_name',
                        type=str,
                        default=os.getenv('CHROMA_COLLECTION_NAME', 'my_ollama_documents'),
                        help='Collection name for ChromaDB')

    parser.add_argument('--embedding_function',
                        type=str,
                        choices=['default', 'openai', 'cohere', 'huggingface', 'ollama'],
                        default=os.getenv('CHROMA_EMBEDDING_FUNCTION', 'ollama'),
                        help='Embedding function type')

    parser.add_argument('--client_type',
                        choices=['http', 'persistent'],
                        default=os.getenv('CHROMA_CLIENT_TYPE', 'http'),
                        help='Type of ChromaDB client to use')

    parser.add_argument('--persist_directory',
                        default=os.getenv('CHROMA_DATA_DIR', './chroma_db'),
                        help='Directory for persistent client data (only used with persistent client)')

    parser.add_argument('--host',
                        default=os.getenv('CHROMA_HOST', 'localhost'),
                        help='ChromaDB server host (used for HTTP client)')

    parser.add_argument('--port',
                        type=int,
                        default=int(os.getenv('CHROMA_PORT', 8080)),
                        help='ChromaDB server port (used for HTTP client)')

    parser.add_argument('--ollama_model',
                        type=str,
                        default=os.getenv('OLLAMA_MODEL', 'mxbai-embed-large'),
                        help='Ollama embedding model name')

    parser.add_argument('--ollama_host',
                        type=str,
                        default=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                        help='Ollama server URL')

    parser.add_argument('--mcp_port',
                        type=int,
                        default=int(os.getenv('MCP_PORT', 8090)),
                        help='Port to run the MCP server on')

    return parser
    
def get_chroma_client():
    """Get or create the global Chroma client instance."""
    global chroma_db
    parser = create_parser()
    args = parser.parse_args()
    chroma_db = ChromaDBWrapper(
        collection_name=args.collection_name,
        embedding_function_name=args.embedding_function,
        client_type=args.client_type,
        persist_directory=args.persist_directory,
        host=args.host,
        port=args.port,
        ollama_model=args.ollama_model,
        ollama_host=args.ollama_host)
    # chroma_db = ChromaDBWrapper(
    # collection_name='my_ollama_documents',
    # embedding_function_name='ollama',
    # client_type='http',
    # persist_directory='/oper/ch/chromadb',
    # host='localhost',
    # port=8080,
    # ollama_model='mxbai-embed-large',
    # ollama_host='http://localhost:11434')
    return chroma_db

            
# Initialize FastMCP
mcp = FastMCP("ChromaDB MCP Tools")

# ChromaDB tools
@mcp.tool()
def add_documents(documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, 
                  ids: Optional[List[str]] = None) -> List[str]:
    """添加文档到ChromaDB集合
    
    Args:
        documents: 文档内容列表
        metadatas: 元数据列表（可选）
        ids: ID列表（可选，如不提供将自动生成）
        
    Returns:
        添加的文档ID列表
    """
    chroma_db = get_chroma_client()
    return chroma_db.add_documents(documents=documents, metadatas=metadatas, ids=ids)

@mcp.tool()
def search_documents(query: str = None, n_results: int = 5, 
                     where: Optional[str] = None, 
                     where_document: Optional[str] = None,
                     include: Optional[List[str]] = None) -> Dict[str, Any]:
    """搜索与查询相似的文档
    
    Args:
        query: 查询文本
        n_results: 返回结果数量
        where: 元数据过滤条件，JSON格式字符串
        where_document: 文档内容过滤条件，JSON格式字符串
        include: 要包含在结果中的项目，可选值："documents", "embeddings", "metadatas", "distances"
        
    Returns:
        搜索结果
    """
    chroma_db = get_chroma_client()
    # 解析JSON字符串参数
    where_dict = json.loads(where) if where else None
    where_document_dict = json.loads(where_document) if where_document else None
    
    return chroma_db.search(
        query=query, 
        n_results=n_results, 
        where=where_dict, 
        where_document=where_document_dict,
        include=include
    )

@mcp.tool()
def get_documents_by_ids(ids: List[str], include: Optional[List[str]] = None) -> Dict[str, Any]:
    """通过ID获取文档
    
    Args:
        ids: 要获取的文档ID列表
        include: 要包含在结果中的项目，可选值："documents", "embeddings", "metadatas"
    
    Returns:
        获取的文档信息
    """
    chroma_db = get_chroma_client()
    return chroma_db.get_by_ids(ids=ids, include=include)

@mcp.tool()
def get_all_documents(limit: Optional[int] = None, 
                      where: Optional[str] = None,
                      where_document: Optional[str] = None,
                      include: Optional[List[str]] = None) -> Dict[str, Any]:
    """获取所有文档
    
    Args:
        limit: 限制返回数量（可选）
        where: 元数据过滤条件，JSON格式字符串
        where_document: 文档内容过滤条件，JSON格式字符串
        include: 要包含在结果中的项目，可选值："documents", "embeddings", "metadatas"
    
    Returns:
        所有文档信息
    """
    chroma_db = get_chroma_client()
    # 解析JSON字符串参数
    where_dict = json.loads(where) if where else None
    where_document_dict = json.loads(where_document) if where_document else None
    
    return chroma_db.get_all(
        limit=limit, 
        where=where_dict, 
        where_document=where_document_dict,
        include=include
    )

@mcp.tool()
def update_documents(ids: List[str], 
                     documents: Optional[List[str]] = None, 
                     metadatas: Optional[List[Dict[str, Any]]] = None) -> str:
    """更新文档
    
    Args:
        ids: 要更新的文档ID列表
        documents: 新的文档内容列表（可选）
        metadatas: 新的元数据列表（可选）
    
    Returns:
        更新结果消息
    """
    chroma_db = get_chroma_client()
    chroma_db.update_documents(ids=ids, documents=documents, metadatas=metadatas)
    return f"成功更新 {len(ids)} 条文档"

@mcp.tool()
def upsert_documents(documents: List[str], 
                     ids: List[str],
                     metadatas: Optional[List[Dict[str, Any]]] = None) -> str:
    """更新或插入文档（如果ID存在则更新，不存在则插入）
    
    Args:
        documents: 文档内容列表
        ids: ID列表
        metadatas: 元数据列表（可选）
    
    Returns:
        操作结果消息
    """
    chroma_db = get_chroma_client()
    chroma_db.upsert_documents(documents=documents, ids=ids, metadatas=metadatas)
    return f"成功更新或插入 {len(ids)} 条文档"

@mcp.tool()
def delete_documents_by_ids(ids: List[str]) -> str:
    """通过ID删除文档
    
    Args:
        ids: 要删除的文档ID列表
    
    Returns:
        删除结果消息
    """
    chroma_db = get_chroma_client()
    chroma_db.delete_by_ids(ids=ids)
    return f"成功删除 {len(ids)} 条文档"

@mcp.tool()
def delete_documents_by_filter(where: Optional[str] = None,
                               where_document: Optional[str] = None) -> str:
    """通过过滤条件删除文档
    
    Args:
        where: 元数据过滤条件，JSON格式字符串
        where_document: 文档内容过滤条件，JSON格式字符串
    
    Returns:
        删除结果消息
    """
    chroma_db = get_chroma_client()
    # 解析JSON字符串参数
    where_dict = json.loads(where) if where else None
    where_document_dict = json.loads(where_document) if where_document else None
    
    chroma_db.delete_by_filter(where=where_dict, where_document=where_document_dict)
    return "成功删除符合条件的文档"

@mcp.tool()
def get_document_count() -> int:
    """获取集合中文档的数量
    
    Returns:
        文档数量
    """
    chroma_db = get_chroma_client()
    return chroma_db.count()

@mcp.tool()
def get_collection_info() -> Dict[str, Any]:
    """获取集合信息
    
    Returns:
        集合信息
    """
    chroma_db = get_chroma_client()
    return chroma_db.get_collection_info()

@mcp.tool()
def list_all_collections() -> List[str]:
    """列出所有集合
    
    Returns:
        集合名称列表
    """
    chroma_db = get_chroma_client()
    return chroma_db.list_collections()

@mcp.tool()
def modify_collection_name(new_name: str) -> str:
    """修改集合名称
    
    Args:
        new_name: 新的集合名称
    
    Returns:
        操作结果消息
    """
    chroma_db = get_chroma_client()
    old_name = chroma_db.collection.name
    chroma_db.modify_collection_name(new_name=new_name)
    return f"成功将集合从 '{old_name}' 重命名为 '{new_name}'"

@mcp.tool()
def delete_current_collection() -> str:
    """删除当前使用的集合
    
    Returns:
        操作结果消息
    """
    chroma_db = get_chroma_client()
    collection_name = chroma_db.collection.name
    chroma_db.delete_collection()
    return f"成功删除集合: {collection_name}"

def main():
    """Entry point for the Chroma MCP server."""
    # parser = create_parser()
    # args = parser.parse_args()
       # Initialize client with parsed args
    try:
        get_chroma_client()
        print("Successfully initialized Chroma client")
    except Exception as e:
        print(f"Failed to initialize Chroma client: {str(e)}")
        raise
    
    # Initialize and run the server
    print("Starting MCP server")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # Start the FastMCP server
    main()
    # print(f"Starting ChromaDB MCP Server on port {args.mcp_port} ...")
    # mcp.run()
    # uvicorn.run(mcp, host="0.0.0.0", port=args.mcp_port)