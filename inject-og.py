#!/usr/bin/env python3
"""Inject per-page Open Graph + Twitter Card meta into every HTML page of
eylenburg.github.io. Inserts a block after the existing author meta so each
page gets its own og:title/og:description/og:url. CRLF preserved."""
import html as htmlmod
import re, pathlib

ROOT = pathlib.Path("/home/paperclip/scratch/eylenburg.github.io")
SITE = "Eylenburg's Tech Website"
BASE = "https://eylenburg.github.io"

def html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def og_block(title, desc, url):
    return (
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="' + SITE + '">\n'
        '<meta property="og:title" content="' + title + '">\n'
        '<meta property="og:description" content="' + desc + '">\n'
        '<meta property="og:url" content="' + url + '">\n'
        '<meta property="og:image" content="' + BASE + '/og-image.png">\n'
        '<meta property="og:image:type" content="image/png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:title" content="' + title + '">\n'
        '<meta name="twitter:description" content="' + desc + '">\n'
        '<meta name="twitter:image" content="' + BASE + '/og-image.png">\n'
    )

files = sorted(ROOT.glob("*.htm")) + [ROOT / "index.html"]
changed = []
for f in files:
    raw = f.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    if had_bom:
        raw = raw[3:]
    text = raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    if "og:title" in text:
        print("SKIP (already has og):", f.name)
        continue
    # extract title and meta description
    m_title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    title = m_title.group(1).strip() if m_title else f.stem
    title = htmlmod.unescape(re.sub(r"\s+", " ", title))
    title = htmlmod.escape(title, quote=True)
    m_desc = re.search(r'<meta name="description" content="([^"]*)"', text, re.I)
    desc = m_desc.group(1).strip() if m_desc else title
    desc = htmlmod.unescape(re.sub(r"\s+", " ", desc))
    desc = htmlmod.escape(desc, quote=True)
    page = f.name if f.name != "index.html" else ""
    url = BASE + "/" + page if page else BASE + "/"
    block = og_block(title, desc, url)
    # anchor: insert after the author meta line (present on every page)
    anchor = re.search(r'<meta name="author" content="[^"]*"[^>]*>', text, re.I)
    if not anchor:
        print("ERROR no author anchor:", f.name)
        continue
    end = anchor.end()
    insert = "\n" + block.rstrip("\n") + "\n"
    text = text[:end] + insert + text[end:]
    out = raw[:0]  # BOM handled above
    out = (b"\xef\xbb\xbf" if had_bom else b"") + text.encode("utf-8")
    f.write_bytes(out)
    changed.append(f.name)

print("changed:", len(changed))
for c in changed:
    print(" -", c)