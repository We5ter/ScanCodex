# ScanCodex

> The security scanner codex for AI agents — powered by [Scanners-Box](https://github.com/We5ter/Scanners-Box).

An MCP (Model Context Protocol) server that turns the Scanners-Box arsenal of 300+ open-source security tools into a queryable knowledge base for Claude, Cursor, and any MCP-compatible AI agent.

Ask your AI assistant _"what should I use to scan Kubernetes for misconfigs?"_ and it will consult the codex and recommend the right tools.

## Tools exposed

| Tool | Description |
|------|-------------|
| `list_categories` | Browse all scanner categories |
| `recommend_scanners` | Find scanners by task description, category, or language |
| `build_workflow` | Get a full tool chain for a pentest phase |

## Quick start

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
# Clone both repos side by side
git clone https://github.com/We5ter/Scanners-Box
git clone https://github.com/We5ter/ScanCodex
cd ScanCodex

# Test it locally
uvx --from . scancodex
```

## Claude Desktop setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scancodex": {
      "command": "uvx",
      "args": ["--from", "/path/to/ScanCodex", "scancodex"]
    }
  }
}
```

If Scanners-Box is not in a sibling directory, set the path explicitly:

```json
{
  "mcpServers": {
    "scancodex": {
      "command": "uvx",
      "args": ["--from", "/path/to/ScanCodex", "scancodex"],
      "env": {
        "SCANNERS_BOX_README": "/path/to/Scanners-Box/README.md"
      }
    }
  }
}
```

## Claude Code setup

```bash
claude mcp add scancodex -- uvx --from /path/to/ScanCodex scancodex
```

## Example prompts

```
What tools should I use to test an LLM app for prompt injection?

I need to scan a Kubernetes cluster for security issues — what do you recommend?

Build me a recon workflow for a pentest engagement.

Show me Go-based vulnerability scanners for container images.
```

## Pentest phases for build_workflow

`recon` · `vuln_scan` · `web` · `container` · `mobile` · `smart_contract` · `ai_apps` · `malware` · `code_analysis` · `incident`

## License

MIT — data sourced from [Scanners-Box](https://github.com/We5ter/Scanners-Box) (CC-BY-NC-ND-4.0).
