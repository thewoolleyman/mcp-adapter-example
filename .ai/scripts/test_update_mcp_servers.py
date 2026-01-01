import json
import pytest
from update_mcp_servers import (
    load_servers,
    generate_mcp_json,
    load_adapters,
    apply_adapter,
)


def test_apply_adapter_gemini():
    servers = {
        "example_http": {
            "name": "example_http",
            "transport": "http",
            "url": "http://localhost:3333/mcp",
        }
    }
    adapter = {
        "tool": "gemini",
        "server": "example_http",
        "mapping": {"name": "{{name}}", "type": "{{transport}}", "url": "{{url}}"},
    }

    result = apply_adapter(adapter, servers)
    assert result == {
        "name": "example_http",
        "type": "http",
        "url": "http://localhost:3333/mcp",
    }


def test_load_adapters(tmp_path):
    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()

    a1 = {"tool": "t1", "server": "s1"}
    a2 = {"tool": "t2", "server": "s2"}

    (adapters_dir / "a1.json").write_text(json.dumps(a1))
    (adapters_dir / "a2.json").write_text(json.dumps(a2))

    adapters = load_adapters(adapters_dir)
    assert len(adapters) == 2
    assert adapters[0]["tool"] == "t1"
    assert adapters[1]["tool"] == "t2"


def test_apply_adapter_success():
    servers = {
        "gitlab": {
            "name": "gitlab",
            "transport": "http",
            "url": "https://gitlab.com/api",
        }
    }
    adapter = {
        "tool": "duo",
        "server": "gitlab",
        "mapping": {
            "name": "GitLab Duo",
            "type": "{{transport}}",
            "api_url": "{{url}}",
        },
    }

    result = apply_adapter(adapter, servers)
    assert result == {
        "name": "GitLab Duo",
        "type": "http",
        "api_url": "https://gitlab.com/api",
    }


def test_apply_adapter_placeholder_list():
    servers = {"s1": {"name": "s1", "args": ["--debug", "run"]}}
    adapter = {"tool": "t1", "server": "s1", "mapping": {"command_args": "{{args}}"}}

    result = apply_adapter(adapter, servers)
    assert result == {"command_args": ["--debug", "run"]}


def test_apply_adapter_missing_server():
    servers = {"s1": {"name": "s1"}}
    adapter = {"tool": "t1", "server": "unknown"}

    with pytest.raises(ValueError, match="targets unknown server 'unknown'"):
        apply_adapter(adapter, servers)


def test_load_servers_success(tmp_path):
    servers_dir = tmp_path / "servers"
    servers_dir.mkdir()

    s1 = {"name": "server1", "transport": "stdio", "command": "node", "args": ["s1.js"]}
    s2 = {"name": "server2", "transport": "http", "url": "http://localhost:1234"}

    (servers_dir / "s2.json").write_text(json.dumps(s2))
    (servers_dir / "s1.json").write_text(json.dumps(s1))

    servers = load_servers(servers_dir)

    assert len(servers) == 2
    assert "server1" in servers
    assert "server2" in servers
    assert servers["server1"] == s1
    assert servers["server2"] == s2
    # Deterministic check: keys should be sorted by filename (s1, s2)
    assert list(servers.keys()) == ["server1", "server2"]


def test_load_servers_duplicate_name(tmp_path):
    servers_dir = tmp_path / "servers"
    servers_dir.mkdir()

    s1 = {"name": "dup", "transport": "http", "url": "url1"}
    s2 = {"name": "dup", "transport": "http", "url": "url2"}

    (servers_dir / "a.json").write_text(json.dumps(s1))
    (servers_dir / "b.json").write_text(json.dumps(s2))

    with pytest.raises(ValueError, match="Duplicate server name 'dup'"):
        load_servers(servers_dir)


def test_load_servers_missing_name(tmp_path):
    servers_dir = tmp_path / "servers"
    servers_dir.mkdir()

    s1 = {"transport": "http", "url": "url1"}
    (servers_dir / "a.json").write_text(json.dumps(s1))

    with pytest.raises(ValueError, match="missing 'name' field"):
        load_servers(servers_dir)


def test_load_servers_unsupported_transport(tmp_path):
    servers_dir = tmp_path / "servers"
    servers_dir.mkdir()

    s1 = {"name": "s1", "transport": "ftp", "url": "url1"}
    (servers_dir / "a.json").write_text(json.dumps(s1))

    with pytest.raises(ValueError, match="unsupported transport: ftp"):
        load_servers(servers_dir)


def test_generate_mcp_json(tmp_path):
    output_path = tmp_path / ".mcp.json"
    servers = {
        "z_server": {"name": "z_server", "transport": "http", "url": "url_z"},
        "a_server": {"name": "a_server", "transport": "http", "url": "url_a"},
    }

    generate_mcp_json(servers, output_path)

    assert output_path.exists()
    content = json.loads(output_path.read_text())

    assert "mcpServers" in content
    assert content["mcpServers"] == servers

    # Verify deterministic ordering in the file
    lines = output_path.read_text().splitlines()
    # "a_server" should come before "z_server" due to sort_keys=True
    a_idx = next(i for i, line in enumerate(lines) if "a_server" in line)
    z_idx = next(i for i, line in enumerate(lines) if "z_server" in line)
    assert a_idx < z_idx
