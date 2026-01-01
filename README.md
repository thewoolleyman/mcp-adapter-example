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
│   └── scripts/
│       ├── update_mcp_servers.py
│       └── test_update_mcp_servers.py
├── .mcp.json                # GENERATED (Do not edit manually)
├── pyproject.toml           # Python project configuration
├── mise.toml                # Tool version pinning (uv, python)
└── README.md
```

## How to Regenerate `.mcp.json`

If you add or modify a server definition in `.ai/mcp/servers/`, you must regenerate the root `.mcp.json` file:

```bash
uv run python .ai/scripts/update_mcp_servers.py
```

## Testing

Tests ensure that the generation script remains deterministic and validates the integrity of server definitions:

```bash
uv run pytest
```

## Benefits

- **Consistency**: One source of truth for all MCP servers.
- **Compatibility**: Supports Claude's auto-discovery via the generated `.mcp.json`.
- **Extensibility**: Easily add new adapters for other tools (like GitLab Duo CLI) without changing the core definitions.
