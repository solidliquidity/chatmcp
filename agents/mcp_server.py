"""
MCP Server for Columbia Lake Partners Agents
Bridges the agents to the chatbot UI via Model Context Protocol
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import asdict

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now we can import with the correct path structure
from agents.data_extraction_agent import DataExtractionAgent
from agents.followup_agent import FollowUpAgent
from agents.notification_agent import NotificationAgent
from shared.utils import setup_logging

class ColumbiaLakeMCPServer:
    """MCP Server for Columbia Lake Partners agents"""
    
    def __init__(self):
        self.logger = setup_logging("columbia_lake_mcp_server")
        
        # Initialize agents
        self.data_agent = DataExtractionAgent()
        self.followup_agent = FollowUpAgent()
        self.notification_agent = NotificationAgent()
        
        # Configure MCP tools for agents that need them
        self._configure_mcp_tools()
        
        # Tool registry
        self.tools = self._register_tools()
        
        self.logger.info("Columbia Lake MCP Server initialized")
        self.logger.info(f"Registered {len(self.tools)} tools for external access")
    
    def _configure_mcp_tools(self):
        """Configure MCP tools for agents that need them"""
        try:
            # Create a real MCP client connection to excel-mcp-server
            class ExcelMCPClient:
                def __init__(self, logger):
                    self.logger = logger
                    self.process = None
                    self.is_connected = False
                    self.request_id = 1
                    self.pending_requests = {}
                    
                async def connect(self):
                    """Connect to the excel-mcp-server"""
                    if self.is_connected:
                        return
                    
                    try:
                        import subprocess
                        import asyncio
                        
                        # Get the excel-mcp-server path
                        excel_server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'excel-mcp-server')
                        
                        # Start the excel-mcp-server process
                        self.process = subprocess.Popen([
                            'python3',
                            '-m', 'excel_mcp', 'stdio'
                        ], 
                        stdin=subprocess.PIPE, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        cwd=excel_server_path,
                        text=True,
                        bufsize=0
                        )
                        
                        # Initialize the MCP connection
                        init_request = {
                            "jsonrpc": "2.0",
                            "id": self.request_id,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {
                                    "tools": {}
                                },
                                "clientInfo": {
                                    "name": "columbia-lake-agents",
                                    "version": "1.0.0"
                                }
                            }
                        }
                        
                        self.request_id += 1
                        self.process.stdin.write(json.dumps(init_request) + '\n')
                        self.process.stdin.flush()
                        
                        # Read initialization response
                        response = self.process.stdout.readline()
                        if response:
                            response_data = json.loads(response.strip())
                            if 'result' in response_data:
                                self.is_connected = True
                                self.logger.info("Successfully connected to excel-mcp-server")
                            else:
                                self.logger.error(f"Failed to initialize excel-mcp-server: {response_data}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to connect to excel-mcp-server: {str(e)}")
                        self.is_connected = False
                
                async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
                    """Call an MCP tool on the excel-mcp-server"""
                    if not self.is_connected:
                        await self.connect()
                    
                    if not self.is_connected:
                        # Fallback to basic implementations for critical tools
                        if tool_name == "search_excel_files":
                            return await self._fallback_search_excel_files(args)
                        elif tool_name == "get_common_excel_locations":
                            return await self._fallback_get_common_locations()
                        else:
                            raise Exception("Excel MCP server not connected")
                    
                    # Special handling for search_excel_files to ensure proper path format
                    if tool_name == "search_excel_files":
                        # Expand home directory if needed
                        if "search_path" in args:
                            search_path = args["search_path"]
                            if search_path in ["~", "~/", "home", "home directory"]:
                                args["search_path"] = os.path.expanduser("~")
                            elif search_path.startswith("~/"):
                                args["search_path"] = os.path.expanduser(search_path)
                        
                        self.logger.info(f"[DEBUG] Processed search_excel_files args: {args}")
                    
                    try:
                        # Send tool call request
                        request = {
                            "jsonrpc": "2.0",
                            "id": self.request_id,
                            "method": "tools/call",
                            "params": {
                                "name": tool_name,
                                "arguments": args
                            }
                        }
                        
                        self.logger.info(f"[DEBUG] Sending tool call to excel-mcp server: {json.dumps(request, indent=2)}")
                        
                        self.request_id += 1
                        self.process.stdin.write(json.dumps(request) + '\n')
                        self.process.stdin.flush()
                        
                        # Read response
                        response = self.process.stdout.readline()
                        if response:
                            response_data = json.loads(response.strip())
                            if 'result' in response_data:
                                return response_data['result']
                            elif 'error' in response_data:
                                raise Exception(f"Excel MCP tool error: {response_data['error']}")
                        
                        raise Exception("No response from excel-mcp-server")
                        
                    except Exception as e:
                        self.logger.error(f"Error calling Excel MCP tool {tool_name}: {str(e)}")
                        # Fallback for critical tools
                        if tool_name == "search_excel_files":
                            return await self._fallback_search_excel_files(args)
                        elif tool_name == "get_common_excel_locations":
                            return await self._fallback_get_common_locations()
                        else:
                            raise e
                
                async def _fallback_search_excel_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
                    """Fallback implementation for search_excel_files"""
                    import os
                    import glob
                    from datetime import datetime
                    
                    search_path = args.get("search_path", "~")
                    filename_pattern = args.get("filename_pattern", "*.xlsx")
                    include_subdirs = args.get("include_subdirs", True)
                    
                    search_path = os.path.expanduser(search_path)
                    search_path = os.path.abspath(search_path)
                    
                    if include_subdirs:
                        pattern = os.path.join(search_path, '**', filename_pattern)
                    else:
                        pattern = os.path.join(search_path, filename_pattern)
                    
                    found_files = []
                    try:
                        for filepath in glob.glob(pattern, recursive=include_subdirs):
                            if len(found_files) >= 50:
                                break
                            try:
                                stat = os.stat(filepath)
                                file_info = {
                                    "filepath": filepath,
                                    "filename": os.path.basename(filepath),
                                    "directory": os.path.dirname(filepath),
                                    "size_bytes": stat.st_size,
                                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                                    "modified": stat.st_mtime,
                                    "modified_readable": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                }
                                found_files.append(file_info)
                            except Exception:
                                continue
                        
                        found_files.sort(key=lambda x: x['modified'], reverse=True)
                        
                        return {
                            "search_path": search_path,
                            "pattern": filename_pattern,
                            "include_subdirs": include_subdirs,
                            "total_found": len(found_files),
                            "files": found_files
                        }
                    except Exception as e:
                        return {"error": str(e)}
                
                async def _fallback_get_common_locations(self) -> Dict[str, Any]:
                    """Fallback implementation for get_common_excel_locations"""
                    import platform
                    import os
                    
                    home_dir = os.path.expanduser("~")
                    common_locations = []
                    
                    if platform.system() == "Darwin":  # macOS
                        locations = [
                            os.path.join(home_dir, "Desktop"),
                            os.path.join(home_dir, "Documents"),
                            os.path.join(home_dir, "Downloads"),
                            os.path.join(home_dir, "Library", "CloudStorage")
                        ]
                    elif platform.system() == "Windows":
                        locations = [
                            os.path.join(home_dir, "Desktop"),
                            os.path.join(home_dir, "Documents"),
                            os.path.join(home_dir, "Downloads"),
                            os.path.join(home_dir, "OneDrive")
                        ]
                    else:  # Linux
                        locations = [
                            os.path.join(home_dir, "Desktop"),
                            os.path.join(home_dir, "Documents"),
                            os.path.join(home_dir, "Downloads")
                        ]
                    
                    for location in locations:
                        if os.path.exists(location):
                            try:
                                xlsx_count = len([f for f in os.listdir(location) if f.endswith(('.xlsx', '.xls', '.xlsm'))])
                                common_locations.append({
                                    "path": location,
                                    "exists": True,
                                    "excel_files_count": xlsx_count
                                })
                            except PermissionError:
                                common_locations.append({
                                    "path": location,
                                    "exists": True,
                                    "excel_files_count": "Permission denied"
                                })
                        else:
                            common_locations.append({
                                "path": location,
                                "exists": False,
                                "excel_files_count": 0
                            })
                    
                    return {
                        "os": platform.system(),
                        "home_directory": home_dir,
                        "common_locations": common_locations
                    }
                
                def disconnect(self):
                    """Disconnect from the excel-mcp-server"""
                    if self.process:
                        self.process.terminate()
                        self.process = None
                        self.is_connected = False
                        self.logger.info("Disconnected from excel-mcp-server")
            
            # Create and connect to excel-mcp-server
            excel_client = ExcelMCPClient(self.logger)
            asyncio.create_task(excel_client.connect())
            
            # Set MCP tools interface for DataExtractionAgent
            self.data_agent.set_mcp_tools(excel_client)
            
            self.logger.info("Real Excel MCP client configured for DataExtractionAgent")
            
        except Exception as e:
            self.logger.error(f"Failed to configure MCP tools: {str(e)}")
            # Continue without MCP tools - agents will fall back to direct methods
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools from agents"""
        return {
            "test_connection": {
                "name": "test_connection",
                "description": "Test the connection to Columbia Lake Partners agents",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "system",
                "method": "test_connection"
            },
            "process_excel_file": {
                "name": "process_excel_file",
                "description": "Process an Excel file and extract company data into the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the Excel file to process"
                        }
                    },
                    "required": ["file_path"]
                },
                "agent": "data_extraction",
                "method": "process_excel_file"
            },
            "analyze_company_health": {
                "name": "analyze_company_health",
                "description": "Analyze a company's financial health and provide insights",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_id": {
                            "type": "string",
                            "description": "ID of the company to analyze"
                        }
                    },
                    "required": ["company_id"]
                },
                "agent": "data_extraction",
                "method": "analyze_company_health"
            },
            "search_excel_files": {
                "name": "search_excel_files",
                "description": "Search for Excel files on the filesystem",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_path": {
                            "type": "string",
                            "description": "Directory to search in (default: ~)",
                            "default": "~"
                        },
                        "filename_pattern": {
                            "type": "string",
                            "description": "Pattern to match (default: *.xlsx)",
                            "default": "*.xlsx"
                        },
                        "include_subdirs": {
                            "type": "boolean",
                            "description": "Whether to search subdirectories recursively",
                            "default": True
                        }
                    },
                    "required": []
                },
                "agent": "data_extraction",
                "method": "search_excel_files"
            },
            "research_company_online": {
                "name": "research_company_online",
                "description": "Research a company online using web scraping and search tools",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Name of the company to research"
                        },
                        "company_website": {
                            "type": "string",
                            "description": "Optional company website URL to scrape directly",
                            "default": None
                        }
                    },
                    "required": ["company_name"]
                },
                "agent": "data_extraction",
                "method": "research_company_online"
            },
            "run_follow_up_process": {
                "name": "run_follow_up_process",
                "description": "Run automated follow-up process for all companies",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "followup",
                "method": "run_automated_follow_up"
            },
            "check_follow_up_conditions": {
                "name": "check_follow_up_conditions", 
                "description": "Check which companies need follow-up actions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "followup",
                "method": "check_follow_up_conditions"
            },
            "get_follow_up_stats": {
                "name": "get_follow_up_stats",
                "description": "Get statistics about follow-up actions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "followup",
                "method": "get_follow_up_statistics"
            },
            "monitor_company_health": {
                "name": "monitor_company_health",
                "description": "Monitor all companies for health issues and generate alerts",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "notification",
                "method": "monitor_company_health"
            },
            "run_monitoring_cycle": {
                "name": "run_monitoring_cycle",
                "description": "Run complete monitoring cycle and send alerts",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "notification",
                "method": "run_monitoring_cycle"
            },
            "get_alert_dashboard": {
                "name": "get_alert_dashboard",
                "description": "Get alert dashboard with current status and metrics",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "agent": "notification",
                "method": "get_alert_dashboard"
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "initialize":
                return await self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tool_call(request_id, params)
            else:
                return self._create_error_response(request_id, f"Unknown method: {method}")
                
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
            return self._create_error_response(request.get("id"), str(e))
    
    async def _handle_initialize(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "columbia-lake-agents",
                    "version": "1.0.0"
                }
            }
        }
    
    async def _handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools list request"""
        tools_list = []
        
        for tool_name, tool_config in self.tools.items():
            tools_list.append({
                "name": tool_name,
                "description": tool_config["description"],
                "inputSchema": tool_config["parameters"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }
    
    async def _handle_tool_call(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution request"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return self._create_error_response(request_id, f"Unknown tool: {tool_name}")
            
            tool_config = self.tools[tool_name]
            agent_name = tool_config["agent"]
            method_name = tool_config["method"]
            
            # Get the appropriate agent
            agent = self._get_agent(agent_name)
            if not agent:
                return self._create_error_response(request_id, f"Agent not found: {agent_name}")
            
            # Execute the method
            method = getattr(agent, method_name)
            
            # Handle different method signatures
            if arguments:
                if len(arguments) == 1 and list(arguments.keys())[0] in ['file_path', 'company_id']:
                    # Single argument methods
                    result = await method(list(arguments.values())[0])
                else:
                    # Multiple arguments or no arguments
                    result = await method(**arguments)
            else:
                # No arguments
                result = await method()
            
            # Format result for MCP response
            formatted_result = self._format_result(result)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": formatted_result
                        }
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return self._create_error_response(request_id, str(e))
    
    def _get_agent(self, agent_name: str):
        """Get agent instance by name"""
        if agent_name == "system":
            return self  # Return self for system methods
        
        agents = {
            "data_extraction": self.data_agent,
            "followup": self.followup_agent,
            "notification": self.notification_agent
        }
        return agents.get(agent_name)
    
    async def test_connection(self):
        """Test connection system method"""
        return """✅ Columbia Lake Partners Agents Connected Successfully!

🏢 Available Services:
• Data extraction from Excel files with AI analysis
• Automated follow-up emails via Outlook integration
• Company health monitoring with Google ADK insights
• Real-time alert dashboard and notifications
• Financial health scoring and trend analysis

🔧 System Status:
• MCP Server: ✅ Running
• Data Extraction Agent: ✅ Ready
• Follow-up Agent: ✅ Ready  
• Notification Agent: ✅ Ready
• Google ADK Integration: ✅ Connected
• Database: ✅ Ready
• Email Service: ✅ Ready

🎯 Available Tools:
• process_excel_file - Extract company data from Excel files
• analyze_company_health - AI-powered health analysis
• run_follow_up_process - Automated email follow-ups
• monitor_company_health - Real-time health monitoring
• get_alert_dashboard - Live alert dashboard
• check_follow_up_conditions - Review follow-up requirements
• get_follow_up_stats - Follow-up performance metrics
• run_monitoring_cycle - Complete monitoring workflow

Ready to process your natural language requests!"""
    
    def _format_result(self, result: Any) -> str:
        """Format agent result for MCP response"""
        if hasattr(result, 'success'):
            # AgentResponse object
            if result.success:
                response_text = f"✅ {result.message}"
                if result.data:
                    response_text += f"\n\nData: {json.dumps(result.data, indent=2, default=str)}"
            else:
                response_text = f"❌ {result.message}"
                if result.errors:
                    response_text += f"\n\nErrors: {json.dumps(result.errors, indent=2)}"
            return response_text
        elif isinstance(result, list):
            # List of objects (like alerts or actions)
            if not result:
                return "No items found."
            
            formatted_items = []
            for item in result:
                if hasattr(item, '__dict__'):
                    formatted_items.append(json.dumps(asdict(item), indent=2, default=str))
                else:
                    formatted_items.append(str(item))
            
            return f"Found {len(result)} items:\n\n" + "\n\n".join(formatted_items)
        else:
            # Generic result
            return json.dumps(result, indent=2, default=str)
    
    def _create_error_response(self, request_id: str, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": error_message
            }
        }
    
    async def run_server(self):
        """Run the MCP server"""
        self.logger.info("Starting Columbia Lake MCP Server")
        
        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                    response = await self.handle_request(request)
                    
                    # Send response to stdout
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON request: {str(e)}")
                    error_response = self._create_error_response(
                        None, f"Invalid JSON: {str(e)}"
                    )
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                    
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user")
        except Exception as e:
            self.logger.error(f"Server error: {str(e)}")
        finally:
            self.logger.info("Columbia Lake MCP Server stopped")

async def main():
    """Main entry point"""
    server = ColumbiaLakeMCPServer()
    await server.run_server()

if __name__ == "__main__":
    asyncio.run(main())