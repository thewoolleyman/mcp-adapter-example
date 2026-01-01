package mcp

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type ServerConfig map[string]interface{}

func LoadServers(serversDir string) (map[string]ServerConfig, error) {
	servers := make(map[string]ServerConfig)

	entries, err := os.ReadDir(serversDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read servers directory: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}

		path := filepath.Join(serversDir, entry.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("failed to read file %s: %w", path, err)
		}

		var config ServerConfig
		if err := json.Unmarshal(data, &config); err != nil {
			return nil, fmt.Errorf("failed to parse JSON from %s: %w", path, err)
		}

		name, ok := config["name"].(string)
		if !ok || name == "" {
			return nil, fmt.Errorf("server definition in %s is missing 'name' field", path)
		}

		if _, exists := servers[name]; exists {
			return nil, fmt.Errorf("duplicate server name '%s' found in %s", name, path)
		}

		transport, ok := config["transport"].(string)
		if !ok {
			return nil, fmt.Errorf("server '%s' is missing or has invalid 'transport' field", name)
		}

		if transport == "stdio" {
			if _, ok := config["command"]; !ok {
				return nil, fmt.Errorf("server '%s' (stdio) is missing 'command'", name)
			}
		} else if transport == "http" {
			if _, ok := config["url"]; !ok {
				return nil, fmt.Errorf("server '%s' (http) is missing 'url'", name)
			}
		} else {
			return nil, fmt.Errorf("server '%s' has unsupported transport: %s", name, transport)
		}

		servers[name] = config
	}

	return servers, nil
}

type AdapterConfig struct {
	Tool       string                 `json:"tool"`
	Server     string                 `json:"server"`
	Format     string                 `json:"format"`
	Mapping    map[string]interface{} `json:"mapping"`
	OutputPath string                 `json:"output_path"`
	FormatType string                 `json:"format_type"` // "json" or "toml"
}

func LoadAdapters(adaptersDir string) ([]AdapterConfig, error) {
	var adapters []AdapterConfig

	entries, err := os.ReadDir(adaptersDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read adapters directory: %w", err)
	}

	// Sort entries to ensure deterministic loading order
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}

		path := filepath.Join(adaptersDir, entry.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("failed to read file %s: %w", path, err)
		}

		var config AdapterConfig
		if err := json.Unmarshal(data, &config); err != nil {
			return nil, fmt.Errorf("failed to parse JSON from %s: %w", path, err)
		}

		if config.Tool == "" {
			// For untyped loading to check specific fields if needed
			var raw map[string]interface{}
			_ = json.Unmarshal(data, &raw)
			if _, ok := raw["tool"]; !ok {
				// Just skipping if no tool is present or handle as error?
				// Python implementation skipped if no tool.
				continue
			}
		}

		adapters = append(adapters, config)
	}

	return adapters, nil
}
