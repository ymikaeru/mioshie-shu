"""Classificação temática dos trechos.

  python scripts/classify_batches.py preparar   -> data/_classif/lote_NN.jsonl
  python scripts/classify_batches.py aplicar    -> junta lote_NN.out.json em data/tags.json (valida)

Formato de saída de cada lote: {"v01-001": {"temas": ["medicina", ...], "palavras": ["...", ...]}, ...}
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'data', '_classif')
TAM_LOTE = 120


def trechos():
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'vols', 'vol*.json'))):
        yield from json.load(open(f, encoding='utf8'))['trechos']


def resumo(t, limite=1400):
    texto = '\n'.join(p['x'] for p in t['paras'])
    if len(texto) > limite:
        texto = texto[:limite - 300] + ' […] ' + texto[-300:]
    return texto


def preparar():
    os.makedirs(DIR, exist_ok=True)
    ts = list(trechos())
    for n, i in enumerate(range(0, len(ts), TAM_LOTE), 1):
        with open(os.path.join(DIR, f'lote_{n:02d}.jsonl'), 'w', encoding='utf8') as f:
            for t in ts[i:i + TAM_LOTE]:
                f.write(json.dumps({'id': t['id'], 'titulo': t['titulo'], 'formato': t['formatos'],
                                    'texto': resumo(t)}, ensure_ascii=False) + '\n')
    print(f'{len(ts)} trechos em {n} lotes')


def aplicar():
    tax = json.load(open(os.path.join(ROOT, 'data', 'taxonomy.json'), encoding='utf8'))
    validos = {t['id'] for t in tax['temas']}
    ids = [t['id'] for t in trechos()]
    tags, erros = {}, []
    for f in sorted(glob.glob(os.path.join(DIR, 'lote_*.out.json'))):
        for k, v in json.load(open(f, encoding='utf8')).items():
            temas = [x for x in v.get('temas', []) if x in validos]
            if len(temas) != len(v.get('temas', [])):
                erros.append(f'{k}: tema inválido {v.get("temas")}')
            tags[k] = {'temas': temas[:3], 'palavras': [p.strip() for p in v.get('palavras', []) if p.strip()][:6]}
    faltando = [i for i in ids if i not in tags or not tags[i]['temas']]
    with open(os.path.join(ROOT, 'data', 'tags.json'), 'w', encoding='utf8') as f:
        json.dump({i: tags[i] for i in ids if i in tags}, f, ensure_ascii=False, indent=0)
    print(f'classificados: {len(tags)}/{len(ids)}  sem tema: {len(faltando)}  temas inválidos: {len(erros)}')
    for e in erros[:20]:
        print(' ', e)
    if faltando:
        print('  faltando:', ' '.join(faltando[:40]))


if __name__ == '__main__':
    {'preparar': preparar, 'aplicar': aplicar}[sys.argv[1]]()
