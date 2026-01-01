package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestEndToEnd_GeminiConfigValidation(t *testing.T) {
	// 1. Build mcp-bridge
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Failed to get CWD: %v", err)
	}
	repoRoot := filepath.Dir(cwd)

	binPath := filepath.Join(cwd, "mcp-bridge-e2e")
	buildCmd := exec.Command("go", "build", "-o", binPath, filepath.Join(repoRoot, "cmd", "mcp-bridge"))
	if output, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("Failed to build mcp-bridge: %v\nOutput: %s", err, string(output))
	}
	defer os.Remove(binPath)

	// 2. Run mcp-bridge to generate config
	runCmd := exec.Command(binPath)
	runCmd.Dir = repoRoot
	if output, err := runCmd.CombinedOutput(); err != nil {
		t.Fatalf("Failed to run mcp-bridge from %s: %v\nOutput: %s", repoRoot, err, string(output))
	}

	// 3. Verify Gemini CLI accepts the config
	geminiCmd := exec.Command("gemini", "--version")
	geminiCmd.Dir = repoRoot
	
	output, err := geminiCmd.CombinedOutput()
	if err != nil {
		t.Fatalf("Gemini CLI rejected the configuration:\n%s\nError: %v", string(output), err)
	}
	if strings.Contains(string(output), "Invalid configuration") {
		t.Fatalf("Gemini CLI reported invalid configuration:\n%s", string(output))
	}

		// 4. Verify Cursor CLI using cursor-agent

		cursorAgentCmd := exec.Command("cursor-agent", "mcp", "list")

		cursorAgentCmd.Dir = repoRoot

		output, err = cursorAgentCmd.CombinedOutput()

		if err != nil {

			t.Fatalf("cursor-agent mcp list failed:\n%s\nError: %v", string(output), err)

		}

		

		// Verify that our 'cursor' server (from example_stdio) is listed

		// Our adapter currently generates the key as "cursor" in .cursor/mcp.json

		if !strings.Contains(string(output), "cursor") {

			t.Fatalf("cursor-agent did not list the 'cursor' MCP server:\n%s", string(output))

		}

	}

	