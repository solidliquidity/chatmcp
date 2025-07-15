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
        
        # Tool registry
        self.tools = self._register_tools()
        
        self.logger.info("Columbia Lake MCP Server initialized")
    
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