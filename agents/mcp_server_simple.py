"""
Simple MCP Server for Columbia Lake Partners Agents
Test version without complex dependencies
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

class SimpleMCPServer:
    """Simple MCP Server for testing"""
    
    def __init__(self):
        self.tools = {
            "test_connection": {
                "name": "test_connection",
                "description": "Test the connection to Columbia Lake Partners agents",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_company_status": {
                "name": "get_company_status",
                "description": "Get status of all companies in the portfolio",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "process_excel_mock": {
                "name": "process_excel_mock",
                "description": "Mock Excel processing for testing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Excel file"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }
        
        print("Columbia Lake MCP Server initialized successfully", file=sys.stderr)
    
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
            
            # Execute the tool
            result = await self._execute_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self._create_error_response(request_id, str(e))
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return results"""
        
        if tool_name == "test_connection":
            return "✅ Connection to Columbia Lake Partners agents is working!\n\nAvailable services:\n- Data extraction from Excel files\n- Automated follow-up emails\n- Company health monitoring\n- Alert dashboard"
        
        elif tool_name == "get_company_status":
            # Mock company data
            companies = [
                {"name": "TechCorp Inc", "status": "active", "health_score": 85},
                {"name": "StartupXYZ", "status": "active", "health_score": 72},
                {"name": "OldCorp Ltd", "status": "failing", "health_score": 45}
            ]
            
            result = "📊 Company Portfolio Status:\n\n"
            for company in companies:
                status_emoji = "🟢" if company["status"] == "active" else "🔴"
                result += f"{status_emoji} {company['name']}: {company['status']} (Health: {company['health_score']}%)\n"
            
            return result
        
        elif tool_name == "process_excel_mock":
            file_path = arguments.get("file_path", "unknown.xlsx")
            return f"✅ Mock Excel processing completed!\n\nFile: {file_path}\nProcessed: 15 companies\nSuccess rate: 100%\n\nNext steps:\n- Data stored in database\n- Health scores calculated\n- Follow-up actions identified"
        
        else:
            return f"❌ Tool {tool_name} not implemented yet"
    
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
                    error_response = self._create_error_response(
                        None, f"Invalid JSON: {str(e)}"
                    )
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                    
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Server error: {str(e)}", file=sys.stderr)

async def main():
    """Main entry point"""
    server = SimpleMCPServer()
    await server.run_server()

if __name__ == "__main__":
    asyncio.run(main())