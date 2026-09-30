#!/usr/bin/env python3
"""Build the indexed note collections, their assets, and website navigation."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = '/mnt/c/Users/saigo/Documents/Life/Notes'
GROUPS = [('Digital_Design', 'Digital Design', 'digital-design'),
          ('Computer_Architecture', 'Computer Architecture', 'computer-architecture')]
WIKI = re.compile(r'\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]')
CALLOUT = re.compile(r'^>\s*\[!(\w+)\]\s*(.*)$')


def slug(title):
    # Keep existing URLs, notably flynns-taxonomy.html.
    return re.sub(r'[^a-z0-9]+', '-', title.lower().replace("'", '')).strip('-')


def catalogue(source):
    notes = []
    for folder, section, site_folder in GROUPS:
        directory = source / folder
        titles = ['Index']
        for line in (directory/'Index.md').read_text().splitlines():
            if re.match(r'^\s*(?:\d+\.|-)\s+', line):
                match = WIKI.search(line)
                if match and match[1] not in titles:
                    titles.append(match[1])
        for title in titles:
            path = directory/(title+'.md')
            if not path.is_file():
                raise ValueError(f'Indexed note does not exist: {path}')
            notes.append(dict(path=path, title=title, slug=slug(title),
                              section=section, folder=site_folder))
    outputs = [(n['folder'], n['slug']) for n in notes]
    if len(outputs) != len(set(outputs)):
        raise ValueError('Duplicate note output paths')
    return notes


def nav_href(note):
    return '../../notes.html#' + quote(note['section']+'/'+note['title'], safe='/')


def preprocess(text, note, notes):
    index = {n['title']: n for n in notes if n['title'] != 'Index'}
    index['Index'] = next(n for n in notes if n['title']=='Index' and n['section']==note['section'])

    def resolve(match):
        title = match[1].strip()
        if title not in index:
            raise ValueError(f"Unknown wikilink in {note['path'].name}: {title}")
        return (f'<a href="{html.escape(nav_href(index[title]), quote=True)}" target="_top">'
                + html.escape(match[2] or title) + '</a>')

    out = []
    fence = None
    callout = False
    for line in text.lstrip().splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker and not callout:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0]==fence[0] and len(token)>=len(fence):
                fence = None
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        if callout and not line.startswith('>'):
            out.extend(['::::', ''])
            callout = False
        match = CALLOUT.match(line)
        if match and not callout:
            kind = match[1].lower()
            out.extend([f':::: {{.callout .callout-{kind}}}', '::: callout-title',
                        match[2] or kind.capitalize(), ':::', ''])
            callout = True
            continue
        if callout:
            line = re.sub(r'^> ?', '', line)
        if line.startswith('Tools used:'):
            continue
        # Keep inline code examples literal, as well as fenced code above.
        pieces = re.split(r'(`+[^`]*`+)', line)
        line = ''.join(part if part.startswith('`') else WIKI.sub(resolve, part) for part in pieces)
        if re.fullmatch(r'-{3,}\s*', line) and out and out[-1].strip():
            out.append('')
        out.append(line)
    if callout:
        out.append('::::')
    return '\n'.join(out)+'\n'


def footer(note, notes):
    if note['title']=='Index':
        return ''
    group = [n for n in notes if n['section']==note['section']]
    i = group.index(note)
    out = ['<nav class="note-nav" aria-label="Adjacent notes">']
    adjacent = [(group[i-1] if i else None, 'nav-prev', '← ', ''),
                (group[i+1] if i+1<len(group) else None, 'nav-next', '', ' →')]
    for other, cls, before, after in adjacent:
        if other:
            out.append(f'<a class="{cls}" href="{html.escape(nav_href(other), quote=True)}" target="_top">'
                       + before+html.escape(other['title'])+after+'</a>')
        else:
            out.append('<span></span>')
    return '\n'.join(out+['</nav>'])


def render(note, notes, pandoc):
    text = preprocess(note['path'].read_text(), note, notes)
    title = note['section'] if note['title']=='Index' else note['title']
    result = subprocess.run([
        pandoc, '-f', 'markdown+fenced_divs-yaml_metadata_block-multiline_tables',
        '-t', 'html5', '--mathml', '-s', '--toc', '--toc-depth=2', '-c', 'style.css',
        '--metadata', 'pagetitle='+title, '--metadata', 'lang=en',
        '--lua-filter', str(REPO/'tools/public_note_links.lua')],
        input=text, capture_output=True, text=True)
    if result.returncode or result.stderr.strip():
        raise RuntimeError(f"Pandoc failed or warned for {note['path'].name}:\n{result.stderr}")
    page = convert_overlines(result.stdout)
    return page.replace('</body>', footer(note, notes)+'\n</body>', 1)


def add_subtopics(pages, notes):
    for hub in [n for n in notes if n['title']=='Index']:
        key = (hub['folder'], hub['slug'])
        page = pages[key]
        for note in [n for n in notes if n['section']==hub['section'] and n['title']!='Index']:
            body = pages[(note['folder'],note['slug'])]
            headings = re.findall(r'<h2\b[^>]*>(.*?)</h2>', body, re.S)
            labels = [html.unescape(re.sub('<[^>]+>', '', h)).strip() for h in headings]
            labels = [label for label in labels if label and label!='References']
            if not labels:
                continue
            details = '<details class="subtopics"><summary>sections</summary><ul>'
            details += ''.join('<li>'+html.escape(label)+'</li>' for label in labels)+'</ul></details>'
            anchor = 'href="'+html.escape(nav_href(note), quote=True)+'"'
            pattern = r'(<li>\s*<a '+re.escape(anchor)+r'[^>]*>.*?)(</li>)'
            page = re.sub(pattern, lambda m:m[1]+details+m[2], page, count=1, flags=re.S)
        pages[key] = page


def sidebar(notes, site):
    groups = []
    for _, section, folder in GROUPS:
        groups.append(dict(label=section, notes=[dict(title=n['title'], file=f'notes/{folder}/{n["slug"]}.html')
                                                for n in notes if n['section']==section]))
    text = (site/'notes.html').read_text()
    declaration = 'const SECTIONS = '+json.dumps(groups, indent=4, ensure_ascii=False)+';'
    text, count = re.subn(r'const SECTIONS = \[.*?\];', lambda _:declaration, text, count=1, flags=re.S)
    if count!=1:
        raise ValueError('Cannot locate SECTIONS in notes.html')
    return text


def asset_copies(note, output, site):
    figures = note['path'].parent/'figs'
    files = []
    if figures.is_dir():
        files += [(f, output/'figs'/f.name) for f in figures.iterdir()
                  if f.is_file() and f.suffix.lower() in {'.svg','.png','.jpg','.jpeg','.gif','.webp'}]
    files.append((note['path'].parent/'LICENSE', output/'LICENSE.txt'))
    files.append((site/'notes'/note['folder']/'style.css', output/'style.css'))
    for src, dst in files:
        if not src.is_file():
            raise ValueError(f'Missing asset: {src}')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='*', type=Path, help='Optional indexed notes to build individually')
    parser.add_argument('--source-root', type=Path, default=Path(os.environ.get('NOTES_SOURCE_ROOT', DEFAULT_SOURCE)))
    parser.add_argument('--site-root', type=Path, default=REPO, help='Website checkout (default: this repository)')
    parser.add_argument('-o', '--output-dir', type=Path, help='Output directory for individual inputs')
    args = parser.parse_args()
    if args.output_dir and not args.inputs:
        parser.error('-o requires individual inputs')
    notes = catalogue(args.source_root)
    selected = notes
    if args.inputs:
        selected = []
        for path in args.inputs:
            match = next((n for n in notes if path.is_file() and os.path.samefile(n['path'], path)), None)
            if match is None:
                parser.error(f'Input must appear in a source index: {path}')
            if match not in selected:
                selected.append(match)
        if args.output_dir and len({n['folder'] for n in selected})>1:
            parser.error('-o cannot combine sections with potentially colliding figures/indexes')
    site = args.site_root.resolve()
    # Convert all selected pages before writing, so malformed source cannot cause a partial render.
    pages = {(n['folder'],n['slug']): render(n, notes, os.environ.get('PANDOC','pandoc')) for n in selected}
    assets = []
    for folder in {n['folder'] for n in selected}:
        note = next(n for n in selected if n['folder']==folder)
        output = args.output_dir.resolve() if args.output_dir else site/'notes'/folder
        assets += asset_copies(note, output, site)
    if not args.inputs:
        add_subtopics(pages, notes)
        host = sidebar(notes, site)
    for (folder, name), page in pages.items():
        output = args.output_dir.resolve() if args.output_dir else site/'notes'/folder
        output.mkdir(parents=True, exist_ok=True)
        (output/(name+'.html')).write_text(page)
        print(f'Built {folder}/{name}.html')
    for src, dst in assets:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or not os.path.samefile(src,dst):
            shutil.copy2(src,dst)
    if not args.inputs:
        (site/'notes.html').write_text(host)
    print(f'Built {len(pages)} pages'+(' and updated navigation.' if not args.inputs else '.'))


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


if __name__ == "__main__":
    main()
