import json
from pathlib import Path
import pytest
from update_mcp_servers import load_servers, generate_mcp_json

def test_load_servers_success(tmp_path):
    servers_dir = tmp_path / "servers"
    servers_dir.mkdir()
    
    s1 = {
        "name": "server1",
        "transport": "stdio",
        "command": "node",
        "args": ["s1.js"]
    }
    s2 = {
        "name": "server2",
        "transport": "http",
        "url": "http://localhost:1234"
    }
    
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
        "a_server": {"name": "a_server", "transport": "http", "url": "url_a"}
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
