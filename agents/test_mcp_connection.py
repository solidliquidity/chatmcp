#!/usr/bin/env python3
"""
Test MCP server connections
"""

import asyncio
import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools_client import UnifiedMCPToolsClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_connections():
    """Test MCP server connections"""
    print("🔍 Testing MCP Server Connections")
    print("=" * 50)
    
    logger = logging.getLogger("test")
    client = UnifiedMCPToolsClient(logger)
    
    # Test Excel MCP server specifically
    print("\n📊 Testing Excel MCP Server...")
    excel_config = {
        "path": "../excel-mcp-server",
        "command": ["python", "-m", "excel_mcp", "stdio"],
        "description": "Excel manipulation tools"
    }
    
    try:
        await client._connect_to_server("excel-mcp", excel_config)
        
        if "excel-mcp" in client.servers:
            print("✅ Excel MCP server connected successfully!")
            
            # Test tool discovery
            tools = await client._get_server_tools("excel-mcp")
            print(f"✅ Found {len(tools)} Excel tools")
            
            # List first few tools
            for i, tool in enumerate(tools[:5]):
                print(f"   {i+1}. {tool.get('name', 'unknown')}")
            
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")
                
        else:
            print("❌ Excel MCP server failed to connect")
            
    except Exception as e:
        print(f"❌ Error testing Excel MCP: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Firecrawl MCP server
    print("\n🌐 Testing Firecrawl MCP Server...")
    firecrawl_config = {
        "path": "../firecrawl-mcp",
        "command": ["firecrawl-mcp"],
        "description": "Web scraping and crawling tools",
        "env": {
            "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "fc-demo-key")
        }
    }
    
    try:
        await client._connect_to_server("firecrawl", firecrawl_config)
        
        if "firecrawl" in client.servers:
            print("✅ Firecrawl MCP server connected successfully!")
            
            # Test tool discovery
            tools = await client._get_server_tools("firecrawl")
            print(f"✅ Found {len(tools)} Firecrawl tools")
            
            # List first few tools
            for i, tool in enumerate(tools[:5]):
                print(f"   {i+1}. {tool.get('name', 'unknown')}")
            
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")
                
        else:
            print("❌ Firecrawl MCP server failed to connect")
            
    except Exception as e:
        print(f"❌ Error testing Firecrawl MCP: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Connection Summary:")
    print(f"   Connected servers: {len(client.servers)}")
    for name, server in client.servers.items():
        print(f"   ✅ {name}: {server['config']['description']}")
    
    # Clean up
    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_connections())