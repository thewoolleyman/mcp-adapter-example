# mcp-adapter-example

This project demonstrates a pattern for managing MCP (Model Context Protocol) server definitions in a tool-agnostic way while maintaining compatibility with tools that expect a `.mcp.json` file.

## The Problem

- `.mcp.json` is currently auto-discovered primarily by Anthropic tools (Claude Code, Claude Desktop).
- Other tools (Gemini CLI, Cursor, etc.) do not yet auto-discover this file.
- Maintaining multiple configuration files for different tools leads to duplication and drift.

## The Solution

1.  **Canonical Definitions**: All MCP server definitions are stored as individual JSON files in `.ai/mcp/servers/`. These are the single source of truth and follow standard MCP concepts.
2.  **Generated Artifacts**: The `.mcp.json` file in the root is a **generated artifact**. It is created by a script that aggregates all canonical definitions.
3.  **Adapters**: For tools that require specific formats or additional metadata, adapters in `.ai/mcp/adapters/` define how to map canonical definitions to those tool-specific formats.

## Repository Structure

```
.
├── .ai/
│   ├── mcp/
│   │   ├── servers/         # SOURCE OF TRUTH (Canonical definitions)
│   │   └── adapters/        # Tool-specific mapping definitions
├── cmd/mcp-bridge/          # Go CLI implementation
├── internal/mcp/            # Core logic
├── .mcp.json                # GENERATED (Do not edit manually)
├── go.mod                   # Go project configuration
├── mise.toml                # Tool version pinning (go)
└── README.md
```

## How to Regenerate `.mcp.json`

If you add or modify a server definition in `.ai/mcp/servers/`, you must regenerate the root `.mcp.json` file:

```bash
go run ./cmd/mcp-bridge
```

## Testing

Tests ensure that the generation script remains deterministic and validates the integrity of server definitions.

### Unit & Integration Tests

Run core tests (excluding E2E):
```bash
go test -v ./internal/...
```

### End-to-End (E2E) Tests

Run E2E tests (verifies actual tool integration):
```bash
go test -v ./tests/...
```

## Quality Assurance

This project uses standard Go tooling to ensure code quality.

### Pre-commit Hooks

We use `pre-commit` to run linters and tests before every commit.
1. Install pre-commit: `brew install pre-commit` (or via `mise`)
2. Install hooks: `pre-commit install`

Hooks running:
- `go-fmt`, `go-vet`, `go-mod-tidy`
- `golangci-lint`
- Unit/Integration tests (`go test ./internal/...`)

### CI/CD

GitHub Actions runs the following checks on every push:
1. **Lint**: `golangci-lint`
2. **Test**: Unit and Integration tests
3. **Build**: Verifies the binary compiles

## Benefits

- **Consistency**: One source of truth for all MCP servers.
- **Compatibility**: Supports Claude's auto-discovery via the generated `.mcp.json`.
- **Extensibility**: Easily add new adapters for other tools (like GitLab Duo CLI) without changing the core definitions.
