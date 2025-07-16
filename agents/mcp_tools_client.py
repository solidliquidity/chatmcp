"""
Unified MCP Tools Client for Columbia Lake Agents
Provides access to ALL MCP tools from multiple servers
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
import logging

class UnifiedMCPToolsClient:
    """Client that connects to all available MCP servers and provides unified tool access"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.servers = {}
        self.tools_registry = {}
        self.is_initialized = False
        
        # Define MCP server configurations
        self.server_configs = {
            "excel-mcp": {
                "path": "../excel-mcp-server",
                "command": ["python", "-m", "excel_mcp", "stdio"],
                "description": "Excel manipulation tools"
            },
            "firecrawl": {
                "path": "../firecrawl-mcp", 
                "command": ["firecrawl-mcp"],
                "description": "Web scraping and crawling tools",
                "env": {
                    "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "fc-demo-key")
                }
            }
        }
    
    async def initialize(self):
        """Initialize connections to all MCP servers"""
        if self.is_initialized:
            return
        
        self.logger.info("Initializing unified MCP tools client...")
        
        # Connect to each server
        for server_name, config in self.server_configs.items():
            try:
                await self._connect_to_server(server_name, config)
            except Exception as e:
                self.logger.warning(f"Failed to connect to {server_name}: {str(e)}")
        
        # Discover all available tools
        await self._discover_all_tools()
        
        self.is_initialized = True
        total_tools = sum(len(tools) for tools in self.tools_registry.values())
        self.logger.info(f"Unified MCP client initialized with {total_tools} tools from {len(self.servers)} servers")
    
    async def _connect_to_server(self, server_name: str, config: Dict[str, Any]):
        """Connect to a specific MCP server"""
        try:
            server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config["path"])
            
            # Check if server path exists
            if not os.path.exists(server_path):
                self.logger.error(f"Server path does not exist: {server_path}")
                return
            
            self.logger.info(f"Starting {server_name} server at {server_path}")
            self.logger.info(f"Command: {' '.join(config['command'])}")
            
            # Prepare environment variables
            env = os.environ.copy()
            if "env" in config:
                env.update(config["env"])
            
            # Start the MCP server process
            process = subprocess.Popen(
                config["command"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                cwd=server_path,
                text=True,
                bufsize=0,
                env=env
            )
            
            # Wait a moment for server to start
            await asyncio.sleep(1)
            
            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {
                        "name": "columbia-lake-unified-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            process.stdin.write(json.dumps(init_request) + '\n')
            process.stdin.flush()
            
            # Read initialization response with timeout
            try:
                response = process.stdout.readline()
                if response:
                    response_data = json.loads(response.strip())
                    self.logger.info(f"Init response from {server_name}: {response_data}")
                    
                    if 'result' in response_data:
                        self.servers[server_name] = {
                            "process": process,
                            "config": config,
                            "request_id": 2,
                            "is_connected": True
                        }
                        self.logger.info(f"✅ Connected to {server_name}: {config['description']}")
                    else:
                        self.logger.error(f"❌ Failed to initialize {server_name}: {response_data}")
                        process.terminate()
                else:
                    self.logger.error(f"❌ No response from {server_name}")
                    process.terminate()
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ Invalid JSON from {server_name}: {e}")
                process.terminate()
            except Exception as e:
                self.logger.error(f"❌ Error reading from {server_name}: {e}")
                process.terminate()
        except Exception as e:
            self.logger.error(f"Error connecting to {server_name}: {str(e)}")
    
    async def _discover_all_tools(self):
        """Discover tools from all connected servers"""
        for server_name, server_info in self.servers.items():
            try:
                tools = await self._get_server_tools(server_name)
                if tools:
                    self.tools_registry[server_name] = tools
                    tool_names = [tool.get('name', 'unknown') for tool in tools]
                    self.logger.info(f"Discovered {len(tools)} tools from {server_name}: {tool_names[:5]}...")
                
            except Exception as e:
                self.logger.error(f"Failed to discover tools from {server_name}: {str(e)}")
    
    async def _get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get available tools from a specific server"""
        server_info = self.servers.get(server_name)
        if not server_info or not server_info["is_connected"]:
            return []
        
        try:
            # Send initialized notification first (required for Excel MCP)
            if server_name == "excel-mcp":
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                process = server_info["process"]
                process.stdin.write(json.dumps(initialized_notification) + '\n')
                process.stdin.flush()
                
                # Wait a moment for server to be ready
                await asyncio.sleep(0.5)
            
            # Send tools/list request
            request = {
                "jsonrpc": "2.0",
                "id": server_info["request_id"],
                "method": "tools/list",
                "params": {}
            }
            
            server_info["request_id"] += 1
            process = server_info["process"]
            
            self.logger.info(f"Requesting tools from {server_name}: {request}")
            
            process.stdin.write(json.dumps(request) + '\n')
            process.stdin.flush()
            
            # Read response
            response = process.stdout.readline()
            if response:
                response_data = json.loads(response.strip())
                self.logger.info(f"Tools response from {server_name}: {response_data}")
                
                if 'result' in response_data and 'tools' in response_data['result']:
                    return response_data['result']['tools']
                elif 'error' in response_data:
                    self.logger.error(f"Tools request error from {server_name}: {response_data['error']}")
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting tools from {server_name}: {str(e)}")
            return []
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Call any MCP tool by name"""
        if not self.is_initialized:
            await self.initialize()
        
        # Find which server has this tool
        server_name = self._find_tool_server(tool_name)
        if not server_name:
            raise Exception(f"Tool '{tool_name}' not found in any connected MCP server")
        
        return await self._call_server_tool(server_name, tool_name, args)
    
    def _find_tool_server(self, tool_name: str) -> Optional[str]:
        """Find which server contains the specified tool"""
        for server_name, tools in self.tools_registry.items():
            for tool in tools:
                if tool.get('name') == tool_name:
                    return server_name
        return None
    
    async def _call_server_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """Call a tool on a specific server"""
        server_info = self.servers.get(server_name)
        if not server_info or not server_info["is_connected"]:
            raise Exception(f"Server {server_name} not connected")
        
        try:
            # Prepare tool call request
            request = {
                "jsonrpc": "2.0",
                "id": server_info["request_id"],
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            }
            
            server_info["request_id"] += 1
            process = server_info["process"]
            
            # Send request
            process.stdin.write(json.dumps(request) + '\n')
            process.stdin.flush()
            
            # Read response
            response = process.stdout.readline()
            if response:
                response_data = json.loads(response.strip())
                if 'result' in response_data:
                    return response_data['result']['content'][0]['text']
                elif 'error' in response_data:
                    raise Exception(f"Tool call failed: {response_data['error']['message']}")
            
            raise Exception("No response received from MCP server")
            
        except Exception as e:
            self.logger.error(f"Error calling {tool_name} on {server_name}: {str(e)}")
            raise
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """Get all available tools organized by server"""
        available_tools = {}
        for server_name, tools in self.tools_registry.items():
            available_tools[server_name] = [tool.get('name', 'unknown') for tool in tools]
        return available_tools
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        for server_name, tools in self.tools_registry.items():
            for tool in tools:
                if tool.get('name') == tool_name:
                    return {
                        **tool,
                        "server": server_name,
                        "server_description": self.server_configs[server_name]["description"]
                    }
        return None
    
    async def cleanup(self):
        """Clean up all server connections"""
        for server_name, server_info in self.servers.items():
            try:
                if server_info.get("process"):
                    server_info["process"].terminate()
                    server_info["process"].wait()
            except Exception as e:
                self.logger.warning(f"Error cleaning up {server_name}: {str(e)}")
        
        self.servers.clear()
        self.tools_registry.clear()
        self.is_initialized = False

# Global instance for agents to use
unified_mcp_client = None

async def get_unified_mcp_client(logger: Optional[logging.Logger] = None) -> UnifiedMCPToolsClient:
    """Get the global unified MCP client instance"""
    global unified_mcp_client
    
    if unified_mcp_client is None:
        unified_mcp_client = UnifiedMCPToolsClient(logger)
        await unified_mcp_client.initialize()
    
    return unified_mcp_client

# Example usage
async def demo_all_tools():
    """Demo function showing how to use all available MCP tools"""
    client = await get_unified_mcp_client()
    
    print("Available MCP Tools:")
    available_tools = client.get_available_tools()
    for server, tools in available_tools.items():
        print(f"\n{server.upper()}:")
        for tool in tools:
            print(f"  - {tool}")
    
    # Example: Use Excel tools
    try:
        # Search for Excel files
        excel_search = await client.call_tool("search_excel_files", {
            "search_path": "~",
            "filename_pattern": "*.xlsx",
            "include_subdirs": True
        })
        print(f"\nExcel search result: {excel_search}")
        
        # Get workbook metadata
        workbook_info = await client.call_tool("get_workbook_metadata", {
            "filepath": "./sample.xlsx",
            "include_ranges": True
        })
        print(f"\nWorkbook info: {workbook_info}")
        
    except Exception as e:
        print(f"Excel tool demo failed: {e}")
    
    # Example: Use Firecrawl tools
    try:
        # Scrape a website
        scrape_result = await client.call_tool("firecrawl_scrape", {
            "url": "https://example.com",
            "formats": ["markdown"]
        })
        print(f"\nScrape result: {scrape_result[:200]}...")
        
    except Exception as e:
        print(f"Firecrawl tool demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(demo_all_tools())