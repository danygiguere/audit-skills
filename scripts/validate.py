#!/usr/bin/env python3
"""Package validator for audit-skills.

Maintainer tooling only — NOT part of what users install. Consumers of this
package copy the `.agents/` folder (pure markdown; nothing executes); this
script exists so maintainers and CI can verify the package before a release.
Requires only the Python standard library.

Checks, from the repo root:
  1. Every SKILL.md has valid frontmatter (name matches folder, spec name
     format, spec length limits).
  2. Every relative markdown link in the skills tree resolves.
  3. Routing tables stay in sync: the router's "What to load", the AGENTS.md
     "Deep checklists" table, the README catalog, and the files on disk all
     describe the same set of knowledge files.
  4. Every checklist carries the "recognition vocabulary" glossary note.
  5. Every checklist follows the template (required sections) and every
     glossary table covers all eight ecosystems.
  6. Wrapper coverage is bidirectional: every wrapper points at a real file
     AND every knowledge file has a wrapper.
  7. README counts (badge, invariants, checklists) match the topic count,
     and the AGENTS.md digest has one invariant bullet per topic.
  8. VERSION is semver and every version stamp anywhere in the repo
     (vX.Y.Z mentions, `version:` frontmatter fields) matches it.
  9. Remediation pointers are bidirectional: every checklist that cites a
     remediation playbook is named in that playbook's Scope, and every topic
     named in a Scope cites that playbook back.

Run: python3 scripts/validate.py
"""
import os
import re
import sys

BASE = ".agents/skills"
REFS = os.path.join(BASE, "audit", "references")
ECOSYSTEMS = ["Rails", "Laravel", "Django", "Spring", "Node/Express",
              "Vapor", ".NET", "Go"]
REQUIRED_SECTIONS = ["## Invariant", "## Why it happens",
                     "## Detection smells", "## Concept glossary",
                     "## Example", "## Severity guidance"]
problems: list[str] = []


def topic_files() -> set[str]:
    """Knowledge files relative to REFS, excluding internal methodology."""
    out = set()
    for root, _, files in os.walk(REFS):
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), REFS)
                if not rel.startswith("methodology/"):
                    out.add(rel)
    return out


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
        n = name.group(1).strip()
        if n != d:
            problems.append(f"{sk}: name does not match folder")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n):
            problems.append(f"{sk}: name violates spec format")
        if len(n) > 64:
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


def check_table_sync() -> None:
    """The three routing surfaces and the disk must agree."""
    disk = topic_files() | {
        os.path.relpath(os.path.join(r, f), REFS)
        for r, _, fs in os.walk(os.path.join(REFS, "methodology"))
        for f in fs if f.endswith(".md")
    }
    router_src = open(os.path.join(BASE, "audit", "SKILL.md")).read()
    router = set(re.findall(r"`references/([\w./-]+\.md)`", router_src))
    agents = set(re.findall(r"`([\w-]+/[\w.-]+\.md)`", open("AGENTS.md").read()))
    readme = set(re.findall(
        r"\]\(\.agents/skills/audit/references/([\w./-]+\.md)\)",
        open("README.md").read()))

    def diff(label_a, a, label_b, b):
        for missing in sorted(a - b):
            problems.append(f"table sync: {missing} in {label_a} but not {label_b}")
        for missing in sorted(b - a):
            problems.append(f"table sync: {missing} in {label_b} but not {label_a}")

    diff("disk", disk, "router table", router)
    diff("router table", router, "AGENTS.md table", agents)
    expected_readme = {p for p in router if not p.startswith("methodology/")}
    diff("router (minus methodology)", expected_readme, "README catalog", readme)


def check_glossary_note() -> int:
    note = "Recognition vocabulary, not a support list"
    count = 0
    for rel in sorted(topic_files()):
        count += 1
        if note not in open(os.path.join(REFS, rel)).read():
            problems.append(f"{rel}: missing glossary note")
    return count


def check_templates() -> None:
    """Checklists follow the template; all glossaries cover all ecosystems."""
    for rel in sorted(topic_files()):
        text = open(os.path.join(REFS, rel)).read()
        if not rel.startswith("remediation/"):
            for section in REQUIRED_SECTIONS:
                if f"\n{section}" not in text and not text.startswith(section):
                    problems.append(f"{rel}: missing section '{section}'")
        for eco in ECOSYSTEMS:
            if not re.search(rf"^\| {re.escape(eco)}\s", text, re.M):
                problems.append(f"{rel}: glossary missing ecosystem row '{eco}'")


def check_wrapper_coverage() -> int:
    """Every wrapper points at a real file; every knowledge file has a wrapper."""
    referenced = set()
    wrappers = 0
    for d in sorted(os.listdir(BASE)):
        if not d.startswith("audit-"):
            continue
        sk = os.path.join(BASE, d, "SKILL.md")
        if not os.path.isfile(sk):
            continue
        wrappers += 1
        for link in re.findall(r"`\.\./audit/references/([\w./-]+\.md)`",
                               open(sk).read()):
            referenced.add(link)
    # methodology/ is shared plumbing every wrapper cites, not a topic
    referenced = {r for r in referenced if not r.startswith("methodology/")}
    disk = topic_files()
    for missing in sorted(disk - referenced):
        problems.append(f"wrapper coverage: {missing} has no wrapper skill")
    for ghost in sorted(referenced - disk):
        problems.append(f"wrapper coverage: wrapper references missing file {ghost}")
    return wrappers


def check_counts() -> int:
    """README numbers and digest bullets must equal the topic count."""
    topics = len({t for t in topic_files() if not t.startswith("remediation/")})
    readme = open("README.md").read()
    badge = re.search(r"audits-(\d+)-success", readme)
    if not badge or int(badge.group(1)) != topics:
        problems.append(f"counts: README badge != {topics} topics")
    for label, pattern in [("invariants", r"all (\d+) invariants"),
                           ("checklists", r"all (\d+) checklists")]:
        m = re.search(pattern, readme)
        if not m or int(m.group(1)) != topics:
            problems.append(f"counts: README 'all N {label}' != {topics}")
    agents = open("AGENTS.md").read()
    section = agents.split("## Invariants")[1].split("## Deep checklists")[0]
    bullets = len(re.findall(r"^- \*\*", section, re.M))
    if bullets != topics:
        problems.append(f"counts: AGENTS.md has {bullets} invariant bullets, "
                        f"expected {topics}")
    return topics


def _section(text: str, header: str) -> str:
    """Return the body of a '## Header' section, up to the next '## ' heading."""
    m = re.search(rf"^{re.escape(header)}\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def check_remediation_scope() -> None:
    """Topic<->playbook pointers must be bidirectional: every checklist that
    cites a remediation playbook is named in that playbook's Scope, and every
    topic named in a Scope cites that playbook back. Convention until now —
    the link resolving (check 2) does not prove the Scope lists it."""
    all_topics = topic_files()
    playbooks = {t for t in all_topics if t.startswith("remediation/")}
    checklists = all_topics - playbooks

    # checklist -> the playbooks it cites (any `../remediation/X.md` link)
    cites: dict[str, set[str]] = {}
    for rel in checklists:
        text = open(os.path.join(REFS, rel)).read()
        named = {f"remediation/{m}"
                 for m in re.findall(r"`\.\./remediation/([\w.-]+\.md)`", text)}
        for ghost in named - playbooks:
            problems.append(f"remediation scope: {rel} cites missing playbook {ghost}")
        cites[rel] = named & playbooks

    # playbook -> the checklists named in its Scope section
    scope: dict[str, set[str]] = {}
    for pb in playbooks:
        body = _section(open(os.path.join(REFS, pb)).read(), "## Scope")
        scope[pb] = {m for m in re.findall(r"`\.\./([\w./-]+\.md)`", body)
                     if m in checklists}

    for rel, pbs in cites.items():
        for pb in pbs:
            if rel not in scope.get(pb, set()):
                problems.append(f"remediation scope: {rel} cites {pb} but is "
                                f"not named in its Scope section")
    for pb, named in scope.items():
        for rel in named:
            if pb not in cites.get(rel, set()):
                problems.append(f"remediation scope: {pb} Scope names {rel} but "
                                f"{rel} does not cite {pb}")


def check_version() -> str:
    """VERSION is canonical; every stamp anywhere in the repo must match it."""
    v = open("VERSION").read().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        problems.append(f"version: VERSION '{v}' is not X.Y.Z semver")
    stamps = 0
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".idea", ".vscode")]
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            text = open(p).read()
            for hit in re.findall(r"\bv(\d+\.\d+\.\d+)\b", text):
                stamps += 1
                if hit != v:
                    problems.append(f"version: {p} stamps v{hit}, VERSION is {v}")
            for hit in re.findall(r"^version: (.+)$", text, re.M):
                stamps += 1
                if hit.strip() != v:
                    problems.append(f"version: {p} frontmatter '{hit.strip()}', "
                                    f"VERSION is {v}")
    if stamps == 0:
        problems.append("version: no stamps found anywhere — footers missing?")
    return v


def main() -> int:
    skills = check_frontmatter()
    links = check_links()
    check_table_sync()
    noted = check_glossary_note()
    check_templates()
    check_remediation_scope()
    wrappers = check_wrapper_coverage()
    topics = check_counts()
    version = check_version()
    print(f"version: {version}, topics: {topics}, skills: {skills}, "
          f"wrappers: {wrappers}, links checked: {links}, noted files: {noted}")
    if problems:
        for p in problems:
            print(f"  - {p}")
        print("FAILED")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
