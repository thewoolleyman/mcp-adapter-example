"""
Tests for the MCP Server Configuration Generator.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from update_mcp_servers import (
    apply_adapter,
    generate_mcp_json,
    generate_tool_config,
    load_adapters,
    load_servers,
    substitute,
)


# ============================================================================
# Test load_servers
# ============================================================================


def test_load_servers_success():
    """Test loading valid server definitions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        # Create stdio server
        stdio_server = {
            "name": "test_stdio",
            "transport": "stdio",
            "command": "node",
            "args": ["./test.js"],
        }
        (servers_dir / "stdio.json").write_text(json.dumps(stdio_server))

        # Create http server
        http_server = {
            "name": "test_http",
            "transport": "http",
            "url": "http://localhost:3000",
        }
        (servers_dir / "http.json").write_text(json.dumps(http_server))

        servers = load_servers(servers_dir)

        assert len(servers) == 2
        assert "test_stdio" in servers
        assert "test_http" in servers
        assert servers["test_stdio"]["command"] == "node"
        assert servers["test_http"]["url"] == "http://localhost:3000"


def test_load_servers_missing_name():
    """Test that servers without a name field raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        # Create server without name
        invalid_server = {"transport": "stdio", "command": "node"}
        (servers_dir / "invalid.json").write_text(json.dumps(invalid_server))

        with pytest.raises(ValueError, match="missing 'name' field"):
            load_servers(servers_dir)


def test_load_servers_duplicate_name():
    """Test that duplicate server names raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        # Create two servers with same name
        server1 = {"name": "duplicate", "transport": "http", "url": "http://a.com"}
        server2 = {"name": "duplicate", "transport": "http", "url": "http://b.com"}
        (servers_dir / "a.json").write_text(json.dumps(server1))
        (servers_dir / "b.json").write_text(json.dumps(server2))

        with pytest.raises(ValueError, match="Duplicate server name"):
            load_servers(servers_dir)


def test_load_servers_missing_transport():
    """Test that servers without transport field raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        invalid_server = {"name": "test", "command": "node"}
        (servers_dir / "invalid.json").write_text(json.dumps(invalid_server))

        with pytest.raises(ValueError, match="missing 'transport' field"):
            load_servers(servers_dir)


def test_load_servers_unsupported_transport():
    """Test that unsupported transport types raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        invalid_server = {"name": "test", "transport": "websocket", "url": "ws://test"}
        (servers_dir / "invalid.json").write_text(json.dumps(invalid_server))

        with pytest.raises(ValueError, match="unsupported transport"):
            load_servers(servers_dir)


def test_load_servers_stdio_missing_command():
    """Test that stdio servers without command raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        invalid_server = {"name": "test", "transport": "stdio"}
        (servers_dir / "invalid.json").write_text(json.dumps(invalid_server))

        with pytest.raises(ValueError, match="missing 'command'"):
            load_servers(servers_dir)


def test_load_servers_http_missing_url():
    """Test that http servers without url raise an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        servers_dir = Path(tmpdir)

        invalid_server = {"name": "test", "transport": "http"}
        (servers_dir / "invalid.json").write_text(json.dumps(invalid_server))

        with pytest.raises(ValueError, match="missing 'url'"):
            load_servers(servers_dir)


# ============================================================================
# Test load_adapters
# ============================================================================


def test_load_adapters_success():
    """Test loading valid adapter configurations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapters_dir = Path(tmpdir)

        adapter = {
            "tool": "cursor",
            "server": "test_stdio",
            "format": "mcpServers",
            "output_path": ".cursor/mcp.json",
            "mapping": {"command": "{{command}}"},
        }
        (adapters_dir / "cursor.json").write_text(json.dumps(adapter))

        adapters = load_adapters(adapters_dir)

        assert len(adapters) == 1
        assert adapters[0]["tool"] == "cursor"


def test_load_adapters_skips_without_tool():
    """Test that adapters without tool field are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapters_dir = Path(tmpdir)

        # Adapter without tool field
        invalid_adapter = {"server": "test", "mapping": {}}
        (adapters_dir / "invalid.json").write_text(json.dumps(invalid_adapter))

        adapters = load_adapters(adapters_dir)

        assert len(adapters) == 0


def test_load_adapters_deterministic_order():
    """Test that adapters are loaded in alphabetical order by filename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapters_dir = Path(tmpdir)

        # Create adapters in non-alphabetical order
        (adapters_dir / "z_adapter.json").write_text(
            json.dumps({"tool": "z_tool", "server": "s", "mapping": {}})
        )
        (adapters_dir / "a_adapter.json").write_text(
            json.dumps({"tool": "a_tool", "server": "s", "mapping": {}})
        )
        (adapters_dir / "m_adapter.json").write_text(
            json.dumps({"tool": "m_tool", "server": "s", "mapping": {}})
        )

        adapters = load_adapters(adapters_dir)

        assert len(adapters) == 3
        assert adapters[0]["tool"] == "a_tool"
        assert adapters[1]["tool"] == "m_tool"
        assert adapters[2]["tool"] == "z_tool"


# ============================================================================
# Test substitute
# ============================================================================


def test_substitute_simple_string():
    """Test simple string placeholder replacement."""
    server_config = {"command": "node", "url": "http://test.com"}

    result = substitute("Run {{command}}", server_config)

    assert result == "Run node"


def test_substitute_preserves_type_for_exact_match():
    """Test that exact placeholder match preserves original type."""
    server_config = {"args": ["./test.js", "--verbose"], "port": 3000}

    # List should be preserved
    result = substitute("{{args}}", server_config)
    assert result == ["./test.js", "--verbose"]
    assert isinstance(result, list)

    # Integer should be preserved
    result = substitute("{{port}}", server_config)
    assert result == 3000
    assert isinstance(result, int)


def test_substitute_nested_dict():
    """Test placeholder substitution in nested dictionaries."""
    server_config = {"command": "node", "url": "http://test.com"}

    value = {"outer": {"inner": "{{command}}", "other": "{{url}}"}}

    result = substitute(value, server_config)

    assert result == {"outer": {"inner": "node", "other": "http://test.com"}}


def test_substitute_list():
    """Test placeholder substitution in lists."""
    server_config = {"command": "node", "url": "http://test.com"}

    value = ["{{command}}", "static", "{{url}}"]

    result = substitute(value, server_config)

    assert result == ["node", "static", "http://test.com"]


def test_substitute_partial_string():
    """Test partial placeholder replacement in strings."""
    server_config = {"name": "test", "port": 3000}

    result = substitute("Server {{name}} on port {{port}}", server_config)

    assert result == "Server test on port 3000"


def test_substitute_no_placeholder():
    """Test that strings without placeholders are unchanged."""
    server_config = {"command": "node"}

    result = substitute("No placeholders here", server_config)

    assert result == "No placeholders here"


def test_substitute_non_string_passthrough():
    """Test that non-string, non-dict, non-list values pass through unchanged."""
    server_config = {"command": "node"}

    assert substitute(42, server_config) == 42
    assert substitute(3.14, server_config) == 3.14
    assert substitute(True, server_config) is True
    assert substitute(None, server_config) is None


# ============================================================================
# Test apply_adapter
# ============================================================================


def test_apply_adapter_success():
    """Test successful adapter application."""
    servers = {
        "test_server": {
            "name": "test_server",
            "transport": "stdio",
            "command": "node",
            "args": ["./test.js"],
        }
    }

    adapter = {
        "tool": "cursor",
        "server": "test_server",
        "mapping": {"command": "{{command}}", "args": "{{args}}"},
    }

    result = apply_adapter(adapter, servers)

    assert result == {"command": "node", "args": ["./test.js"]}


def test_apply_adapter_missing_server_field():
    """Test that missing server field raises an error."""
    servers = {"test_server": {"name": "test_server"}}

    adapter = {"tool": "cursor", "mapping": {}}

    with pytest.raises(ValueError, match="missing 'server' field"):
        apply_adapter(adapter, servers)


def test_apply_adapter_unknown_server():
    """Test that referencing unknown server raises an error."""
    servers = {"test_server": {"name": "test_server"}}

    adapter = {"tool": "cursor", "server": "unknown_server", "mapping": {}}

    with pytest.raises(ValueError, match="unknown server"):
        apply_adapter(adapter, servers)


# ============================================================================
# Test generate_mcp_json
# ============================================================================


def test_generate_mcp_json():
    """Test generating the root .mcp.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / ".mcp.json"

        servers = {
            "server1": {"name": "server1", "transport": "http", "url": "http://a.com"},
            "server2": {"name": "server2", "transport": "http", "url": "http://b.com"},
        }

        generate_mcp_json(servers, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            result = json.load(f)

        assert "mcpServers" in result
        assert result["mcpServers"] == servers


# ============================================================================
# Test generate_tool_config
# ============================================================================


def test_generate_tool_config_json():
    """Test generating a JSON tool configuration file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / ".cursor" / "mcp.json"

        config = {"command": "node", "args": ["./test.js"]}

        generate_tool_config(
            "cursor", config, "mcpServers", output_path, use_toml=False
        )

        assert output_path.exists()

        with open(output_path) as f:
            result = json.load(f)

        assert result == {"mcpServers": {"cursor": config}}


def test_generate_tool_config_toml():
    """Test generating a TOML tool configuration file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / ".codex" / "config.toml"

        config = {"command": "node", "args": ["./test.js"]}

        generate_tool_config("codex", config, "mcpServers", output_path, use_toml=True)

        assert output_path.exists()

        content = output_path.read_text()
        assert "[mcp_servers.codex]" in content
        assert 'command = "node"' in content


def test_generate_tool_config_creates_parent_dirs():
    """Test that parent directories are created if they don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "deeply" / "nested" / "dir" / "config.json"

        config = {"key": "value"}

        generate_tool_config("test", config, "format", output_path, use_toml=False)

        assert output_path.exists()


def test_generate_tool_config_uses_config_name():
    """Test that config name is used instead of tool name when present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "config.json"

        config = {"name": "custom_name", "key": "value"}

        generate_tool_config("tool_name", config, "format", output_path, use_toml=False)

        with open(output_path) as f:
            result = json.load(f)

        assert "custom_name" in result["format"]
        assert "tool_name" not in result["format"]


# ============================================================================
# Integration tests
# ============================================================================


def test_full_workflow():
    """Test the complete workflow from loading to generating configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create server directory and files
        servers_dir = tmpdir / "servers"
        servers_dir.mkdir()

        stdio_server = {
            "name": "example_stdio",
            "transport": "stdio",
            "command": "node",
            "args": ["./example.js"],
            "env": {"MODE": "test"},
        }
        (servers_dir / "example_stdio.json").write_text(json.dumps(stdio_server))

        http_server = {
            "name": "example_http",
            "transport": "http",
            "url": "http://localhost:3000/mcp",
        }
        (servers_dir / "example_http.json").write_text(json.dumps(http_server))

        # Create adapter directory and files
        adapters_dir = tmpdir / "adapters"
        adapters_dir.mkdir()

        cursor_adapter = {
            "tool": "cursor",
            "server": "example_stdio",
            "format": "mcpServers",
            "output_path": ".cursor/mcp.json",
            "mapping": {"command": "{{command}}", "args": "{{args}}"},
        }
        (adapters_dir / "cursor.json").write_text(json.dumps(cursor_adapter))

        codex_adapter = {
            "tool": "codex",
            "server": "example_stdio",
            "output_path": ".codex/config.toml",
            "format_type": "toml",
            "mapping": {"command": "{{command}}", "args": "{{args}}"},
        }
        (adapters_dir / "codex.json").write_text(json.dumps(codex_adapter))

        # Load servers
        servers = load_servers(servers_dir)
        assert len(servers) == 2

        # Generate root .mcp.json
        mcp_path = tmpdir / ".mcp.json"
        generate_mcp_json(servers, mcp_path)
        assert mcp_path.exists()

        # Load and apply adapters
        adapters = load_adapters(adapters_dir)
        assert len(adapters) == 2

        for adapter in adapters:
            tool_config = apply_adapter(adapter, servers)
            tool_output_path = tmpdir / adapter["output_path"]
            use_toml = adapter.get("format_type") == "toml"
            format_key = adapter.get("format", "mcpServers")

            generate_tool_config(
                adapter["tool"], tool_config, format_key, tool_output_path, use_toml
            )

        # Verify outputs
        cursor_path = tmpdir / ".cursor" / "mcp.json"
        codex_path = tmpdir / ".codex" / "config.toml"

        assert cursor_path.exists()
        assert codex_path.exists()

        # Verify cursor JSON content
        with open(cursor_path) as f:
            cursor_content = json.load(f)
        assert cursor_content["mcpServers"]["cursor"]["command"] == "node"
        assert cursor_content["mcpServers"]["cursor"]["args"] == ["./example.js"]

        # Verify codex TOML content
        codex_content = codex_path.read_text()
        assert "[mcp_servers.codex]" in codex_content
        assert 'command = "node"' in codex_content
