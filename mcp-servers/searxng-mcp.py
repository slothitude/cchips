#!/usr/bin/env python3
"""
SearXNG MCP Server - Provides search capabilities via local SearXNG instance
"""

import json
import urllib.request
import urllib.parse
from typing import Any

# Simple MCP-like server for SearXNG
SEARXNG_URL = "http://localhost:8888"

def search(query: str, format: str = "json", engines: str = None) -> dict:
    """Search using SearXNG"""
    params = {"q": query, "format": format}
    if engines:
        params["engines"] = engines

    url = f"{SEARXNG_URL}/search?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e), "results": []}


def main():
    """Main entry point for MCP server"""
    import sys

    # Read JSON-RPC messages from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            response = {"jsonrpc": "2.0", "id": request_id}

            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "searxng-mcp",
                        "version": "1.0.0"
                    }
                }
            elif method == "tools/list":
                response["result"] = {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search the web using SearXNG",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query"
                                    },
                                    "engines": {
                                        "type": "string",
                                        "description": "Comma-separated list of engines (optional)"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    ]
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if tool_name == "search":
                    query = tool_args.get("query", "")
                    engines = tool_args.get("engines")
                    result = search(query, engines=engines)
                    response["result"] = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                else:
                    response["error"] = {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            else:
                response["error"] = {"code": -32601, "message": f"Unknown method: {method}"}

            print(json.dumps(response))
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
