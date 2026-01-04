#!/usr/bin/env python3
"""
MCP Server Configuration Generator

This script loads MCP server definitions from individual JSON files,
applies adapter configurations to transform them for specific tools,
and generates output configuration files in JSON or TOML format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomli_w


def load_servers(servers_dir: Path) -> dict[str, dict[str, Any]]:
    """
    Load and validate server definitions from JSON files.

    Args:
        servers_dir: Path to directory containing server JSON files

    Returns:
        Dictionary mapping server names to their configurations

    Raises:
        ValueError: If a server definition is invalid or duplicated
        FileNotFoundError: If servers directory doesn't exist
    """
    servers: dict[str, dict[str, Any]] = {}

    if not servers_dir.exists():
        raise FileNotFoundError(f"Servers directory not found: {servers_dir}")

    for path in sorted(servers_dir.glob("*.json")):
        with open(path) as f:
            config = json.load(f)

        name = config.get("name")
        if not name:
            raise ValueError(f"Server definition in {path} is missing 'name' field")

        if name in servers:
            raise ValueError(f"Duplicate server name '{name}' found in {path}")

        transport = config.get("transport")
        if not transport:
            raise ValueError(f"Server '{name}' is missing 'transport' field")

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


def load_adapters(adapters_dir: Path) -> list[dict[str, Any]]:
    """
    Load adapter configurations from JSON files.

    Args:
        adapters_dir: Path to directory containing adapter JSON files

    Returns:
        List of adapter configurations, sorted by filename for determinism
    """
    adapters: list[dict[str, Any]] = []

    if not adapters_dir.exists():
        return adapters

    for path in sorted(adapters_dir.glob("*.json")):
        with open(path) as f:
            config = json.load(f)

        # Skip adapters without a tool field
        if not config.get("tool"):
            continue

        adapters.append(config)

    return adapters


def substitute(value: Any, server_config: dict[str, Any]) -> Any:
    """
    Recursively substitute {{placeholder}} patterns with server config values.

    If a string value is exactly a placeholder (e.g., "{{args}}"), the original
    type from server_config is preserved. Otherwise, string replacement is used.

    Args:
        value: The value to process (can be string, dict, list, or other)
        server_config: Server configuration containing values to substitute

    Returns:
        The value with placeholders substituted
    """
    if isinstance(value, str):
        # Check each key in server_config for placeholder substitution
        for key, val in server_config.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in value:
                # If the entire value is just the placeholder, preserve the type
                if value == placeholder:
                    return val
                # Otherwise, do string replacement
                value = value.replace(placeholder, str(val))
        return value
    elif isinstance(value, dict):
        return {k: substitute(v, server_config) for k, v in value.items()}
    elif isinstance(value, list):
        return [substitute(item, server_config) for item in value]
    else:
        return value


def apply_adapter(
    adapter: dict[str, Any], servers: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """
    Apply an adapter configuration to transform server config for a specific tool.

    Args:
        adapter: Adapter configuration with 'server' and 'mapping' fields
        servers: Dictionary of loaded server configurations

    Returns:
        Transformed configuration for the tool

    Raises:
        ValueError: If adapter references unknown server or is missing fields
    """
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
    return substitute(mapping, server_config)


def generate_mcp_json(servers: dict[str, dict[str, Any]], output_path: Path) -> None:
    """
    Generate the root .mcp.json file with all server configurations.

    Args:
        servers: Dictionary of server configurations
        output_path: Path to write the output file
    """
    mcp_config = {"mcpServers": servers}
    write_json(output_path, mcp_config)


def generate_tool_config(
    tool_name: str,
    config: dict[str, Any],
    format_key: str,
    output_path: Path,
    use_toml: bool = False,
) -> None:
    """
    Generate a tool-specific configuration file.

    Args:
        tool_name: Name of the tool (used as fallback for config name)
        config: The transformed configuration to write
        format_key: The key to wrap the config under (e.g., "mcpServers")
        output_path: Path to write the output file
        use_toml: If True, write TOML format; otherwise JSON
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use config name if present, otherwise tool name
    name = config.get("name", tool_name)

    # Default format key
    if not format_key:
        format_key = "mcpServers"

    if use_toml:
        # For TOML (e.g., Codex), use mcp_servers as the root key
        final_output = {"mcp_servers": {name: config}}
        write_toml(output_path, final_output)
    else:
        final_output = {format_key: {name: config}}
        write_json(output_path, final_output)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write data to a JSON file with 2-space indentation."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def write_toml(path: Path, data: dict[str, Any]) -> None:
    """Write data to a TOML file."""
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def main() -> None:
    """Main entry point for the MCP server configuration generator."""
    # Determine repo root (parent of .ai directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent

    servers_dir = repo_root / ".ai" / "mcp" / "servers"
    adapters_dir = repo_root / ".ai" / "mcp" / "adapters"
    output_path = repo_root / ".mcp.json"

    # Load servers
    servers = load_servers(servers_dir)

    # Generate root .mcp.json
    generate_mcp_json(servers, output_path)
    print(f"Successfully generated {output_path}")

    # Load and process adapters
    adapters = load_adapters(adapters_dir)

    for adapter in adapters:
        tool = adapter.get("tool")
        if not tool:
            continue

        tool_config = apply_adapter(adapter, servers)

        # Determine output path
        tool_output_path = adapter.get("output_path", f".mcp.{tool}.json")
        tool_output_path = repo_root / tool_output_path

        # Determine format
        use_toml = adapter.get("format_type") == "toml"
        format_key = adapter.get("format", "mcpServers")

        generate_tool_config(tool, tool_config, format_key, tool_output_path, use_toml)
        print(f"Successfully generated {tool_output_path}")


if __name__ == "__main__":
    main()
