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
            raise ValueError(
                f"Server definition in {server_file} is missing 'name' field"
            )

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


def load_adapters(adapters_dir: Path) -> list[Dict[str, Any]]:
    """Loads all adapter definitions from the specified directory."""
    adapters = []
    for adapter_file in sorted(adapters_dir.glob("*.json")):
        try:
            with open(adapter_file, "r") as f:
                adapters.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to load adapter {adapter_file}: {e}")
    return adapters


def apply_adapter(
    adapter: Dict[str, Any], servers: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Applies an adapter to its target server, substituting placeholders."""
    server_name = adapter.get("server")
    if not server_name:
        raise ValueError(
            f"Adapter for tool '{adapter.get('tool')}' is missing 'server' field"
        )

    server_config = servers.get(server_name)
    if not server_config:
        raise ValueError(
            f"Adapter for tool '{adapter.get('tool')}' targets unknown server '{server_name}'"
        )

    mapping = adapter.get("mapping", {})

    def substitute(value: Any) -> Any:
        if isinstance(value, str):
            for key, val in server_config.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in value:
                    # If the value is exactly the placeholder, we might want to preserve the type
                    if value == placeholder:
                        return val
                    value = value.replace(placeholder, str(val))
            return value
        elif isinstance(value, dict):
            return {k: substitute(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute(v) for v in value]
        return value

    return substitute(mapping)


def generate_mcp_json(servers: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    """Generates the .mcp.json file from the loaded server definitions."""
    mcp_config = {"mcpServers": servers}

    with open(output_path, "w") as f:
        json.dump(mcp_config, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    repo_root = Path(__file__).parent.parent.parent
    servers_dir = repo_root / ".ai" / "mcp" / "servers"
    adapters_dir = repo_root / ".ai" / "mcp" / "adapters"
    output_path = repo_root / ".mcp.json"

    try:
        servers = load_servers(servers_dir)
        generate_mcp_json(servers, output_path)
        print(f"Successfully generated {output_path}")

        adapters = load_adapters(adapters_dir)
        for adapter in adapters:
            tool = adapter.get("tool")
            if not tool:
                continue

            tool_config = apply_adapter(adapter, servers)
            # For simplicity, we wrap the result in the format specified by the adapter
            format_key = adapter.get("format", "mcpServers")
            final_output = {format_key: {tool_config.get("name", tool): tool_config}}

            tool_output_path = repo_root / f".mcp.{tool}.json"
            with open(tool_output_path, "w") as f:
                json.dump(final_output, f, indent=2, sort_keys=True)
                f.write("\n")
            print(f"Successfully generated {tool_output_path}")

    except ValueError as e:
        print(f"Validation Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
