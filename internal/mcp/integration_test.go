package mcp_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestIntegration_CorrectFileLocations(t *testing.T) {
	// 1. Setup temporary workspace
	tmpDir := t.TempDir()
	
	// Find repo root (walking up from internal/mcp)
	cwd, _ := os.Getwd()
	repoRoot := filepath.Dir(filepath.Dir(cwd))
	aiSrc := filepath.Join(repoRoot, ".ai")

	// Copy current .ai structure
	err := copyDir(aiSrc, filepath.Join(tmpDir, ".ai"))
	if err != nil {
		t.Fatalf("Failed to copy .ai directory from %s: %v", aiSrc, err)
	}

	// 2. Build the executable
	binPath := filepath.Join(tmpDir, "mcp-bridge")
	// Note: cmd/mcp-bridge is relative to repoRoot
	buildCmd := exec.Command("go", "build", "-o", binPath, filepath.Join(repoRoot, "cmd", "mcp-bridge"))
	if output, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("Failed to build executable: %v\nOutput: %s", err, string(output))
	}

	// 3. Run the executable in the temp dir
	runCmd := exec.Command(binPath)
	runCmd.Dir = tmpDir
	if output, err := runCmd.CombinedOutput(); err != nil {
		t.Fatalf("Failed to run executable: %v\nOutput: %s", err, string(output))
	}

	// 4. Verify file locations and formats
	tests := []struct {
		path string
		ext  string
	}{
		{".mcp.json", ".json"},
		{".gemini/settings.json", ".json"},
		{".cursor/mcp.json", ".json"},
		{".gitlab/duo/mcp.json", ".json"},
		{".codex/config.toml", ".toml"},
	}

	for _, tt := range tests {
		fullPath := filepath.Join(tmpDir, tt.path)
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			t.Errorf("Expected file %s was not created", tt.path)
			continue
		}
		
		if filepath.Ext(fullPath) != tt.ext {
			t.Errorf("File %s has wrong extension: expected %s, got %s", tt.path, tt.ext, filepath.Ext(fullPath))
		}
	}
}

func copyDir(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, info.Mode())
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(target, data, info.Mode())
	})
}
