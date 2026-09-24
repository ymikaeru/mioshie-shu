"""Leitura mínima de .docx (sem dependências): lista de (estilo, texto) por parágrafo."""
import html
import re
import zipfile

P_RE = re.compile(r'<w:p[ >].*?</w:p>', re.S)
STYLE_RE = re.compile(r'<w:pStyle w:val="([^"]+)"')
TOKEN_RE = re.compile(r'<w:t(?: [^>]*)?>([^<]*)</w:t>|<w:tab/>|<w:br/>')


def paragraphs(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf8')
    out = []
    for p in P_RE.findall(xml):
        m = STYLE_RE.search(p)
        style = m.group(1) if m else ''
        parts = []
        for t in TOKEN_RE.finditer(p):
            tok = t.group(0)
            if tok == '<w:tab/>':
                parts.append(' ')
            elif tok == '<w:br/>':
                parts.append('\n')
            else:
                parts.append(t.group(1))
        text = html.unescape(''.join(parts)).strip()
        if text:
            out.append((style, text))
    return out
