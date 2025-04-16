from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

class MCPClientManager:
    """
    A class to manage MCP client sessions and tool interactions.
    """
    
    def __init__(self, server_params_list):
        """
        Initialize the MCPClientManager with a list of server parameters.
        
        Args:
            server_params_list: List of server parameters for connecting to MCP services
        """
        self.server_params_list = server_params_list
        self.sessions = None
        self.session_index = {}
        self.tool_descriptions = ""
        
    async def _create_mcp_client(self, server_params):
        """
        Create and initialize a single MCP client.
        
        Args:
            server_params: Parameters for connecting to the server
            
        Returns:
            Dict containing session, read, write, and client objects
        """
        client = stdio_client(server_params)
        proc = getattr(client, "proc", None) 
        read, write = await client.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        return {"session": session, "read": read, "write": write, "client": client, "proc": proc}
    
    async def _close_mcp_session(self, session_data):
        """
        Gracefully close a single MCP session and its subprocess.
        
        Args:
            session_data: Dictionary containing session, read, write, client, and proc objects
        """
        session = session_data.get("session")
        client = session_data.get("client")
        proc = session_data.get("proc")
        
        try:
            # 先关闭会话
            if session:
                await session.__aexit__(None, None, None)
                
            # 然后关闭客户端
            if client:
                await client.__aexit__(None, None, None)
                
            # 最后确保子进程已终止
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=3)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    
        except Exception as e:
            print(f"[关闭会话异常] {e}")
    
    async def initialize(self):
        """
        Initialize connections to all MCP servers and fetch tool descriptions.
        
        Returns:
            Tuple of (tool_descriptions, session_index)
        """
        self.sessions = []
        try:
            # 逐个创建会话，避免使用asyncio.gather可能导致的问题
            for p in self.server_params_list:
                session_data = await self._create_mcp_client(p)
                self.sessions.append(session_data)
            
            self.tool_descriptions = []
            self.session_index = {}
            
            for idx, tool in enumerate(self.sessions):
                response = await tool['session'].list_tools()
                descriptions = "\n".join(
                    f"{line.name}:{line.description}。inputSchema:{line.inputSchema}" 
                    for line in response.tools
                )
                self.session_index.update({line.name: idx for line in response.tools})
                self.tool_descriptions.append(descriptions)
            
            self.tool_descriptions = "\n".join(self.tool_descriptions)
            return self.tool_descriptions, self.session_index
            
        except Exception as e:
            print(f"初始化错误: {e}")
            # 在发生错误时关闭已创建的会话
            await self.close_all()
            return "", {}
    
    async def run_tool(self, name, input_dict):
        """
        Run a specific tool with the given input.
        
        Args:
            name: Name of the tool to run
            input_dict: Input parameters for the tool
            
        Returns:
            The content returned by the tool
        """
        if name not in self.session_index:
            raise ValueError(f"工具 '{name}' 不存在")
            
        # 为执行工具单独创建一个会话
        temp_session = None
        
        try:
            idx = self.session_index[name]
            temp_session = await self._create_mcp_client(self.server_params_list[idx])
            content = await temp_session['session'].call_tool(name, input_dict)
            return content.content[0].text
            
        except Exception as e:
            print(f"运行工具错误: {e}")
            return None
        finally:
            # 确保关闭临时会话
            if temp_session:
                await self._close_mcp_session(temp_session)
    
    async def close_all(self):
        """
        Close all open sessions.
        """
        if self.sessions:
            # 逐个关闭会话，避免使用asyncio.gather
            for session_data in self.sessions:
                await self._close_mcp_session(session_data)
            self.sessions = []

response={
  "name": "write_file",
  "input_dict": {
    "path": "/oper/ch/code/test.txt",
    "content": "床前明月光，\n疑是地上霜。\n举头望明月，\n低头思故乡。"
  }
}

async def main():
    manager = None
    try: 
        server_params_list = [
           StdioServerParameters(command="uv", args=["run", "/oper/work/endian/intelligent_agent/mcp/mcp_server/private_tools/chromadb_mcp.py",]),
#           StdioServerParameters(command="npx", args=["--yes", "@modelcontextprotocol/server-filesystem", '/oper/ch/code']),
#           StdioServerParameters(command="uvx", args=["mcp-server-fetch"]),
#           StdioServerParameters(command="npx", args=["-y","@modelcontextprotocol/server-puppeteer"]),
        ]
        manager = MCPClientManager(server_params_list)
        descriptions, _ = await manager.initialize()
        print("可用工具:", descriptions)
        
        if descriptions:  # 只有在成功初始化时才尝试运行工具
            result = await manager.run_tool("get_collection_info", None) 
            print("工具结果:", result)
            result = await manager.run_tool(response['name'], response['input_dict']) 
            print("工具结果:", result)
    except Exception as e:
        print(f"主函数异常: {e}")
    finally:
        if manager:
            await manager.close_all()
        print('任务完成')

if __name__ == "__main__":
    asyncio.run(main())
