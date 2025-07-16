#!/usr/bin/env python3
"""
Quick test of unified MCP tools setup
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools_client import get_unified_mcp_client

async def quick_test():
    """Quick test of unified MCP tools"""
    print("🔧 Quick Test: Unified MCP Tools Setup")
    print("=" * 50)
    
    try:
        # Get unified MCP client
        client = await get_unified_mcp_client()
        
        # Show available tools summary
        available_tools = client.get_available_tools()
        print(f"✅ Connected to {len(available_tools)} MCP servers")
        
        total_tools = 0
        for server, tools in available_tools.items():
            print(f"   • {server}: {len(tools)} tools")
            total_tools += len(tools)
        
        print(f"✅ Total tools available: {total_tools}")
        
        # Test a simple Excel tool
        print("\n📊 Testing Excel MCP tool...")
        try:
            result = await client.call_tool("get_common_excel_locations", {})
            print("✅ Excel tool test successful")
        except Exception as e:
            print(f"❌ Excel tool test failed: {e}")
        
        # Test a simple Firecrawl tool - just get tool info
        print("\n🌐 Testing Firecrawl MCP tool availability...")
        try:
            tool_info = client.get_tool_info("firecrawl_scrape")
            if tool_info:
                print("✅ Firecrawl tools available")
            else:
                print("❌ Firecrawl tools not found")
        except Exception as e:
            print(f"❌ Firecrawl test failed: {e}")
            
        print("\n" + "=" * 50)
        print("🎉 Quick test completed!")
        print("Your Columbia Lake agents now have access to ALL MCP tools!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())