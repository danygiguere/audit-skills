#!/usr/bin/env python3
"""Package validator for audit-skills.

Maintainer tooling only — NOT part of what users install. Consumers of this
package copy the `.agents/` folder (pure markdown; nothing executes); this
script exists so maintainers and CI can verify the package before a release.
Requires only the Python standard library.

Checks, from the repo root:
  1. Every SKILL.md has valid frontmatter (name matches folder, spec limits).
  2. Every relative markdown link in the skills tree resolves.
  3. Routing tables stay in sync: the router's "What to load", the AGENTS.md
     "Deep checklists" table, the README catalog, and the files on disk all
     describe the same set of knowledge files.
  4. Every checklist carries the "recognition vocabulary" glossary note.

Run: python3 scripts/validate.py
"""
import os
import re
import sys

BASE = ".agents/skills"
REFS = os.path.join(BASE, "audit", "references")
problems: list[str] = []


def check_frontmatter() -> int:
    count = 0
    for d in sorted(os.listdir(BASE)):
        sk = os.path.join(BASE, d, "SKILL.md")
        if not os.path.isfile(sk):
            continue
        count += 1
        text = open(sk).read()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        fm = m.group(1) if m else ""
        name = re.search(r"^name: (.+)$", fm, re.M)
        desc = re.search(r"^description: (.+)$", fm, re.M)
        if not (m and name and desc):
            problems.append(f"{sk}: missing or malformed frontmatter")
            continue
        if name.group(1).strip() != d:
            problems.append(f"{sk}: name does not match folder")
        if len(name.group(1).strip()) > 64:
            problems.append(f"{sk}: name exceeds 64 chars")
        if len(desc.group(1).strip()) > 1024:
            problems.append(f"{sk}: description exceeds 1024 chars")
    return count


def check_links() -> int:
    count = 0
    for root, _, files in os.walk(BASE):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            pattern = r"`((?:\.\./)+[\w./-]+\.md|references/[\w./-]+\.md)`"
            for link in re.findall(pattern, open(p).read()):
                count += 1
                target = os.path.normpath(os.path.join(os.path.dirname(p), link))
                if not os.path.isfile(target):
                    problems.append(f"{p}: broken link -> {link}")
    for link in re.findall(r"\]\((\.agents/[^)]+\.md)\)", open("README.md").read()):
        count += 1
        if not os.path.isfile(link):
            problems.append(f"README.md: broken link -> {link}")
    return count


def table_sets() -> None:
    """The three routing surfaces and the disk must agree."""
    disk = set()
    for root, _, files in os.walk(REFS):
        for f in files:
            if f.endswith(".md"):
                disk.add(os.path.relpath(os.path.join(root, f), REFS))

    router_src = open(os.path.join(BASE, "audit", "SKILL.md")).read()
    router = set(re.findall(r"`references/([\w./-]+\.md)`", router_src))

    agents = set(re.findall(r"`([\w-]+/[\w.-]+\.md)`", open("AGENTS.md").read()))

    readme = set(
        re.findall(r"\]\(\.agents/skills/audit/references/([\w./-]+\.md)\)",
                   open("README.md").read())
    )

    def diff(label_a, a, label_b, b):
        for missing in sorted(a - b):
            problems.append(f"table sync: {missing} in {label_a} but not {label_b}")
        for missing in sorted(b - a):
            problems.append(f"table sync: {missing} in {label_b} but not {label_a}")

    diff("disk", disk, "router table", router)
    diff("router table", router, "AGENTS.md table", agents)
    # README catalog lists checklists + remediation, not internal methodology.
    expected_readme = {p for p in router if not p.startswith("methodology/")}
    diff("router (minus methodology)", expected_readme, "README catalog", readme)


def check_glossary_note() -> int:
    note = "Recognition vocabulary, not a support list"
    count = 0
    for root, _, files in os.walk(REFS):
        if os.path.basename(root) == "methodology":
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            count += 1
            if note not in open(os.path.join(root, f)).read():
                problems.append(f"{os.path.join(root, f)}: missing glossary note")
    return count


def check_version() -> str:
    """VERSION is canonical; the stamps in the traveling artifacts must match."""
    v = open("VERSION").read().strip()
    router = open(os.path.join(BASE, "audit", "SKILL.md")).read()
    m = re.search(r"^version: (.+)$", router, re.M)
    if not m or m.group(1).strip() != v:
        problems.append(f"version: audit/SKILL.md frontmatter does not match VERSION ({v})")
    if f"v{v}" not in router:
        problems.append(f"version: audit/SKILL.md footer missing v{v}")
    if f"v{v}" not in open("AGENTS.md").read():
        problems.append(f"version: AGENTS.md footer missing v{v}")
    return v


def main() -> int:
    skills = check_frontmatter()
    links = check_links()
    table_sets()
    noted = check_glossary_note()
    version = check_version()
    print(f"version: {version}, skills: {skills}, links checked: {links}, "
          f"checklist files with glossary note: {noted}")
    if problems:
        for p in problems:
            print(f"  - {p}")
        print("FAILED")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
