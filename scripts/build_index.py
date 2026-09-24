"""Gera os dados do site a partir de data/vols, data/articles.json, data/tags.json e data/glossario.json.

Saídas:
  data/index.json            índice leve de trechos, artigos, temas, glossário e relacionados
  data/artigos/<id>.json     texto completo de cada artigo (PT + JP)
  reports/validacao.html     datas incertas, referências não ligadas, trechos sem tema
"""
import difflib
import glob
import html
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from dates import sem_acento  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


def carregar(nome, padrao=None):
    caminho = os.path.join(DATA, nome)
    if not os.path.exists(caminho):
        return padrao
    return json.load(open(caminho, encoding='utf8'))


def norm(s):
    s = sem_acento(s or '').lower()
    s = re.sub(r'^(cap[ií]tulo d[ao] \w+|\[cole[cç][aã]o\]|cole[cç][aã]o|ensaio|artigo)\s*[:\-–]\s*', '', s)
    s = re.sub(r'\((?:parte )?\d+\)|\(reitera[cç][aã]o.*?\)|\(i+\)', '', s)
    return re.sub(r'[^\w]+', ' ', s).strip()


# ---------- referências a artigos ----------
REF_TITULO = re.compile(r'[「〔]\s*⇒?\s*([^」〕]+?)\s*[」〕]|\[\s*⇒?\s*["“]?([^\]"”]+?)["”]?\s*\]|["“]\s*⇒?\s*([^"”]+?)\s*["”]|⇒\s*([^"”」〕\]【()]+)')
SO_NUMERO = re.compile(r'^Eik\w*,?\s*n\.?\s?º\s*(\d+)$', re.I)
PUB = re.compile(r'n\.?\s?º\s*(\d+)', re.I)


def titulos_citados(texto, so_seta=False):
    """Títulos citados num parágrafo; em falas (so_seta) só valem as citações marcadas com ⇒."""
    out = []
    for m in REF_TITULO.finditer(texto):
        if so_seta and '⇒' not in m.group(0):
            continue
        t = next(g for g in m.groups() if g).strip(' ⇒"“”.,')
        for parte in re.split(r',\s*⇒\s*', t):  # "Introdução, ⇒ O que é Doença?, ⇒ ..."
            parte = parte.strip(' ⇒"“”.,')
            if parte and not re.match(r'^(Nota|Refer)', parte, re.I) and len(parte) > 2:
                out.append(parte)
    return out


def ligar_refs(trecho, artigos_por_vol, todos):
    ligados, nao_ligados = [], []
    for p in trecho['paras']:
        if p['t'] != 'ref' and '⇒' not in p['x']:
            continue
        pubs = {int(x) for x in PUB.findall(p['x'])}
        for tit in titulos_citados(p['x'], so_seta=p['t'] != 'ref'):
            so_num = SO_NUMERO.match(tit)
            if so_num:
                alvo = artigo_por_numero(int(so_num.group(1)), trecho['vol'], artigos_por_vol)
            else:
                alvo = melhor_artigo(tit, pubs, trecho['vol'], artigos_por_vol, todos)
            if alvo:
                if alvo not in ligados:
                    ligados.append(alvo)
            else:
                nao_ligados.append(tit)
    return ligados, nao_ligados


def artigo_por_numero(num, vol, artigos_por_vol):
    for v in (vol, vol - 1, vol + 1):
        for a in artigos_por_vol.get(v, []):
            pa = PUB.search(a['fonte'] or '')
            if pa and int(pa.group(1)) == num:
                return a['id']
    return None


def melhor_artigo(titulo, pubs, vol, artigos_por_vol, todos):
    alvo_n = norm(titulo)
    melhor, nota = None, 0.0
    for v_delta, candidatos in ((0, artigos_por_vol.get(vol, [])),
                                (1, artigos_por_vol.get(vol - 1, []) + artigos_por_vol.get(vol + 1, [])),
                                (2, todos)):
        for a in candidatos:
            nomes = [norm(x) for x in [a['titulo']] + a.get('aliases', []) + [c['titulo'] for c in a['complementos']]]
            s = max(difflib.SequenceMatcher(None, alvo_n, n).ratio() for n in nomes)
            if any(alvo_n and (alvo_n in n or n in alvo_n) and len(n) > 4 for n in nomes):
                s = max(s, 0.85)
            if a['titulo_ja'] and titulo == a['titulo_ja']:
                s = 1.0
            pa = PUB.search(a['fonte'] or '')
            if pubs and pa and int(pa.group(1)) in pubs:
                s += 0.25
            s -= 0.08 * v_delta
            if s > nota:
                melhor, nota = a['id'], s
        if nota >= 0.62:
            return melhor
    return None


# ---------- relacionados ----------
def relacionados(trechos, tags, k=6):
    """Semelhança por temas (peso por posição) + palavras-chave + vocabulário do texto (tf-idf leve)."""
    vocab_doc = {}
    df = Counter()
    for t in trechos:
        palavras = re.findall(r'\w{5,}', sem_acento(' '.join(p['x'] for p in t['paras'])).lower())
        c = Counter(palavras)
        vocab_doc[t['id']] = c
        df.update(c.keys())
    n = len(trechos)
    vetores = {}
    for tid, c in vocab_doc.items():
        v = {w: (1 + math.log(f)) * math.log(n / df[w]) for w, f in c.items() if 2 <= df[w] <= n * 0.15}
        top = dict(sorted(v.items(), key=lambda x: -x[1])[:60])
        norma = math.sqrt(sum(x * x for x in top.values())) or 1
        vetores[tid] = {w: x / norma for w, x in top.items()}
    por_palavra = defaultdict(set)
    for tid, v in vetores.items():
        for w in v:
            por_palavra[w].add(tid)
    data = {t['id']: t['data'] for t in trechos}
    out = {}
    for t in trechos:
        a = t['id']
        ta = tags.get(a, {})
        temas_a = {x: 1 / (i + 1) for i, x in enumerate(ta.get('temas', []))}
        kw_a = {sem_acento(x).lower() for x in ta.get('palavras', [])}
        candidatos = set()
        for w in vetores[a]:
            candidatos |= por_palavra[w]
        notas = []
        for b in candidatos:
            if b == a or data[b] == data[a]:
                continue  # relacionados = outros dias
            cos = sum(x * vetores[b].get(w, 0) for w, x in vetores[a].items())
            tb = tags.get(b, {})
            temas = sum(temas_a.get(x, 0) / (i + 1) for i, x in enumerate(tb.get('temas', [])))
            kw = len(kw_a & {sem_acento(x).lower() for x in tb.get('palavras', [])})
            notas.append((cos + 0.25 * temas + 0.2 * kw, b))
        out[a] = [b for s, b in sorted(notas, reverse=True)[:k] if s > 0.12]
    return out


# ---------- glossário ----------
def ocorrencias_glossario(glossario, trechos):
    for g in glossario:
        padrao = re.compile(r'\b(?:' + '|'.join(re.escape(sem_acento(x).lower()) for x in [g['termo']] + g.get('variantes', [])) + r')\b')
        g['trechos'] = [t['id'] for t in trechos
                        if padrao.search(sem_acento(t['titulo'] + ' ' + ' '.join(p['x'] for p in t['paras'])).lower())]
    return glossario


def main():
    tax = carregar('taxonomy.json')
    tags = carregar('tags.json', {})
    artigos = carregar('articles.json')
    glossario = carregar('glossario.json', [])
    vols = [json.load(open(f, encoding='utf8')) for f in sorted(glob.glob(os.path.join(DATA, 'vols', 'vol*.json')))]
    trechos = [t for v in vols for t in v['trechos']]

    artigos_por_vol = defaultdict(list)
    for a in artigos:
        if a['titulo']:
            artigos_por_vol[a['vol']].append(a)
    com_titulo = [a for a in artigos if a['titulo'] or a['titulo_ja']]

    lidos_em = defaultdict(list)
    nao_ligados = []
    refs = {}
    for t in trechos:
        lig, nl = ligar_refs(t, artigos_por_vol, com_titulo)
        refs[t['id']] = lig
        for a in lig:
            lidos_em[a].append(t['id'])
        nao_ligados += [(t['id'], x) for x in nl]

    rel = relacionados(trechos, tags)
    glossario = ocorrencias_glossario(glossario, trechos)

    idx = {
        'temas': tax['temas'], 'grupos': tax['grupos'], 'formatos': tax['formatos'],
        'trechos': [{
            'id': t['id'], 'v': t['vol'], 'n': t['n'], 'd': t['data'], 't': t['titulo'],
            'f': t['formatos'], 'tm': tags.get(t['id'], {}).get('temas', []),
            'kw': tags.get(t['id'], {}).get('palavras', []), 'a': refs[t['id']], 'r': rel[t['id']],
            'l': t['local'], 'inc': t['conflito'], 'c': sum(len(p['x']) for p in t['paras']),
        } for t in trechos],
        'artigos': [{
            'id': a['id'], 'v': a['vol'], 't': a['titulo'], 'tj': a['titulo_ja'], 'fonte': a['fonte'],
            'lidos': lidos_em.get(a['id'], []),
        } for a in artigos],
        'glossario': [{'termo': g['termo'], 'def': g['def'], 'ids': g['trechos']} for g in glossario],
    }
    with open(os.path.join(DATA, 'index.json'), 'w', encoding='utf8') as f:
        json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))

    os.makedirs(os.path.join(DATA, 'artigos'), exist_ok=True)
    for a in artigos:
        with open(os.path.join(DATA, 'artigos', f"{a['id']}.json"), 'w', encoding='utf8') as f:
            json.dump(a, f, ensure_ascii=False, separators=(',', ':'))

    relatorio(trechos, tags, nao_ligados, idx)
    relatorio_classificacao(trechos, tags, tax)
    print(f"trechos {len(trechos)} | com tema {sum(1 for t in trechos if tags.get(t['id']))} | "
          f"refs ligadas {sum(len(x) for x in refs.values())} | não ligadas {len(nao_ligados)} | "
          f"artigos lidos {len(lidos_em)}/{len(artigos)} | glossário {len(glossario)}")


def relatorio(trechos, tags, nao_ligados, idx):
    esc = html.escape
    linhas = ['<!doctype html><meta charset="utf-8"><title>Validação Mioshie-shu</title>',
              '<style>body{font:14px system-ui;margin:2rem;max-width:1100px}td{border-bottom:1px solid #ddd;padding:3px 8px}</style>',
              '<h1>Validação dos dados</h1>']
    por_vol = Counter(t['vol'] for t in trechos)
    linhas.append(f'<p>Total de trechos: <b>{len(trechos)}</b> em {len(por_vol)} volumes.</p>')
    inc = [t for t in trechos if t['conflito']]
    linhas.append(f'<h2>Datas a revisar ({len(inc)})</h2><table>')
    linhas += [f"<tr><td>{t['id']}</td><td>{t['data']}</td><td>{esc(t['conflito'])}</td><td>{esc(t['titulo'])}</td></tr>" for t in inc]
    linhas.append('</table>')
    sem = [t for t in trechos if not tags.get(t['id'])]
    linhas.append(f'<h2>Trechos sem tema ({len(sem)})</h2><p>' + ' '.join(t['id'] for t in sem) + '</p>')
    linhas.append(f'<h2>Referências não ligadas a artigo ({len(nao_ligados)})</h2><table>')
    linhas += [f'<tr><td>{i}</td><td>{esc(x)}</td></tr>' for i, x in nao_ligados]
    linhas.append('</table>')
    nunca = [a for a in idx['artigos'] if not a['lidos']]
    linhas.append(f'<h2>Artigos sem trecho ligado ({len(nunca)})</h2><table>')
    linhas += [f"<tr><td>{a['id']}</td><td>{esc(a['t'] or '')}</td><td>{esc(a['tj'] or '')}</td></tr>" for a in nunca]
    linhas.append('</table>')
    os.makedirs(os.path.join(ROOT, 'reports'), exist_ok=True)
    with open(os.path.join(ROOT, 'reports', 'validacao.html'), 'w', encoding='utf8') as f:
        f.write('\n'.join(linhas))


def relatorio_classificacao(trechos, tags, tax):
    """Trechos agrupados por tema principal, para revisar e corrigir data/tags.json."""
    esc = html.escape
    por_tema = defaultdict(list)
    for t in trechos:
        tg = tags.get(t['id'])
        por_tema[tg['temas'][0] if tg else '(sem tema)'].append(t)
    nomes = {x['id']: x['nome'] for x in tax['temas']}
    linhas = ['<!doctype html><meta charset="utf-8"><title>Classificação Mioshie-shu</title>',
              '<style>body{font:14px system-ui;margin:2rem;max-width:1200px}td{border-bottom:1px solid #eee;padding:3px 8px;vertical-align:top}'
              'details{margin:6px 0}summary{font-weight:600;cursor:pointer}.k{color:#888}</style>',
              '<h1>Revisão da classificação</h1><p>Agrupado pelo tema principal (o primeiro). Para corrigir, edite '
              '<code>data/tags.json</code> e rode <code>python scripts/build_index.py</code>.</p>']
    for tid in [x['id'] for x in tax['temas']] + ['(sem tema)']:
        lista = por_tema.get(tid, [])
        if not lista:
            continue
        linhas.append(f'<details><summary>{esc(nomes.get(tid, tid))} ({len(lista)})</summary><table>')
        for t in lista:
            tg = tags.get(t['id'], {})
            outros = ', '.join(nomes[x] for x in tg.get('temas', [])[1:])
            linhas.append(f"<tr><td>{t['id']}</td><td>{t['data']}</td><td>{esc(t['titulo'])}</td>"
                          f"<td>{esc(outros)}</td><td class=k>{esc(', '.join(tg.get('palavras', [])))}</td></tr>")
        linhas.append('</table></details>')
    with open(os.path.join(ROOT, 'reports', 'classificacao.html'), 'w', encoding='utf8') as f:
        f.write('\n'.join(linhas))


if __name__ == '__main__':
    main()
