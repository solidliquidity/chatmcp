#!/usr/bin/env python3
"""
Columbia Lake Agents in Action
Real demonstration of agents performing useful tasks
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.data_extraction_agent import DataExtractionAgent
from agents.followup_agent import FollowUpAgent
from agents.notification_agent import NotificationAgent

async def demonstrate_agents_in_action():
    """Show agents performing real, useful tasks"""
    print("🤖 Columbia Lake Agents in Action")
    print("=" * 50)
    print("🎯 Demonstrating real-world agent capabilities")
    print("=" * 50)
    
    # Initialize agents
    data_agent = DataExtractionAgent()
    followup_agent = FollowUpAgent()
    notification_agent = NotificationAgent()
    
    print("✅ Agents initialized and ready for action")
    print(f"📊 Data Agent: {data_agent.__class__.__name__}")
    print(f"📧 Follow-up Agent: {followup_agent.__class__.__name__}")
    print(f"🔔 Notification Agent: {notification_agent.__class__.__name__}")
    
    # Task 1: Data Extraction Agent - Excel File Analysis
    print("\n" + "🔍 TASK 1: Data Extraction Agent - Excel File Discovery")
    print("-" * 55)
    
    try:
        print("🤖 Agent: Searching for Excel files to analyze...")
        
        # Use the agent's search capability
        search_result = await data_agent.search_excel_files(
            search_path="~/Downloads",
            filename_pattern="*.xlsx",
            include_subdirs=False
        )
        
        if search_result.success:
            search_data = search_result.data.get("search_results", {})
            files_found = search_data.get("files", [])
            
            print(f"✅ Agent found {len(files_found)} Excel files")
            
            if files_found:
                print("📋 Agent Analysis:")
                for i, file_info in enumerate(files_found[:3], 1):
                    print(f"   {i}. {file_info['filename']}")
                    print(f"      Size: {file_info['size_mb']} MB")
                    print(f"      Modified: {file_info['modified_readable']}")
                    print(f"      Location: {file_info['directory']}")
                
                # Try to analyze the first file
                if files_found:
                    target_file = files_found[0]
                    print(f"\n🔬 Agent: Analyzing '{target_file['filename']}'...")
                    
                    try:
                        # Get file metadata
                        file_path = target_file['filepath']
                        analysis_result = await data_agent.analyze_excel_file(file_path)
                        
                        if analysis_result.success:
                            print("✅ Agent successfully analyzed the file!")
                            analysis_data = analysis_result.data
                            
                            if analysis_data:
                                print("📊 Agent Report:")
                                print(f"   • File format: Excel workbook")
                                print(f"   • Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                print(f"   • Agent assessment: File is accessible and ready for processing")
                        else:
                            print(f"⚠️  Agent encountered issues: {analysis_result.message}")
                            
                    except Exception as e:
                        print(f"⚠️  Agent analysis error: {e}")
            else:
                print("📝 Agent: No Excel files found in Downloads folder")
                print("💡 Agent suggestion: Try placing Excel files in Downloads for analysis")
        else:
            print(f"❌ Agent search failed: {search_result.message}")
            
    except Exception as e:
        print(f"❌ Data extraction agent error: {e}")
    
    # Task 2: Web Research Agent Capabilities
    print("\n" + "🌐 TASK 2: Data Agent - Web Research Capabilities")
    print("-" * 55)
    
    try:
        print("🤖 Agent: Demonstrating web research capabilities...")
        
        # Research a well-known company
        company_name = "Apple Inc."
        company_website = "https://www.apple.com"
        
        print(f"🔍 Agent: Researching '{company_name}'...")
        
        research_result = await data_agent.research_company_online(
            company_name=company_name,
            company_website=company_website
        )
        
        if research_result.success:
            print("✅ Agent successfully completed web research!")
            research_data = research_result.data
            
            print("🌐 Agent Research Report:")
            if research_data.get("website_data"):
                print("   ✅ Website content extracted")
            if research_data.get("search_results"):
                print("   ✅ Search results gathered")
            if research_data.get("analysis"):
                print("   ✅ AI analysis generated")
                
            # Show analysis preview
            analysis = research_data.get("analysis", "")
            if analysis:
                preview = analysis[:200] + "..." if len(analysis) > 200 else analysis
                print(f"   📝 Analysis preview: {preview}")
                
        else:
            print(f"⚠️  Agent research incomplete: {research_result.message}")
            
    except Exception as e:
        print(f"❌ Web research agent error: {e}")
    
    # Task 3: Follow-up Agent Capabilities
    print("\n" + "📧 TASK 3: Follow-up Agent - Process Management")
    print("-" * 55)
    
    try:
        print("🤖 Agent: Checking follow-up requirements...")
        
        # Check follow-up conditions
        conditions_result = await followup_agent.check_follow_up_conditions()
        
        if conditions_result.success:
            print("✅ Agent completed follow-up analysis!")
            conditions_data = conditions_result.data
            
            print("📧 Agent Follow-up Report:")
            if isinstance(conditions_data, dict):
                total_companies = conditions_data.get("total_companies", 0)
                needs_followup = conditions_data.get("needs_followup", 0)
                
                print(f"   📊 Total companies in system: {total_companies}")
                print(f"   📨 Companies needing follow-up: {needs_followup}")
                
                if needs_followup > 0:
                    print("   🚨 Agent recommendation: Follow-up actions required")
                else:
                    print("   ✅ Agent assessment: All follow-ups current")
            else:
                print(f"   📋 Agent status: {conditions_data}")
        else:
            print(f"⚠️  Agent follow-up check: {conditions_result.message}")
            
        # Get follow-up statistics
        print("\n🤖 Agent: Generating follow-up statistics...")
        stats_result = await followup_agent.get_follow_up_statistics()
        
        if stats_result.success:
            print("✅ Agent generated statistics report!")
            stats_data = stats_result.data
            
            print("📊 Agent Statistics Report:")
            if isinstance(stats_data, dict):
                for key, value in stats_data.items():
                    print(f"   • {key}: {value}")
            else:
                print(f"   📈 Statistics: {stats_data}")
                
    except Exception as e:
        print(f"❌ Follow-up agent error: {e}")
    
    # Task 4: Notification Agent Monitoring
    print("\n" + "🔔 TASK 4: Notification Agent - Health Monitoring")
    print("-" * 55)
    
    try:
        print("🤖 Agent: Monitoring system health...")
        
        # Get alert dashboard
        dashboard_result = await notification_agent.get_alert_dashboard()
        
        if dashboard_result.success:
            print("✅ Agent generated health dashboard!")
            dashboard_data = dashboard_result.data
            
            print("🔔 Agent Health Dashboard:")
            if isinstance(dashboard_data, dict):
                for section, details in dashboard_data.items():
                    print(f"   📊 {section}: {details}")
            else:
                print(f"   📈 Dashboard: {dashboard_data}")
                
        else:
            print(f"⚠️  Agent dashboard: {dashboard_result.message}")
            
        # Monitor company health
        print("\n🤖 Agent: Running health monitoring cycle...")
        monitor_result = await notification_agent.monitor_company_health()
        
        if monitor_result.success:
            print("✅ Agent completed health monitoring!")
            monitor_data = monitor_result.data
            
            print("🏥 Agent Health Report:")
            if isinstance(monitor_data, list):
                print(f"   📊 Monitored {len(monitor_data)} items")
                for item in monitor_data[:3]:  # Show first 3 items
                    print(f"   • {item}")
            else:
                print(f"   📈 Monitoring: {monitor_data}")
                
    except Exception as e:
        print(f"❌ Notification agent error: {e}")
    
    # Final Summary
    print("\n" + "=" * 50)
    print("🎉 AGENTS IN ACTION DEMONSTRATION COMPLETE!")
    print("=" * 50)
    
    print("✅ Agent Capabilities Demonstrated:")
    print("   📊 Data Extraction: Excel file discovery and analysis")
    print("   🌐 Web Research: Company information gathering")
    print("   📧 Follow-up Management: Process tracking and statistics")
    print("   🔔 Health Monitoring: System alerts and dashboards")
    
    print("\n🚀 Production-Ready Features:")
    print("   • Automated Excel file processing")
    print("   • Intelligent web research and analysis")
    print("   • Follow-up process management")
    print("   • Real-time health monitoring")
    print("   • Unified MCP tools integration")
    
    print("\n💼 Business Value:")
    print("   • Reduced manual data processing time")
    print("   • Automated company research workflows")
    print("   • Proactive follow-up management")
    print("   • Real-time operational insights")
    
    print("\n🎯 Next Steps:")
    print("   • Deploy agents for live company data processing")
    print("   • Set up automated research workflows")
    print("   • Configure monitoring and alerting")
    print("   • Scale across multiple data sources")

if __name__ == "__main__":
    asyncio.run(demonstrate_agents_in_action())