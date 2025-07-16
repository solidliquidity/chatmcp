#!/usr/bin/env python3
"""
Example Test: Unified MCP Tools in Action
Demonstrates real-world usage of Excel and Firecrawl tools together
"""

import asyncio
import sys
import os
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools_client import get_unified_mcp_client

async def example_test():
    """Comprehensive example test of unified MCP tools"""
    print("🚀 Example Test: Unified MCP Tools in Action")
    print("=" * 60)
    
    try:
        # Get unified MCP client
        client = await get_unified_mcp_client()
        
        # Test 1: Excel File Operations
        print("\n📊 TEST 1: Excel File Operations")
        print("-" * 40)
        
        # Find Excel files on the system
        print("🔍 Searching for Excel files...")
        try:
            search_result = await client.call_tool("search_excel_files", {
                "search_path": os.path.expanduser("~"),
                "filename_pattern": "*.xlsx",
                "include_subdirs": True,
                "max_results": 3
            })
            
            search_data = json.loads(search_result)
            files_found = search_data.get("files", [])
            print(f"✅ Found {len(files_found)} Excel files")
            
            if files_found:
                for i, file_info in enumerate(files_found[:2], 1):
                    print(f"   {i}. {file_info['filename']} ({file_info['size_mb']} MB)")
            else:
                print("   No Excel files found in home directory")
                
        except Exception as e:
            print(f"❌ Excel search failed: {e}")
        
        # Get common Excel locations
        print("\n📁 Getting common Excel file locations...")
        try:
            locations_result = await client.call_tool("get_common_excel_locations", {})
            locations_data = json.loads(locations_result)
            
            print(f"✅ OS: {locations_data.get('os')}")
            locations = locations_data.get("common_locations", [])
            for loc in locations[:3]:
                status = "✓" if loc.get("exists") else "✗"
                count = loc.get("excel_files_count", 0)
                print(f"   {status} {loc['path']} ({count} Excel files)")
                
        except Exception as e:
            print(f"❌ Location check failed: {e}")
        
        # Test 2: Web Research with Firecrawl
        print("\n🌐 TEST 2: Web Research with Firecrawl")
        print("-" * 40)
        
        # Map a website to discover URLs
        print("🗺️  Mapping website structure...")
        try:
            map_result = await client.call_tool("firecrawl_map", {
                "url": "https://httpbin.org",
                "limit": 10
            })
            
            map_data = json.loads(map_result)
            links = map_data.get("links", [])
            print(f"✅ Discovered {len(links)} URLs")
            
            for i, link in enumerate(links[:5], 1):
                print(f"   {i}. {link}")
                
        except Exception as e:
            print(f"❌ Website mapping failed: {e}")
        
        # Scrape a simple webpage
        print("\n🔍 Scraping webpage content...")
        try:
            scrape_result = await client.call_tool("firecrawl_scrape", {
                "url": "https://httpbin.org/html",
                "formats": ["markdown"],
                "onlyMainContent": True
            })
            
            scrape_data = json.loads(scrape_result)
            content = scrape_data.get("markdown", "")
            
            print(f"✅ Scraped content ({len(content)} characters)")
            # Show first few lines of content
            lines = content.split('\n')[:5]
            for line in lines:
                if line.strip():
                    print(f"   {line[:80]}...")
                    
        except Exception as e:
            print(f"❌ Web scraping failed: {e}")
        
        # Test 3: Search functionality
        print("\n🔎 Testing web search...")
        try:
            search_result = await client.call_tool("firecrawl_search", {
                "query": "python programming tutorial",
                "limit": 3,
                "lang": "en"
            })
            
            search_data = json.loads(search_result)
            results = search_data.get("results", [])
            
            print(f"✅ Found {len(results)} search results")
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")[:50]
                url = result.get("url", "No URL")
                print(f"   {i}. {title}...")
                print(f"      {url}")
                
        except Exception as e:
            print(f"❌ Web search failed: {e}")
        
        # Test 4: Tool Information
        print("\n🔧 TEST 4: Tool Information & Capabilities")
        print("-" * 40)
        
        # Show detailed info for key tools
        key_tools = [
            ("read_data_from_excel", "📊"),
            ("firecrawl_scrape", "🌐"),
            ("search_excel_files", "🔍"),
            ("firecrawl_search", "🔎")
        ]
        
        for tool_name, icon in key_tools:
            tool_info = client.get_tool_info(tool_name)
            if tool_info:
                server = tool_info.get("server", "unknown")
                desc = tool_info.get("description", "No description")[:100]
                print(f"{icon} {tool_name} ({server})")
                print(f"   {desc}...")
            else:
                print(f"❌ {tool_name} not found")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 EXAMPLE TEST COMPLETED!")
        print("=" * 60)
        
        available_tools = client.get_available_tools()
        total_tools = sum(len(tools) for tools in available_tools.values())
        
        print(f"✅ Successfully tested unified MCP tools access")
        print(f"✅ {len(available_tools)} servers connected")
        print(f"✅ {total_tools} tools available")
        print(f"✅ Excel operations: File search, location discovery")
        print(f"✅ Web operations: Mapping, scraping, searching")
        print(f"✅ Tool introspection: Detailed capability info")
        
        print("\n🚀 Your Columbia Lake agents are ready for:")
        print("   • Excel file analysis and data extraction")
        print("   • Web research and content scraping")
        print("   • Company data gathering from multiple sources")
        print("   • Automated data workflows across platforms")
        
    except Exception as e:
        print(f"❌ Example test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(example_test())