import re
from pathlib import Path
from collections import defaultdict


def load_scanners(readme_path: Path) -> dict[str, list[dict]]:
    """Parse Scanners-Box README.md into {category: [tool, ...]}."""
    text = readme_path.read_text(encoding="utf-8")

    db: dict[str, list] = defaultdict(list)
    current_cat = ""
    current_subcat = ""
    pending: dict | None = None

    for line in text.splitlines():
        if line.startswith("### "):
            current_cat = line[4:].strip()
            current_subcat = ""
            pending = None
            continue

        if line.startswith("#### "):
            current_subcat = line[5:].strip()
            pending = None
            continue

        # Tool line: - https://github.com/... - **desc**
        m = re.match(r"^- (https://github\.com/[^\s]+)\s+-\s+\*\*(.+?)\*\*", line)
        if m and current_cat:
            url = m.group(1).rstrip("/")
            name = url.split("/")[-1]
            pending = {
                "name": name,
                "url": url,
                "description": m.group(2).strip(),
                "language": "",
                "stars": 0,
                "category": current_cat,
                "subcategory": current_subcat,
            }
            db[current_cat].append(pending)
            continue

        # Badge line following a tool — extract language + star score
        if pending and "MainLanguage-" in line:
            lang_m = re.search(r"MainLanguage-([\w./+# -]+?)(?:-(?:blue|green|yellow|red|orange|purple|lightgrey|gray|grey|brightgreen|informational|critical|success|important))", line)
            if lang_m:
                pending["language"] = lang_m.group(1).replace("--", " ")

            # Stars encoded as %E2%98%85 (★) in the badge URL
            stars_m = re.search(r"Score-((?:%E2%98%85)+)", line)
            if stars_m:
                pending["stars"] = stars_m.group(1).count("%E2%98%85")

    return dict(db)


def load_a3c(a3c_path: Path) -> dict[str, list[dict]]:
    """Parse Project-A3C.md (Markdown table format) into {category: [tool, ...]}."""
    text = a3c_path.read_text(encoding="utf-8")
    db: dict[str, list] = defaultdict(list)
    current_cat = ""

    for line in text.splitlines():
        # Category heading: ## 🔴 AI Autonomous Red Team
        h = re.match(r"^## (.+)", line)
        if h:
            raw = h.group(1).strip()
            # Strip leading emoji + spaces
            raw = re.sub(r"^[\U00010000-\U0010ffff\u2000-\u3300\U0001F000-\U0001FFFF️ ]+", "", raw).strip()
            if raw and raw not in ("Overview", "Categories", "A³C Badge", "Powered by Scanners Box", "Submit a Project"):
                current_cat = f"A³C — {raw}"
            continue

        if not current_cat:
            continue

        # Table data row: | [**Name**](url) | desc | [![lang](badge)](url) | ... |
        if not line.startswith("|") or line.startswith("| Project") or line.startswith("|:"):
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue

        # Cell 0: [**Name**](url)
        link_m = re.search(r"\[(?:\*\*)?([^\]]+?)(?:\*\*)?\]\((https://github\.com/[^\)]+)\)", cells[0])
        if not link_m:
            continue

        name = link_m.group(1).strip()
        url = link_m.group(2).rstrip("/")
        description = re.sub(r"\[.*?\]\(.*?\)", "", cells[1]).strip()  # strip any inline links

        # Cell 2: language badge
        language = ""
        if len(cells) > 2:
            lang_m = re.search(r"language-([\w./+# -]+?)(?:-[0-9A-Fa-f]{6}|\?)", cells[2])
            if lang_m:
                language = lang_m.group(1)

        db[current_cat].append({
            "name": name,
            "url": url,
            "description": description,
            "language": language,
            "stars": 0,  # live badge, no static count
            "category": current_cat,
            "subcategory": "",
            "a3c": True,
        })

    return dict(db)


def load_all(readme_path: Path, a3c_path: Path | None = None) -> dict[str, list[dict]]:
    """Merge Scanners-Box README and Project-A3C into one db."""
    db = load_scanners(readme_path)
    if a3c_path and a3c_path.exists():
        for cat, tools in load_a3c(a3c_path).items():
            db.setdefault(cat, []).extend(tools)
    return db


def _word_count(haystack: str, word: str) -> int:
    """Count whole-word occurrences of word in haystack (case-insensitive)."""
    return len(re.findall(rf"\b{re.escape(word)}\b", haystack))


def search(db: dict, keywords: list[str], category: str = "", language: str = "") -> list[tuple[int, dict]]:
    """Return [(score, tool)] sorted by relevance then star count."""
    kws = [k.lower() for k in keywords]
    results = []

    for cat, tools in db.items():
        if category and category.lower() not in cat.lower():
            continue
        for tool in tools:
            if language and language.lower() not in tool["language"].lower():
                continue
            haystack = " ".join([
                tool["name"], tool["description"], cat, tool["subcategory"]
            ]).lower()
            score = sum(_word_count(haystack, kw) for kw in kws)
            if score > 0:
                results.append((score, tool))

    results.sort(key=lambda x: (-x[0], -x[1]["stars"]))
    return results
