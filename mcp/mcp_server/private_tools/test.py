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
        read, write = await client.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        return {"session": session, "read": read, "write": write, "client": client}
    
    async def _close_mcp_session(self, session, read, write, client):
        """
        Close a single MCP session and its resources.
        
        Args:
            session: The session to close
            read: Read stream
            write: Write stream
            client: Client object
        """
        await read.aclose()
        await write.aclose()
    
    async def initialize(self):
        """
        Initialize connections to all MCP servers and fetch tool descriptions.
        
        Returns:
            Tuple of (tool_descriptions, session_index)
        """
        try:
            self.sessions = await asyncio.gather(
                *(self._create_mcp_client(p) for p in self.server_params_list)
            )
            
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
        finally:
            await asyncio.gather(*(self._close_mcp_session(**e) for e in self.sessions))
    
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
            
        try:
            temp_sessions = await asyncio.gather(
                *(self._create_mcp_client(p) for p in self.server_params_list)
            )
            
            session = temp_sessions[self.session_index[name]]['session']
            content = await session.call_tool(name, input_dict)
            return content.content[0].text
            
        except Exception as e:
            print(f"运行工具错误: {e}")
        finally:
            if temp_sessions:
                await asyncio.gather(
                    *(self._close_mcp_session(**e) for e in temp_sessions)
                )
    
    async def close_all(self):
        """
        Close all open sessions.
        """
        if self.sessions:
            await asyncio.gather(
                *(self._close_mcp_session(**e) for e in self.sessions)
            )
            self.sessions = None
async def main():
        server_params_list = [
           StdioServerParameters(command="uv", args=["run", "/oper/work/endian/intelligent_agent/mcp/mcp_server/private_tools/chromadb_mcp.py",]),
        ]
        manager = MCPClientManager(server_params_list)
        descriptions, _ = await manager.initialize()
        print("可用工具:", descriptions)
asyncio.run(main())
