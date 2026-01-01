package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/thewoolleyman/mcp-adapter-example/internal/mcp"
)

func main() {
	// Locate repo root (assuming we run from repo root or a subdir, 
	// but for now let's assume CWD is repo root like the python script)
	// Actually python script did: repo_root = Path(__file__).parent.parent.parent
	// We will assume the user runs the binary from the repo root for now.
	repoRoot, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting current working directory: %v\n", err)
		os.Exit(1)
	}

	serversDir := filepath.Join(repoRoot, ".ai", "mcp", "servers")
	adaptersDir := filepath.Join(repoRoot, ".ai", "mcp", "adapters")
	outputPath := filepath.Join(repoRoot, ".mcp.json")

	// Load Servers
	servers, err := mcp.LoadServers(serversDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading servers: %v\n", err)
		os.Exit(1)
	}

	// Generate .mcp.json
	if err := mcp.GenerateMCPJson(servers, outputPath); err != nil {
		fmt.Fprintf(os.Stderr, "Error generating .mcp.json: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Successfully generated %s\n", outputPath)

	// Load Adapters
	adapters, err := mcp.LoadAdapters(adaptersDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading adapters: %v\n", err)
		os.Exit(1)
	}

	// Process Adapters
	for _, adapter := range adapters {
		if adapter.Tool == "" {
			continue
		}

		toolConfig, err := mcp.ApplyAdapter(adapter, servers)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error applying adapter for %s: %v\n", adapter.Tool, err)
			os.Exit(1)
		}

		toolOutputPath := filepath.Join(repoRoot, fmt.Sprintf(".mcp.%s.json", adapter.Tool))
		if err := mcp.GenerateToolJson(adapter.Tool, toolConfig, adapter.Format, toolOutputPath); err != nil {
			fmt.Fprintf(os.Stderr, "Error generating config for %s: %v\n", adapter.Tool, err)
			os.Exit(1)
		}
		fmt.Printf("Successfully generated %s\n", toolOutputPath)
	}
}