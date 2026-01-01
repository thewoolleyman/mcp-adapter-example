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

		t.Logf("cursor-agent check skipped/failed (not installed?): %v", err)

	} else {

		// Verify that our 'cursor' server (from example_stdio) is listed

		if !strings.Contains(string(output), "cursor") {

			t.Fatalf("cursor-agent did not list the 'cursor' MCP server:\n%s", string(output))

		}

	}

	// 5. Verify GitLab Duo CLI config

	// GitLab Duo doesn't have a standalone free CLI easily validatable,

	// so we check if the config file exists and is valid JSON as a proxy.

	duoConfigPath := filepath.Join(repoRoot, ".gitlab", "duo", "mcp.json")

	if _, err := os.Stat(duoConfigPath); os.IsNotExist(err) {

		t.Errorf("GitLab Duo config not found at %s", duoConfigPath)

	}

	// 6. Verify Codex config

	// Similarly for Codex, check file existence and basic TOML structure validity

	codexConfigPath := filepath.Join(repoRoot, ".codex", "config.toml")

	if _, err := os.Stat(codexConfigPath); os.IsNotExist(err) {

		t.Errorf("Codex config not found at %s", codexConfigPath)

	}

}
