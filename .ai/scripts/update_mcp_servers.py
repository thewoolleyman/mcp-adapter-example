#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict

def load_servers(servers_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Loads and validates all MCP server definitions from the specified directory."""
    servers = {}
    
    # Sort files for deterministic output
    for server_file in sorted(servers_dir.glob("*.json")):
        try:
            with open(server_file, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to load {server_file}: {e}")
            
        name = config.get("name")
        if not name:
            raise ValueError(f"Server definition in {server_file} is missing 'name' field")
            
        if name in servers:
            raise ValueError(f"Duplicate server name '{name}' found in {server_file}")
            
        # Basic validation: ensure either 'transport': 'stdio' with 'command' 
        # or 'transport': 'http' with 'url'
        transport = config.get("transport")
        if transport == "stdio":
            if "command" not in config:
                raise ValueError(f"Server '{name}' (stdio) is missing 'command'")
        elif transport == "http":
            if "url" not in config:
                raise ValueError(f"Server '{name}' (http) is missing 'url'")
        else:
            raise ValueError(f"Server '{name}' has unsupported transport: {transport}")
            
        servers[name] = config
        
    return servers

def generate_mcp_json(servers: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    """Generates the .mcp.json file from the loaded server definitions."""
    mcp_config = {
        "mcpServers": servers
    }
    
    with open(output_path, "w") as f:
        json.dump(mcp_config, f, indent=2, sort_keys=True)
        f.write("\n")

def main():
    repo_root = Path(__file__).parent.parent.parent
    servers_dir = repo_root / ".ai" / "mcp" / "servers"
    output_path = repo_root / ".mcp.json"
    
    try:
        servers = load_servers(servers_dir)
        generate_mcp_json(servers, output_path)
        print(f"Successfully generated {output_path}")
    except ValueError as e:
        print(f"Validation Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
