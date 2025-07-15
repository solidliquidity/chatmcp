import asyncio
import typer

from .server import run_sse, run_stdio, run_streamable_http

app = typer.Typer(help="Excel MCP Server")

@app.command()
def sse():
    """Start Excel MCP Server in SSE mode"""
    print("Excel MCP Server - SSE mode")
    print("----------------------")
    print("Press Ctrl+C to exit")
    try:
        asyncio.run(run_sse())
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Service stopped.")

@app.command()
def streamable_http():
    """Start Excel MCP Server in streamable HTTP mode"""
    print("Excel MCP Server - Streamable HTTP mode")
    print("---------------------------------------")
    print("Press Ctrl+C to exit")
    try:
        asyncio.run(run_streamable_http())
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Service stopped.")

@app.command()
def stdio():
    """Start Excel MCP Server in stdio mode"""
    # Don't print to stdout in stdio mode - it's reserved for JSON-RPC
    try:
        run_stdio()
    except KeyboardInterrupt:
        # Log to stderr instead of stdout
        import sys
        print("Shutting down server...", file=sys.stderr)
    except Exception as e:
        import sys
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    finally:
        # Don't print anything in finally block for stdio mode
        pass

if __name__ == "__main__":
    app() 