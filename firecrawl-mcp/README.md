# Firecrawl MCP Setup

This directory contains the Firecrawl Model Context Protocol (MCP) server setup.

## Setup

1. **Install dependencies** (already done globally):
   ```bash
   npm install -g firecrawl-mcp
   ```

2. **Configure API key**:
   - Update `.env` file with your Firecrawl API key
   - Replace `fc-YOUR_API_KEY_HERE` with your actual API key

3. **Run the MCP server**:
   ```bash
   env FIRECRAWL_API_KEY=fc-YOUR_API_KEY npx firecrawl-mcp
   ```

## Available Tools

- **Scrape**: Extract content from single/multiple URLs
- **Crawl**: Crawl entire websites
- **Search**: Perform web searches
- **Batch operations**: Handle multiple URLs efficiently
- **Deep research**: Advanced content extraction

## Configuration Files

- `.env`: Environment variables for API keys and settings
- `mcp-config.json`: MCP server configuration for Claude Desktop or other clients

## Usage with Claude Desktop

Add the server configuration to your Claude Desktop config file to use Firecrawl tools directly in Claude conversations.