#!/usr/bin/env python3
import re, subprocess, sys, os

CA_VAULT = "/mnt/c/Users/Channa/Documents/Life/Notes/Computer_Architecture"
CA_LEGACY = "/mnt/c/Users/Channa/Documents/Life/Notes/Computer_Architecture/misc/legacy"
DD_VAULT = "/mnt/c/Users/Channa/Documents/Life/Notes/Digital_Design"
PANDOC = os.environ.get("PANDOC", "pandoc")  # pandoc >= 3.x; set PANDOC env var to a portable binary if not installed

CA_SITE_DIR = "/home/govardhan/git/govardhnn.github.io/notes/computer-architecture"
DD_SITE_DIR = "/home/govardhan/git/govardhnn.github.io/notes/digital-design"

CA_SECTION = "Computer Architecture"
DD_SECTION = "Digital Design"

# (vault, filename, title, slug, section, site_dir) -- in Index.md reading order
NOTES = [
    (CA_VAULT, "Index.md", "Index", "index", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "History of Computing.md", "History of Computing", "history-of-computing", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Flynn's Taxonomy.md", "Flynn's Taxonomy", "flynns-taxonomy", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Floating Point Architecture.md", "Floating Point Architecture", "floating-point-architecture", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Simple Instruction Pipeline.md", "Simple Instruction Pipeline", "simple-instruction-pipeline", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Branch Prediction.md", "Branch Prediction", "branch-prediction", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Caches and Virtual Memory.md", "Caches and Virtual Memory", "caches-and-virtual-memory", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Multicore Cache Coherence.md", "Multicore Cache Coherence", "multicore-cache-coherence", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Memory Model.md", "Memory Model", "memory-model", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Advanced Superscalar Architectures.md", "Advanced Superscalar Architectures", "advanced-superscalar-architectures", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Out of Order Execution and Register Renaming.md", "Out of Order Execution and Register Renaming", "out-of-order-execution-and-register-renaming", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Exceptions.md", "Exceptions", "exceptions", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "RISC-V ISA.md", "RISC-V ISA", "risc-v-isa", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Main Memory and Storage.md", "Main Memory and Storage", "main-memory-and-storage", CA_SECTION, CA_SITE_DIR),
    (CA_VAULT, "Deep Learning Accelerators.md", "Deep Learning Accelerators", "deep-learning-accelerators", CA_SECTION, CA_SITE_DIR),

    (DD_VAULT, "Index.md", "Index", "index", DD_SECTION, DD_SITE_DIR),
    (DD_VAULT, "Boolean Algebra.md", "Boolean Algebra", "boolean-algebra", DD_SECTION, DD_SITE_DIR),
    (DD_VAULT, "Combinational Circuits.md", "Combinational Circuits", "combinational-circuits", DD_SECTION, DD_SITE_DIR),
    (DD_VAULT, "Sequential Circuits.md", "Sequential Circuits", "sequential-circuits", DD_SECTION, DD_SITE_DIR),
    (DD_VAULT, "RTL Design Guide.md", "RTL Design Guide", "rtl-design-guide", DD_SECTION, DD_SITE_DIR),
    (DD_VAULT, "Synthesis, Timing and Power.md", "Synthesis, Timing and Power", "synthesis-timing-and-power", DD_SECTION, DD_SITE_DIR),
]

# title -> (section, slug, site_dir)  -- used to resolve [[wikilinks]] across both vaults
TITLE_INDEX = {title: (section, slug, site_dir) for _, _, title, slug, section, site_dir in NOTES}

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
HR_LINE_RE = re.compile(r"^-{3,}\s*$")
# Drop the "Tools used: ..." line (and the now-orphaned hard-break at the
# end of the preceding "Author:" line) per user request -- keep just Author.
TOOLS_USED_RE = re.compile(r" {2}\nTools used:.*\n")

CALLOUT_HEAD_RE = re.compile(r"^> \[!(\w+)\][ \t]*(.*)$")

def convert_callouts(text):
    # Obsidian callouts ("> [!note] Title" + "> body") render natively in the
    # vault but would come out of pandoc as blockquotes with literal "[!note]"
    # text. Rewrite them as styled divs; pandoc parses the div body as
    # markdown (markdown_in_html_blocks), so math/links inside still work.
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        m = CALLOUT_HEAD_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        ctype = m.group(1).lower()
        title = m.group(2).strip() or ctype.capitalize()
        body = []
        i += 1
        while i < len(lines) and lines[i].startswith(">"):
            body.append(lines[i][1:].lstrip())
            i += 1
        out.append(f'<div class="callout callout-{ctype}">')
        out.append(f'<div class="callout-title">{title}</div>')
        out.append("")
        out.extend(body)
        out.append("")
        out.append("</div>")
    return "\n".join(out)

def resolve_wikilink(m):
    target = m.group(1).strip()
    display = (m.group(2) or target).strip()
    entry = TITLE_INDEX.get(target)
    if entry is None:
        # Target not published yet -- fall back to plain text, no dead link.
        return display
    section, slug, site_dir = entry
    # All notes share one notes.html sidebar/iframe host, so the same
    # "<section>/<title>" hash resolves a link regardless of which vault
    # (Computer Architecture or Digital Design) the target note lives in.
    href = f"../../notes.html#{section}/{target}".replace(" ", "%20")
    return f'<a href="{href}" target="_top">{display}</a>'

def isolate_hr_lines(text):
    # A "---" divider that directly follows a text line (no blank line
    # between) is ambiguous with CommonMark setext-heading underline syntax,
    # which swallows the preceding line into an <h2>. Force a blank line
    # before every standalone "---" so it's unambiguously a thematic break.
    lines = text.split("\n")
    out = []
    for line in lines:
        if HR_LINE_RE.match(line) and out and out[-1].strip() != "":
            out.append("")
        out.append(line)
    return "\n".join(out)

OVER_ACCENTS = ('<mo accent="true">¯</mo>',   # U+00AF from \overline
                '<mo accent="true">‾</mo>')   # U+203E from \bar

def convert_overlines(h):
    # Pandoc renders \overline / \bar as <mover> with a macron accent, which
    # browsers draw as a fixed-width mark instead of stretching it across the
    # base. Rewrite those movers as an mrow with a CSS top border, which
    # always spans the whole expression. Handles nested overlines.
    out = []
    i = 0
    while True:
        j = h.find('<mover>', i)
        if j == -1:
            out.append(h[i:])
            return ''.join(out)
        out.append(h[i:j])
        # find the matching </mover>, accounting for nesting
        depth, pos = 1, j + len('<mover>')
        while depth > 0:
            no = h.find('<mover>', pos)
            nc = h.find('</mover>', pos)
            if nc == -1:
                out.append(h[j:])
                return ''.join(out)
            if no != -1 and no < nc:
                depth += 1
                pos = no + len('<mover>')
            else:
                depth -= 1
                pos = nc + len('</mover>')
        inner = h[j + len('<mover>'):nc]
        acc = next((a for a in OVER_ACCENTS if inner.endswith(a)), None)
        if acc:
            base = inner[:-len(acc)]
            if base.startswith('<mrow>') and base.endswith('</mrow>'):
                base = base[len('<mrow>'):-len('</mrow>')]
            out.append('<mrow style="border-top:0.065em solid;padding-top:0.1em">'
                       + convert_overlines(base) + '</mrow>')
        else:
            out.append('<mover>' + convert_overlines(inner) + '</mover>')
        i = pos

def nav_href(section, title):
    return f"../../notes.html#{section}/{title}".replace(" ", "%20")

def nav_footer(idx):
    # Prev/next links following NOTES order, staying within one sidebar section.
    # Index pages are the hub and get no nav footer.
    _, _, _, slug, section, _ = NOTES[idx]
    if slug == "index":
        return ""
    parts = ['<div class="note-nav">']
    if idx > 0 and NOTES[idx - 1][4] == section:
        pt = NOTES[idx - 1][2]
        parts.append(f'<a class="nav-prev" href="{nav_href(section, pt)}" target="_top">&larr; {pt}</a>')
    else:
        parts.append('<span></span>')
    if idx + 1 < len(NOTES) and NOTES[idx + 1][4] == section:
        nt = NOTES[idx + 1][2]
        parts.append(f'<a class="nav-next" href="{nav_href(section, nt)}" target="_top">{nt} &rarr;</a>')
    else:
        parts.append('<span></span>')
    parts.append('</div>')
    return "\n".join(parts)

def main():
    for idx, (vault, filename, title, slug, section, site_dir) in enumerate(NOTES):
        os.makedirs(site_dir, exist_ok=True)
        src_path = os.path.join(vault, filename)
        with open(src_path, "r", encoding="utf-8") as f:
            text = f.read()

        # A stray leading space before the title "# " (seen in some vault
        # files) stops pandoc from recognizing it as an ATX heading.
        text = text.lstrip()

        text = isolate_hr_lines(text)
        text = TOOLS_USED_RE.sub("\n", text)
        text = convert_callouts(text)
        text = WIKILINK_RE.sub(resolve_wikilink, text)

        tmp_md = f"/tmp/{slug}.md"
        with open(tmp_md, "w", encoding="utf-8") as f:
            f.write(text)

        out_html = os.path.join(site_dir, f"{slug}.html")
        cmd = [
            # yaml_metadata_block off: guards against any "---"-delimited
            # block being misread as hidden YAML front-matter.
            # multiline_tables off: guards against a tight list/paragraph
            # run getting misparsed as a table (bit us once before).
            PANDOC, "-f", "markdown-yaml_metadata_block-multiline_tables", "-t", "html5", "--mathml", "-s",
            "--toc", "--toc-depth=2",
            "-c", "style.css",
            "--metadata", f"pagetitle={title}",
            "-o", out_html, tmp_md,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FAILED: {filename}\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
        if result.stderr.strip():
            print(f"WARN ({filename}): {result.stderr.strip()}")

        with open(out_html, "r", encoding="utf-8") as f:
            html = f.read()
        html = convert_overlines(html)
        html = html.replace("</body>", nav_footer(idx) + "\n</body>", 1)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"OK  {filename} -> {os.path.basename(site_dir)}/{slug}.html")

H2_RE = re.compile(r'<h2 id="[^"]*"[^>]*>(.*?)</h2>', re.S)
TAG_RE = re.compile(r"<[^>]+>")

def note_sections(site_dir, slug):
    with open(os.path.join(site_dir, f"{slug}.html"), encoding="utf-8") as f:
        html = f.read()
    out = []
    for h in H2_RE.findall(html):
        text = " ".join(TAG_RE.sub("", h).split())
        if text and text != "References":
            out.append(text)
    return out

def add_index_subtopics():
    # On each Index page, expand every reading-list entry with a collapsible
    # list of that note's h2 sections. Only touches anchors inside <li> items
    # (the CA index also links DD notes from a paragraph; those are skipped).
    import html as htmlmod
    for site_dir in {CA_SITE_DIR, DD_SITE_DIR}:
        idx_path = os.path.join(site_dir, "index.html")
        with open(idx_path, encoding="utf-8") as f:
            page = f.read()
        for _, _, title, slug, section, nsite in NOTES:
            if slug == "index":
                continue
            href = f"../../notes.html#{section}/{title}".replace(" ", "%20")
            pos = page.find(f'href="{href}"')
            if pos == -1:
                continue
            close = page.find("</li>", pos)
            if close == -1:
                continue
            between = page[pos:close]
            if "</ol>" in between or "</ul>" in between or "<h2" in between:
                continue  # anchor not inside a list item
            secs = note_sections(nsite, slug)
            if not secs:
                continue
            items = "".join(f"<li>{htmlmod.escape(t)}</li>" for t in secs)
            details = ('<details class="subtopics"><summary>sections</summary>'
                       f"<ul>{items}</ul></details>")
            page = page[:close] + details + page[close:]
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(page)
        print(f"OK  subtopics -> {os.path.basename(site_dir)}/index.html")

if __name__ == "__main__":
    main()
    add_index_subtopics()
