"""
Entry point for Columbia Lake Partners MCP Server
"""

import asyncio
import sys
import os

# Add the parent directory to path so we can import mcp_server_simple
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server_simple import main

if __name__ == "__main__":
    asyncio.run(main())