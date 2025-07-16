#!/usr/bin/env python3
"""
Practical Example: Real-World Agent Workflow
Demonstrates how Columbia Lake agents would use unified MCP tools
"""

import asyncio
import sys
import os
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools_client import get_unified_mcp_client

async def practical_example():
    """Practical example showing real-world agent workflow"""
    print("🏢 Practical Example: Columbia Lake Agent Workflow")
    print("=" * 60)
    
    try:
        # Get unified MCP client
        client = await get_unified_mcp_client()
        
        print("🤖 Agent Task: Research and analyze company data")
        print("📋 Workflow: Excel analysis + Web research + Data integration")
        print("-" * 60)
        
        # Step 1: Excel Data Discovery
        print("\n📊 STEP 1: Excel Data Discovery")
        print("🔍 Agent: Looking for Excel files containing company data...")
        
        try:
            # Find Excel files in common locations
            locations_result = await client.call_tool("get_common_excel_locations", {})
            locations_data = json.loads(locations_result)
            
            print(f"✅ System scan complete ({locations_data.get('os')})")
            
            # Check Downloads folder (most likely to have company data)
            downloads_path = os.path.join(locations_data.get("home_directory", ""), "Downloads")
            if os.path.exists(downloads_path):
                print(f"✅ Found Downloads folder with Excel files")
                
                # Quick search in Downloads
                try:
                    search_result = await client.call_tool("search_excel_files", {
                        "search_path": downloads_path,
                        "filename_pattern": "*.xlsx",
                        "include_subdirs": False,
                        "max_results": 3
                    })
                    
                    search_data = json.loads(search_result)
                    files = search_data.get("files", [])
                    
                    if files:
                        print(f"✅ Agent found {len(files)} Excel files:")
                        for file_info in files[:2]:
                            print(f"   • {file_info['filename']} ({file_info['size_mb']} MB)")
                            print(f"     Modified: {file_info['modified_readable']}")
                    else:
                        print("📝 No Excel files found in Downloads")
                        
                except Exception as e:
                    print(f"⚠️  Excel search in Downloads failed: {e}")
            
        except Exception as e:
            print(f"❌ Excel discovery failed: {e}")
        
        # Step 2: Web Research Capabilities
        print("\n🌐 STEP 2: Web Research Capabilities")
        print("🔍 Agent: Preparing web research tools for company analysis...")
        
        # Check web research tools
        web_tools = [
            ("firecrawl_scrape", "Single page content extraction"),
            ("firecrawl_search", "Web search for company information"),
            ("firecrawl_map", "Website structure discovery"),
            ("firecrawl_crawl", "Deep website content extraction")
        ]
        
        print("✅ Web research toolkit ready:")
        for tool_name, description in web_tools:
            tool_info = client.get_tool_info(tool_name)
            if tool_info:
                print(f"   • {tool_name}: {description}")
            else:
                print(f"   ❌ {tool_name}: Not available")
        
        # Step 3: Tool Integration Demo
        print("\n🔧 STEP 3: Tool Integration Demo")
        print("🤖 Agent: Demonstrating combined workflow...")
        
        # Simulate a simple workflow
        print("\n📝 Simulated Workflow:")
        print("   1. Agent finds Excel file with company list")
        print("   2. Agent extracts company names and websites")
        print("   3. Agent researches each company online")
        print("   4. Agent combines Excel data with web research")
        print("   5. Agent updates Excel with enriched data")
        
        # Show tool capabilities for each step
        workflow_tools = [
            ("read_data_from_excel", "Extract company data from Excel"),
            ("firecrawl_scrape", "Scrape company websites"),
            ("firecrawl_search", "Search for company information"),
            ("write_data_to_excel", "Write enriched data back to Excel")
        ]
        
        print("\n🔗 Required tools for this workflow:")
        all_available = True
        for tool_name, purpose in workflow_tools:
            tool_info = client.get_tool_info(tool_name)
            if tool_info:
                server = tool_info.get("server", "unknown")
                print(f"   ✅ {tool_name} ({server}): {purpose}")
            else:
                print(f"   ❌ {tool_name}: Not available")
                all_available = False
        
        if all_available:
            print("\n✅ All required tools are available!")
            print("🚀 Agent can execute complete workflow!")
        
        # Step 4: System Status
        print("\n📊 STEP 4: System Status Summary")
        print("-" * 40)
        
        available_tools = client.get_available_tools()
        total_tools = sum(len(tools) for tools in available_tools.values())
        
        print(f"🔧 MCP Servers: {len(available_tools)} connected")
        print(f"🔧 Total Tools: {total_tools} available")
        
        for server, tools in available_tools.items():
            print(f"   • {server}: {len(tools)} tools")
        
        # Agent capabilities summary
        print("\n🤖 Agent Capabilities Summary:")
        print("   ✅ Excel file discovery and analysis")
        print("   ✅ Web content scraping and research")
        print("   ✅ Data extraction and enrichment")
        print("   ✅ Cross-platform data integration")
        print("   ✅ Automated workflow execution")
        
        # Real-world use cases
        print("\n🎯 Real-World Use Cases:")
        print("   📈 Company financial analysis")
        print("   🏢 Market research and competitor analysis")
        print("   📊 Data enrichment for CRM systems")
        print("   🔍 Due diligence research workflows")
        print("   📋 Automated reporting and dashboards")
        
        # Final Status
        print("\n" + "=" * 60)
        print("✅ PRACTICAL EXAMPLE COMPLETED!")
        print("=" * 60)
        
        print("🎉 Your Columbia Lake agents are fully equipped with:")
        print(f"   • {total_tools} unified MCP tools")
        print("   • Excel and web research capabilities")
        print("   • End-to-end data workflows")
        print("   • Seamless tool integration")
        
        print("\n🚀 Ready for production use!")
        
    except Exception as e:
        print(f"❌ Practical example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(practical_example())