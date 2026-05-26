import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .parser import load_all, search

mcp = FastMCP("ScanCodex")

_db: dict | None = None

PHASE_KEYWORDS = {
    "recon":            ["Subdomain Enumeration", "Services fingerprint"],
    "vuln_scan":        ["Vulnerability Assessment", "Special Vulnerability"],
    "web":              ["SQL Injection", "Cross-site scripting", "Web"],
    "container":        ["Container and Cluster"],
    "mobile":           ["Mobile App"],
    "smart_contract":   ["Smart Contract"],
    "ai_apps":          ["AI Apps", "AI Model-Powered"],
    "malware":          ["Malware Detection", "Advanced Persistent Threat"],
    "code_analysis":    ["Dynamic or Static Code Analysis"],
    "incident":         ["Advanced Persistent Threat", "Red Team"],
    "a3c":              ["A³C"],
}


_SCANNERS_BOX_URL = "https://raw.githubusercontent.com/We5ter/Scanners-Box/master/README.md"
_A3C_URL = "https://raw.githubusercontent.com/We5ter/Scanners-Box/master/Project-A3C.md"
_CACHE_DIR = Path.home() / ".cache" / "scancodex"


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ScanCodex/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.URLError, OSError):
        return False


def _db_get() -> dict:
    global _db
    if _db is None:
        readme = _CACHE_DIR / "README.md"
        if not readme.exists():
            print("ScanCodex: downloading Scanners-Box README...", flush=True)
            if not _download(_SCANNERS_BOX_URL, readme):
                raise RuntimeError(
                    "Failed to download Scanners-Box README. Check your network."
                )

        a3c = _CACHE_DIR / "Project-A3C.md"
        if not a3c.exists():
            _download(_A3C_URL, a3c)

        _db = load_all(readme, a3c if a3c.exists() else None)
    return _db


@mcp.tool()
def list_categories() -> str:
    """List all scanner categories available in the Scanners-Box codex."""
    db = _db_get()
    lines = ["Available scanner categories:\n"]
    for cat, tools in db.items():
        lines.append(f"  • {cat}  ({len(tools)} tools)")
    return "\n".join(lines)


@mcp.tool()
def recommend_scanners(
    query: str,
    category: str = "",
    language: str = "",
    limit: int = 5,
) -> str:
    """
    Recommend security scanners from Scanners-Box for your task.

    Args:
        query:    Describe what you want to scan or test.
                  Examples: "kubernetes cluster", "LLM prompt injection",
                  "sql injection web app", "android apk malware"
        category: Optional — filter by category name (partial match OK).
                  Use list_categories() to see all options.
        language: Optional — filter by implementation language, e.g. Python, Go.
        limit:    Max results to return (default 5).
    """
    db = _db_get()
    keywords = query.split()
    results = search(db, keywords, category=category, language=language)

    if not results:
        return (
            f'No scanners found for "{query}". '
            "Try broader keywords or call list_categories() to browse."
        )

    top = results[:limit]
    lines = [f'Top {len(top)} of {len(results)} matches for "{query}":\n']
    for rank, (_, tool) in enumerate(top, 1):
        stars = "★" * tool["stars"] or "—"
        subcat = f" › {tool['subcategory']}" if tool["subcategory"] else ""
        lines += [
            f"{rank}. **{tool['name']}**  [{tool['category']}{subcat}]",
            f"   {tool['description']}",
            f"   Language: {tool['language'] or '—'}  |  Score: {stars}",
            f"   {tool['url']}",
            "",
        ]
    return "\n".join(lines)


@mcp.tool()
def build_workflow(phase: str) -> str:
    """
    Get a recommended tool chain for a pentest or security assessment phase.

    Args:
        phase: One of: recon, vuln_scan, web, container, mobile,
               smart_contract, ai_apps, malware, code_analysis, incident, a3c
    """
    targets = PHASE_KEYWORDS.get(phase.lower())
    if not targets:
        phases = ", ".join(PHASE_KEYWORDS)
        return f'Unknown phase "{phase}". Available phases: {phases}'

    db = _db_get()
    lines = [f"Recommended toolchain for phase: **{phase}**\n"]
    found_any = False

    for target in targets:
        target_lc = target.lower()
        for cat, tools in db.items():
            # Match category name or any tool's subcategory
            cat_match = target_lc in cat.lower()
            subcat_tools = [t for t in tools if target_lc in t["subcategory"].lower()]
            matched_tools = tools if cat_match else subcat_tools
            if not matched_tools:
                continue
            found_any = True
            label = matched_tools[0]["subcategory"] if not cat_match else cat
            lines.append(f"### {label}")
            for tool in matched_tools[:4]:
                stars = "★" * tool["stars"] or "—"
                lines.append(f"- **{tool['name']}** ({stars})  {tool['url']}")
                lines.append(f"  {tool['description']}")
            lines.append("")

    if not found_any:
        lines.append("No tools found for this phase in the current codex.")

    return "\n".join(lines)


_README_KEYWORDS = [
    "install", "setup", "usage", "quick start",
    "getting started", "requirement", "how to use", "run",
]

# Fallback install steps when README fetch fails, keyed by normalised language
_LANG_STEPS: dict[str, list[str]] = {
    "python":     ["git clone {url}", "cd {name}", "pip install -r requirements.txt"],
    "go":         ["git clone {url}", "cd {name}", "go build -o {name} ."],
    "java":       ["git clone {url}", "cd {name}", "mvn package -DskipTests"],
    "ruby":       ["git clone {url}", "cd {name}", "bundle install"],
    "javascript": ["git clone {url}", "cd {name}", "npm install"],
    "shell":      ["git clone {url}", "cd {name}", "chmod +x *.sh"],
    "c":          ["git clone {url}", "cd {name}", "make"],
    "rust":       ["git clone {url}", "cd {name}", "cargo build --release"],
    "php":        ["git clone {url}", "cd {name}", "composer install"],
}
_LANG_ALIASES: dict[str, str] = {
    "py": "python", "python3": "python",
    "golang": "go",
    "js": "javascript", "node": "javascript", "typescript": "javascript", "ts": "javascript",
    "bash": "shell", "sh": "shell",
    "c++": "c", "cpp": "c",
    "rs": "rust",
}

# Files that indicate how to build/install after cloning
_BUILD_PROBES: list[tuple[str, list[str]]] = [
    ("requirements.txt",  ["pip install -r requirements.txt"]),
    ("pyproject.toml",    ["pip install ."]),
    ("setup.py",          ["pip install ."]),
    ("go.mod",            ["go build ./..."]),
    ("package.json",      ["npm install"]),
    ("Cargo.toml",        ["cargo build --release"]),
    ("Makefile",          ["make"]),
    ("pom.xml",           ["mvn package -DskipTests"]),
    ("build.gradle",      ["gradle shadowJar"]),
    ("Gemfile",           ["bundle install"]),
    ("composer.json",     ["composer install"]),
]


def _fetch_readme(github_url: str) -> str | None:
    parts = github_url.rstrip("/").split("/")
    if len(parts) < 5:
        return None
    owner, repo = parts[-2], parts[-1]
    for branch in ("main", "master", "HEAD"):
        raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        try:
            req = urllib.request.Request(raw, headers={"User-Agent": "ScanCodex/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
    return None


def _extract_sections(text: str, keywords: list[str], max_lines: int = 80) -> str:
    """Return markdown sections whose headings contain any keyword."""
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    current_level = 0
    buf: list[str] = []

    for line in lines:
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).lower()
            if any(kw in title for kw in keywords):
                if buf:
                    out.append("\n".join(buf))
                buf = [line]
                capture = True
                current_level = level
            elif capture and level <= current_level:
                out.append("\n".join(buf))
                buf = []
                capture = False
            elif capture:
                buf.append(line)
        elif capture:
            buf.append(line)

    if buf:
        out.append("\n".join(buf))

    result = "\n\n".join(out)
    # Trim to max_lines to keep responses manageable
    trimmed = "\n".join(result.splitlines()[:max_lines])
    if len(result.splitlines()) > max_lines:
        trimmed += "\n\n_(README truncated — see full docs at the link below)_"
    return trimmed


def _fallback_steps(tool: dict) -> str:
    lang = _LANG_ALIASES.get(tool["language"].lower(), tool["language"].lower())
    steps = _LANG_STEPS.get(lang, ["git clone {url}", "cd {name}", "# see README"])
    cmds = [s.format(name=tool["name"], url=tool["url"]) for s in steps]
    return "```bash\n" + "\n".join(cmds) + "\n```"


def _find_tool(tool_name: str) -> tuple[dict | None, list[dict]]:
    db = _db_get()
    needle = tool_name.lower()
    found: dict | None = None
    candidates: list[dict] = []
    for tools in db.values():
        for t in tools:
            if t["name"].lower() == needle:
                found = t
                break
            if needle in t["name"].lower() or needle in t["description"].lower():
                candidates.append(t)
        if found:
            break
    return found, candidates


@mcp.tool()
def get_tool_usage(tool_name: str) -> str:
    """
    Get installation and usage instructions for a security tool by fetching its GitHub README.

    Args:
        tool_name: Tool name (partial match OK), e.g. "GitHack", "sqlmap", "subfinder".
    """
    found, candidates = _find_tool(tool_name)

    if not found:
        if not candidates:
            return (
                f'Tool "{tool_name}" not found. '
                "Try recommend_scanners() to discover tools first."
            )
        found = candidates[0]

    stars = "★" * found["stars"] if found["stars"] else "—"
    subcat = f" › {found['subcategory']}" if found["subcategory"] else ""
    header = (
        f"## {found['name']}\n\n"
        f"**Category:** {found['category']}{subcat}\n"
        f"**Language:** {found['language'] or '—'}  |  **Score:** {stars}\n"
        f"**Description:** {found['description']}\n\n"
    )

    readme = _fetch_readme(found["url"])
    if readme:
        sections = _extract_sections(readme, _README_KEYWORDS)
        if sections:
            body = f"### From README\n\n{sections}\n\n"
        else:
            body = f"### Installation (auto-detected)\n\n{_fallback_steps(found)}\n\n"
    else:
        body = f"### Installation (auto-detected)\n\n{_fallback_steps(found)}\n\n"

    footer = f"**Full docs:** {found['url']}#readme"

    if len(candidates) > 1 and found is candidates[0]:
        others = ", ".join(c["name"] for c in candidates[1:5])
        footer += f"\n\n> Also matched: {others}"

    return header + body + footer


@mcp.tool()
def install_tool(tool_name: str, target_dir: str = "") -> str:
    """
    Clone and install a security tool from the codex onto the local machine.

    Args:
        tool_name:  Name of the tool to install (partial match OK).
        target_dir: Where to install. Defaults to ~/tools/<tool_name>.
    """
    found, candidates = _find_tool(tool_name)
    if not found:
        if not candidates:
            return f'Tool "{tool_name}" not found. Try recommend_scanners() first.'
        found = candidates[0]

    dest = Path(target_dir).expanduser() if target_dir else Path.home() / "tools" / found["name"]

    if dest.exists():
        return f'Directory already exists: {dest}\nIf you want a fresh install, remove it first:\n  rm -rf {dest}'

    logs: list[str] = [f"Installing **{found['name']}** into `{dest}`...\n"]

    # 1. Clone
    result = subprocess.run(
        ["git", "clone", "--depth=1", found["url"], str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return f"git clone failed:\n```\n{result.stderr.strip()}\n```"
    logs.append(f"✓ Cloned from {found['url']}")

    # 2. Detect build system from cloned files and run setup
    setup_ran = False
    for probe_file, cmds in _BUILD_PROBES:
        if (dest / probe_file).exists():
            for cmd_str in cmds:
                logs.append(f"  Running: `{cmd_str}`")
                r = subprocess.run(
                    cmd_str, shell=True, cwd=str(dest),
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    logs.append(f"  ⚠ Command exited {r.returncode}:\n```\n{r.stderr.strip()[:400]}\n```")
                else:
                    logs.append(f"  ✓ Done")
            setup_ran = True
            break

    if not setup_ran:
        logs.append("  ℹ No recognised build file found — manual setup may be needed.")

    logs.append(f"\n**Installed at:** `{dest}`")
    logs.append(f"**Docs:** {found['url']}#readme")
    return "\n".join(logs)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
