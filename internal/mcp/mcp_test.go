package mcp

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestLoadServers(t *testing.T) {
	tmpDir := t.TempDir()

	s1 := ServerConfig{
		"name":      "server1",
		"transport": "stdio",
		"command":   "node",
		"args":      []string{"s1.js"},
	}
	s2 := ServerConfig{
		"name":      "server2",
		"transport": "http",
		"url":       "http://localhost:1234",
	}

	writeTestJson(t, filepath.Join(tmpDir, "s1.json"), s1)
	writeTestJson(t, filepath.Join(tmpDir, "s2.json"), s2)

	servers, err := LoadServers(tmpDir)
	if err != nil {
		t.Fatalf("LoadServers failed: %v", err)
	}

	if len(servers) != 2 {
		t.Errorf("Expected 2 servers, got %d", len(servers))
	}
	if servers["server1"]["name"] != "server1" {
		t.Errorf("Expected server1 name to be server1")
	}
}

func TestApplyAdapter(t *testing.T) {
	servers := map[string]ServerConfig{
		"s1": {
			"name":      "s1",
			"transport": "http",
			"url":       "http://test",
			"args":      []string{"--flag"},
		},
	}

	adapter := AdapterConfig{
		Tool:   "t1",
		Server: "s1",
		Mapping: map[string]interface{}{
			"cmd":  "{{name}}",
			"args": "{{args}}",
			"uri":  "{{url}}",
			"nested": map[string]interface{}{
				"val": "{{transport}}",
			},
		},
	}

	result, err := ApplyAdapter(adapter, servers)
	if err != nil {
		t.Fatalf("ApplyAdapter failed: %v", err)
	}

	if result["cmd"] != "s1" {
		t.Errorf("Expected cmd to be s1, got %v", result["cmd"])
	}
	if result["uri"] != "http://test" {
		t.Errorf("Expected uri to be http://test, got %v", result["uri"])
	}
	
	// Check nested replacement
	nested, ok := result["nested"].(map[string]interface{})
	if !ok {
		t.Fatal("nested field is not a map")
	}
	if nested["val"] != "http" {
		t.Errorf("Expected nested val to be http, got %v", nested["val"])
	}

	// Check type preservation for list
	_, ok = result["args"].([]interface{}) // JSON unmarshal creates []interface{}
	if !ok {
		// Wait, our mock ServerConfig used []string, but LoadServers unmarshals to interface{}
		// In this test we manually created ServerConfig with []string
		// The substitute function handles specific types? 
		// substitute logic:
		// case string:
		// ... if v == placeholder { return val }
		// So if val is []string, it returns []string.
		// Let's check what it actually is.
		t.Logf("args type: %T", result["args"])
	}
	
	// Since we defined s1 args as []string, it should be preserved
	strs, ok := result["args"].([]string)
	if ok {
		if len(strs) != 1 || strs[0] != "--flag" {
			t.Errorf("Args content mismatch: %v", strs)
		}
	} else {
		// If it came from JSON unmarshal it would be []interface{}, but here we injected Go types
		t.Errorf("Expected []string, got %T", result["args"])
	}
}

func writeTestJson(t *testing.T, path string, data interface{}) {
	file, err := os.Create(path)
	if err != nil {
		t.Fatalf("Failed to create %s: %v", path, err)
	}
	defer file.Close()
	if err := json.NewEncoder(file).Encode(data); err != nil {
		t.Fatalf("Failed to encode json: %v", err)
	}
}
