# True Agentic MCP Integration

## Overview
Direct LLM integration with Firecrawl MCP server for autonomous web scraping and website cloning. No API layers - just natural language to tool execution.

## Setup
1. **Install Firecrawl MCP**: `npm install -g firecrawl-mcp`
2. **Configure API key**: Add your Firecrawl API key to `.env.local`
3. **Use natural language**: LLM automatically discovers and uses tools

## Architecture
- **MCP Client**: `lib/mcp/mcp-client.ts` - Direct MCP server communication
- **Tool Integration**: `app/api/chat/tools/route.ts` - LLM has direct access to MCP tools
- **Auto Discovery**: `lib/mcp/mcp-integration.ts` - Dynamic tool discovery and execution

## How It Works
1. **LLM discovers MCP tools** automatically when chat starts
2. **User gives natural language commands** 
3. **LLM chooses appropriate tools** based on context
4. **MCP tools execute directly** - no API translation needed
5. **Results integrated into conversation**

## Natural Language Examples
Just chat normally - the LLM will automatically use tools when needed:

**Website Cloning:**
- "Can you clone the documentation from docs.anthropic.com?"
- "Download all the pages from the React website"
- "I need to mirror example.com for analysis"

**Smart Scraping:**
- "What are the latest features on the OpenAI website?"
- "Get me the pricing information from Stripe's website"
- "Scrape the news from techcrunch.com"

**Web Research:**
- "Find information about the latest AI developments"
- "Research best practices for React performance"
- "What are companies saying about remote work policies?"

## Available Tools (Auto-Discovered)
The LLM automatically has access to:
- **firecrawl_scrape**: Single page content extraction
- **firecrawl_crawl**: Full website cloning with multiple pages
- **firecrawl_map**: Website structure discovery
- **firecrawl_search**: Web search with content extraction
- **firecrawl_extract**: Structured data extraction
- **firecrawl_deep_research**: AI-powered research analysis

## Testing
1. Set your `FIRECRAWL_API_KEY` in `.env.local`
2. Run `npm run dev`
3. Start a chat and ask to scrape/clone any website
4. LLM automatically uses appropriate tools

## True Agentic Behavior
- **No manual tool selection** - LLM decides what tools to use
- **Intelligent chaining** - Can use multiple tools in sequence
- **Context awareness** - Results inform next tool choices
- **Error handling** - Automatically retries with different approaches
- **Natural responses** - Tool results integrated seamlessly

## Future Extensions
- Add more MCP servers (email, database, etc.)
- Tool chaining for complex workflows
- Multi-step research capabilities
- Custom tool creation