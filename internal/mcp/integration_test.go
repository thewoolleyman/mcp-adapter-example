package mcp_test

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/pelletier/go-toml/v2"
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

	// 4. Verify file locations, formats, and content
	tests := []struct {
		path          string
		ext           string
		expectContent string
	}{
		{
			path: ".mcp.json",
			ext:  ".json",
			expectContent: `{
  "mcpServers": {
    "example_http": {
      "name": "example_http",
      "transport": "http",
      "url": "http://localhost:3333/mcp"
    },
    "example_stdio": {
      "args": [
        "./tools/example.js"
      ],
      "command": "node",
      "env": {
        "EXAMPLE_MODE": "demo"
      },
      "name": "example_stdio",
      "transport": "stdio"
    },
    "gitlab": {
      "name": "gitlab",
      "transport": "http",
      "url": "https://gitlab.com/api/v4/mcp"
    }
  }
}`,
		},
		{
			path: ".gemini/settings.json",
			ext:  ".json",
			expectContent: `{
  "mcpServers": {
    "gemini": {
      "url": "http://localhost:3333/mcp"
    }
  }
}`,
		},
		{
			path: ".cursor/mcp.json",
			ext:  ".json",
			expectContent: `{
  "mcpServers": {
    "cursor": {
      "args": [
        "./tools/example.js"
      ],
      "command": "node"
    }
  }
}`,
		},
		{
			path: ".gitlab/duo/mcp.json",
			ext:  ".json",
			expectContent: `{
  "mcpServers": {
    "gitlab-duo-cli": {
      "type": "http",
      "url": "https://gitlab.com/api/v4/mcp"
    }
  }
}`,
		},
		{
			path: ".codex/config.toml",
			ext:  ".toml",
			expectContent: `[mcp_servers]
[mcp_servers.codex]
args = [ './tools/example.js' ]
command = 'node'
`,
		},
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

		content, err := os.ReadFile(fullPath)
		if err != nil {
			t.Errorf("Failed to read file %s: %v", tt.path, err)
			continue
		}

		// Normalize line endings and whitespace for comparison (simple approach)
		// For JSON, we might want to unmarshal and compare maps if we cared less about formatting,
		// but since we control the generator's indentation, string comparison is stricter and fine here.
		// However, TOML ordering might vary if not carefully controlled, but go-toml/v2 is usually deterministic enough for maps if keys are simple.
		// Let's rely on basic string containment or trim logic if needed. For now, exact match logic.

		// Note: The toml library might format slightly differently (e.g. single vs double quotes).
		// We should probably check if content *contains* key values or parse it back.
		// Let's parse it back to map for robust comparison.

		if tt.ext == ".json" {
			verifyJsonContent(t, tt.path, content, []byte(tt.expectContent))
		} else if tt.ext == ".toml" {
			// TOML is harder to string match exactly due to potential ordering/formatting differences
			// We'll trust the verify content helper if we implement generic map comparison,
			// or just simple string check for now.
			// Let's check for key substrings for TOML to avoid flakiness with ordering/quoting
			// OR we can verify via unmarshal.
			verifyTomlContent(t, tt.path, content, []byte(tt.expectContent))
		}
	}
}

// verifyJsonContent unmarshals both expected and actual to compare them as data structures
func verifyJsonContent(t *testing.T, path string, actual, expected []byte) {
	var actMap, expMap interface{}
	if err := json.Unmarshal(actual, &actMap); err != nil {
		t.Errorf("File %s contains invalid JSON: %v", path, err)
		return
	}
	if err := json.Unmarshal(expected, &expMap); err != nil {
		t.Errorf("Test expectation for %s is invalid JSON: %v", path, err)
		return
	}

	if !equal(actMap, expMap) {
		t.Errorf("File %s content mismatch.\nExpected:\n%s\nActual:\n%s", path, expected, actual)
	}
}

// verifyTomlContent unmarshals both to compare as maps
func verifyTomlContent(t *testing.T, path string, actual, expected []byte) {
	var actMap, expMap interface{}
	if err := toml.Unmarshal(actual, &actMap); err != nil {
		t.Errorf("File %s contains invalid TOML: %v", path, err)
		return
	}
	if err := toml.Unmarshal(expected, &expMap); err != nil {
		t.Errorf("Test expectation for %s is invalid TOML: %v", path, err)
		return
	}

	if !equal(actMap, expMap) {
		t.Errorf("File %s content mismatch.\nExpected:\n%s\nActual:\n%s", path, expected, actual)
	}
}

// simple deep equal for map[string]interface{} / []interface{} / scalars
// implementing a basic version since reflect.DeepEqual can be strict about types (float64 vs int)
// stemming from different decoders (json uses float64, toml might use int64)
func equal(a, b interface{}) bool {
	// For simplicity in this test context, we can rely on reflect.DeepEqual
	// IF we ensure test expectations match the decoder types.
	// JSON unmarshals numbers to float64. TOML unmarshals integers to int64.
	// This might be tricky. Let's try reflect.DeepEqual first and refine if needed.
	return reflect.DeepEqual(a, b)
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
