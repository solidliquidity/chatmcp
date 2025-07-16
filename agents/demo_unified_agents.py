#!/usr/bin/env python3
"""
Demo script showing Columbia Lake agents with full MCP tools access
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.data_extraction_agent import DataExtractionAgent
from mcp_tools_client import get_unified_mcp_client

async def demo_all_mcp_tools():
    """Demonstrate access to all MCP tools"""
    print("🚀 Columbia Lake Agents - Unified MCP Tools Demo")
    print("=" * 60)
    
    # Get unified MCP client
    mcp_client = await get_unified_mcp_client()
    
    # Show all available tools
    print("\n📋 Available MCP Tools:")
    available_tools = mcp_client.get_available_tools()
    total_tools = 0
    
    for server, tools in available_tools.items():
        print(f"\n🔧 {server.upper()} ({len(tools)} tools):")
        for tool in tools[:10]:  # Show first 10 tools
            print(f"  ✓ {tool}")
        if len(tools) > 10:
            print(f"  ... and {len(tools) - 10} more")
        total_tools += len(tools)
    
    print(f"\n📊 Total: {total_tools} tools from {len(available_tools)} MCP servers")
    
    return mcp_client

async def demo_excel_operations():
    """Demo Excel operations with unified tools"""
    print("\n" + "=" * 60)
    print("📊 EXCEL OPERATIONS DEMO")
    print("=" * 60)
    
    agent = DataExtractionAgent()
    
    try:
        # Search for Excel files
        print("\n🔍 Searching for Excel files...")
        search_result = await agent.search_excel_files(
            search_path="~",
            filename_pattern="*.xlsx",
            include_subdirs=True
        )
        
        if search_result.success:
            print("✅ Excel file search completed")
            files_found = search_result.data.get("search_results", {}).get("total_found", 0)
            print(f"   Found {files_found} Excel files")
        else:
            print("❌ Excel file search failed")
            print(f"   Error: {search_result.message}")
    
    except Exception as e:
        print(f"❌ Excel demo failed: {str(e)}")

async def demo_web_research():
    """Demo web research capabilities"""
    print("\n" + "=" * 60)
    print("🌐 WEB RESEARCH DEMO") 
    print("=" * 60)
    
    agent = DataExtractionAgent()
    
    try:
        # Research a company online
        print("\n🔍 Researching Apple Inc. online...")
        research_result = await agent.research_company_online(
            company_name="Apple Inc.",
            company_website="https://www.apple.com"
        )
        
        if research_result.success:
            print("✅ Web research completed")
            data = research_result.data
            if data.get("website_data"):
                print("   ✓ Website scraped successfully")
            if data.get("search_results"):
                print("   ✓ Search results gathered")
            if data.get("analysis"):
                print("   ✓ AI analysis generated")
                # Show first 200 chars of analysis
                analysis_preview = data["analysis"][:200] + "..."
                print(f"   Analysis preview: {analysis_preview}")
        else:
            print("❌ Web research failed")
            print(f"   Error: {research_result.message}")
    
    except Exception as e:
        print(f"❌ Web research demo failed: {str(e)}")

async def demo_tool_info():
    """Demo getting detailed tool information"""
    print("\n" + "=" * 60)
    print("ℹ️  TOOL INFORMATION DEMO")
    print("=" * 60)
    
    mcp_client = await get_unified_mcp_client()
    
    # Show info for specific tools
    interesting_tools = [
        "get_workbook_metadata",
        "read_data_from_excel", 
        "firecrawl_scrape",
        "firecrawl_search"
    ]
    
    for tool_name in interesting_tools:
        tool_info = mcp_client.get_tool_info(tool_name)
        if tool_info:
            print(f"\n🔧 {tool_name}")
            print(f"   Server: {tool_info.get('server')}")
            print(f"   Description: {tool_info.get('description', 'No description')}")
            print(f"   Server Type: {tool_info.get('server_description')}")
        else:
            print(f"\n❌ Tool '{tool_name}' not found")

async def main():
    """Main demo function"""
    try:
        # Initialize and show all available tools
        await demo_all_mcp_tools()
        
        # Demo Excel operations
        await demo_excel_operations()
        
        # Demo web research capabilities  
        await demo_web_research()
        
        # Show detailed tool information
        await demo_tool_info()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("Your agents now have access to ALL MCP tools!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())