package mcp

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/pelletier/go-toml/v2"
)

func GenerateMCPJson(servers map[string]ServerConfig, outputPath string) error {
	mcpConfig := map[string]interface{}{
		"mcpServers": servers,
	}
	return writeJson(outputPath, mcpConfig)
}

func GenerateToolConfig(toolName string, config map[string]interface{}, formatKey string, outputPath string, useTOML bool) error {
	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return fmt.Errorf("failed to create directory for %s: %w", outputPath, err)
	}

	// If formatKey is empty, default to "mcpServers" to match Python behavior
	if formatKey == "" {
		formatKey = "mcpServers"
	}

	name, ok := config["name"].(string)
	if !ok || name == "" {
		name = toolName
	}

	var finalOutput map[string]interface{}

	if useTOML {
		// For Codex TOML, it seems the format is [mcp_servers.<name>]
		// So we structure it accordingly.
		finalOutput = map[string]interface{}{
			"mcp_servers": map[string]interface{}{
				name: config,
			},
		}
		return writeToml(outputPath, finalOutput)
	}

	finalOutput = map[string]interface{}{
		formatKey: map[string]interface{}{
			name: config,
		},
	}

	return writeJson(outputPath, finalOutput)
}

func writeJson(path string, data interface{}) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("failed to create file %s: %w", path, err)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(data); err != nil {
		return fmt.Errorf("failed to encode JSON to %s: %w", path, err)
	}

	return nil
}

func writeToml(path string, data interface{}) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("failed to create file %s: %w", path, err)
	}
	defer file.Close()

	encoder := toml.NewEncoder(file)
	if err := encoder.Encode(data); err != nil {
		return fmt.Errorf("failed to encode TOML to %s: %w", path, err)
	}

	return nil
}
