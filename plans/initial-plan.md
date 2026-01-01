# Implementation Plan: mcp-adapter-example

This document is intended to be handed directly to an AI coding agent.
It captures ALL relevant context from the prior discussion and defines
a concrete, reproducible implementation.

────────────────────────────────────────────────────────────
0. CONTEXT AND NON-NEGOTIABLE CONSTRAINTS
────────────────────────────────────────────────────────────

Background:

- `.mcp.json` is currently auto-discovered ONLY by Anthropic tools:
  - Claude Code (VS Code)
  - Claude Code (JetBrains)
  - Claude Desktop

- Other tools (Gemini CLI, Codex CLI, Cursor, GitLab Duo CLI) DO NOT
  auto-discover `.mcp.json`.

- `.mcp.json` is conceptually editor-agnostic, but in practice only
  Anthropic tools load it automatically today.

- Goal: avoid MCP server definition duplication while still allowing:
  - Claude to auto-discover `.mcp.json`
  - Other tools to consume the SAME server definitions via adapters

Key architectural decisions (MANDATORY):

- Canonical MCP server definitions live under:
  .ai/mcp/servers/

- `.mcp.json` is a GENERATED artifact, never hand-edited.

- Generation script lives at:
  .ai/scripts/update-mcp-servers.py

- Python tooling uses:
  - uv (for deps / venv / execution)
  - mise (to install and pin uv)

- Tests must be:
  - pytest
  - co-located with the script under `.ai/scripts/`

- Repo name:
  mcp-adapter-example

- Repo must include:
  - Two example MCP servers
  - One adapter for GitLab Duo CLI

────────────────────────────────────────────────────────────
1. REPOSITORY SETUP
────────────────────────────────────────────────────────────

Create a new PUBLIC GitHub repository:

  name: mcp-adapter-example

Initialize with:
- README.md
- .gitignore (Python-appropriate)

────────────────────────────────────────────────────────────
2. DIRECTORY STRUCTURE (AUTHORITATIVE)
────────────────────────────────────────────────────────────

Create the following structure exactly:

.
├── .ai/
│   ├── mcp/
│   │   ├── servers/
│   │   │   ├── example_stdio.json
│   │   │   ├── example_http.json
│   │   │   └── gitlab_duo.json
│   │   └── adapters/
│   │       └── gitlab_duo_cli.json
│   ├── scripts/
│   │   ├── update-mcp-servers.py
│   │   └── test_update_mcp_servers.py
├── .mcp.json              # GENERATED FILE
├── pyproject.toml
├── uv.toml
├── mise.toml
└── README.md

────────────────────────────────────────────────────────────
3. CANONICAL MCP SERVER DEFINITIONS
────────────────────────────────────────────────────────────

All files in `.ai/mcp/servers/` are the SOURCE OF TRUTH.

They MUST be tool-agnostic and follow MCP concepts only.

Example: example_stdio.json

{
  "name": "example_stdio",
  "transport": "stdio",
  "command": "node",
  "args": ["./tools/example.js"],
  "env": {
    "EXAMPLE_MODE": "demo"
  }
}

Example: example_http.json

{
  "name": "example_http",
  "transport": "http",
  "url": "http://localhost:3333/mcp"
}

GitLab Duo server definition (canonical):

gitlab_duo.json

{
  "name": "gitlab",
  "transport": "http",
  "url": "https://gitlab.com/api/v4/mcp"
}

Rules:
- Each file defines EXACTLY one server
- `name` must be unique
- No Claude-specific keys
- No editor-specific metadata

────────────────────────────────────────────────────────────
4. ADAPTER DEFINITIONS
────────────────────────────────────────────────────────────

Adapters live under:

.ai/mcp/adapters/

These describe how canonical servers map to specific tools.

GitLab Duo CLI adapter example:

gitlab_duo_cli.json

{
  "tool": "gitlab-duo-cli",
  "format": "mcpServers",
  "mapping": {
    "name": "GitLab",
    "type": "http",
    "url": "{{url}}"
  }
}

Notes:
- This file is NOT consumed directly by tools
- It is consumed by the generator script
- Placeholders ({{url}}, {{command}}, etc.) are substituted

────────────────────────────────────────────────────────────
5. MCP GENERATION SCRIPT
────────────────────────────────────────────────────────────

File:
.ai/scripts/update-mcp-servers.py

Responsibilities:

1. Load all JSON files from `.ai/mcp/servers/`
2. Validate:
   - required keys
   - unique names
3. Generate `.mcp.json` in repo root:

{
  "mcpServers": {
    "<name>": { ...server config... }
  }
}

4. Optionally emit tool-specific outputs (future-proofing)
5. Exit non-zero on validation failure

Implementation constraints:

- Pure Python 3.12+
- No global state
- Deterministic output ordering
- Use pathlib
- Use json with sorted keys

────────────────────────────────────────────────────────────
6. PYTHON TOOLING (uv)
────────────────────────────────────────────────────────────

pyproject.toml

[project]
name = "mcp-adapter-example"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = []

[tool.pytest.ini_options]
testpaths = [".ai/scripts"]

uv.toml

[project]
managed = true

[tool.uv]
dev-dependencies = [
  "pytest>=8.0"
]

Usage expectations:

- uv run python .ai/scripts/update-mcp-servers.py
- uv run pytest

────────────────────────────────────────────────────────────
7. MISE CONFIGURATION
────────────────────────────────────────────────────────────

mise.toml

[tools]
uv = "latest"
python = "3.12"

Assumption:
- mise is responsible ONLY for installing uv and python
- uv manages the virtual environment

────────────────────────────────────────────────────────────
8. TESTING REQUIREMENTS
────────────────────────────────────────────────────────────

File:
.ai/scripts/test_update_mcp_servers.py

Tests MUST cover:

- Successful generation of `.mcp.json`
- Deterministic ordering
- Validation failures:
  - duplicate server names
  - missing required fields
- GitLab server appears correctly in output

Tests must:
- Use tmp_path
- Never write to real repo root
- Invoke the script as a function, not via subprocess

────────────────────────────────────────────────────────────
9. README CONTENT
────────────────────────────────────────────────────────────

README.md must explain:

- Why `.mcp.json` is generated
- Why canonical configs live under `.ai/mcp/`
- Which tools auto-discover `.mcp.json`
- How to regenerate:
  uv run python .ai/scripts/update-mcp-servers.py
- How this pattern avoids duplication across:
  - Claude
  - GitLab Duo CLI
  - Future MCP clients

────────────────────────────────────────────────────────────
10. FINAL CHECKLIST FOR AI AGENT
────────────────────────────────────────────────────────────

- [ ] Repo created and pushed to GitHub
- [ ] Directory structure matches exactly
- [ ] Two example
