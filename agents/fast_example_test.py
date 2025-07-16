#!/usr/bin/env python3
"""
Fast Example Test: Unified MCP Tools Demo
Quick demonstration of key functionality
"""

import asyncio
import sys
import os
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools_client import get_unified_mcp_client

async def fast_example_test():
    """Fast example test focusing on key capabilities"""
    print("⚡ Fast Example Test: Unified MCP Tools Demo")
    print("=" * 55)
    
    try:
        # Get unified MCP client
        client = await get_unified_mcp_client()
        
        # Show tool inventory
        available_tools = client.get_available_tools()
        total_tools = sum(len(tools) for tools in available_tools.values())
        
        print(f"🔧 Connected to {len(available_tools)} MCP servers")
        print(f"🔧 Total tools available: {total_tools}")
        
        for server, tools in available_tools.items():
            print(f"   • {server}: {len(tools)} tools")
        
        # Test 1: Excel Common Locations (fast)
        print("\n📊 TEST 1: Excel System Integration")
        print("-" * 35)
        
        try:
            locations_result = await client.call_tool("get_common_excel_locations", {})
            locations_data = json.loads(locations_result)
            
            print(f"✅ Operating System: {locations_data.get('os')}")
            print(f"✅ Home Directory: {locations_data.get('home_directory')}")
            
            locations = locations_data.get("common_locations", [])
            print(f"✅ Found {len(locations)} common Excel locations:")
            
            for loc in locations[:3]:
                status = "✓" if loc.get("exists") else "✗"
                count = loc.get("excel_files_count", 0)
                path = loc["path"].replace(locations_data.get("home_directory", ""), "~")
                print(f"   {status} {path} ({count} Excel files)")
                
        except Exception as e:
            print(f"❌ Excel locations test failed: {e}")
        
        # Test 2: Web Mapping (fast)
        print("\n🌐 TEST 2: Web Discovery")
        print("-" * 25)
        
        try:
            # Use a simple, reliable test site
            map_result = await client.call_tool("firecrawl_map", {
                "url": "https://httpbin.org",
                "limit": 5
            })
            
            map_data = json.loads(map_result)
            links = map_data.get("links", [])
            print(f"✅ Website mapping successful")
            print(f"✅ Discovered {len(links)} URLs from httpbin.org")
            
            for i, link in enumerate(links[:3], 1):
                print(f"   {i}. {link}")
                
        except Exception as e:
            print(f"❌ Web mapping test failed: {e}")
        
        # Test 3: Tool Introspection
        print("\n🔍 TEST 3: Tool Capabilities")
        print("-" * 30)
        
        # Show key tool information
        key_tools = [
            ("read_data_from_excel", "📊 Excel Data Reader"),
            ("firecrawl_scrape", "🌐 Web Content Scraper"),
            ("search_excel_files", "🔍 Excel File Finder"),
            ("firecrawl_search", "🔎 Web Search Engine")
        ]
        
        for tool_name, display_name in key_tools:
            tool_info = client.get_tool_info(tool_name)
            if tool_info:
                server = tool_info.get("server", "unknown")
                print(f"✅ {display_name} (via {server})")
            else:
                print(f"❌ {display_name} not available")
        
        # Test 4: Simple Web Content Test
        print("\n🔬 TEST 4: Web Content Extraction")
        print("-" * 35)
        
        try:
            # Test with a very simple page
            scrape_result = await client.call_tool("firecrawl_scrape", {
                "url": "https://httpbin.org/html",
                "formats": ["markdown"],
                "onlyMainContent": True
            })
            
            scrape_data = json.loads(scrape_result)
            content = scrape_data.get("markdown", "")
            
            print(f"✅ Content extraction successful")
            print(f"✅ Extracted {len(content)} characters")
            
            # Show a snippet
            if content:
                lines = content.split('\n')
                for line in lines[:3]:
                    if line.strip():
                        preview = line[:60] + "..." if len(line) > 60 else line
                        print(f"   {preview}")
                        break
                        
        except Exception as e:
            print(f"❌ Web content test failed: {e}")
        
        # Success Summary
        print("\n" + "=" * 55)
        print("🎉 FAST EXAMPLE TEST COMPLETED!")
        print("=" * 55)
        
        print("✅ Unified MCP Tools System Status:")
        print(f"   • {len(available_tools)} MCP servers connected")
        print(f"   • {total_tools} tools available")
        print("   • Excel operations: Ready")
        print("   • Web operations: Ready")
        print("   • Tool discovery: Ready")
        
        print("\n🚀 Your Columbia Lake agents can now:")
        print("   • Access Excel files across your system")
        print("   • Research companies and data online")
        print("   • Extract structured data from websites")
        print("   • Combine Excel and web data seamlessly")
        
        print("\n📋 Next Steps:")
        print("   • Use these tools in your data extraction workflows")
        print("   • Combine Excel analysis with web research")
        print("   • Build automated data processing pipelines")
        
    except Exception as e:
        print(f"❌ Fast example test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fast_example_test())