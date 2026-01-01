package mcp

import (
	"encoding/json"
	"fmt"
	"os"
)

func GenerateMCPJson(servers map[string]ServerConfig, outputPath string) error {
	mcpConfig := map[string]interface{}{
		"mcpServers": servers,
	}
	return writeJson(outputPath, mcpConfig)
}

func GenerateToolJson(toolName string, config map[string]interface{}, formatKey string, outputPath string) error {
	// If formatKey is empty, default to "mcpServers" to match Python behavior
	if formatKey == "" {
		formatKey = "mcpServers"
	}
	
	// Create the tool output structure
	// Format: { "formatKey": { "toolName": config } }
	// Wait, checking python implementation: 
	// final_output = {format_key: {tool_config.get("name", tool): tool_config}}
	
	name, ok := config["name"].(string)
	if !ok || name == "" {
		name = toolName
	}
	
	finalOutput := map[string]interface{}{
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
