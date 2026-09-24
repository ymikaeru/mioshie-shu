"""Extrai os 33 volumes para data/vols/volNN.json preservando a sequência original.

Cada volume = lista de trechos (Heading2) na ordem do documento. O título do trecho é
editorial (criado na tradução); o dado original é a data do registro.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from docx_util import paragraphs  # noqa: E402
from dates import parse_linha_data, parse_cabecalho_mes, iso  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Conteudo Original Traduzido')
OUT = os.path.join(ROOT, 'data', 'vols')

SEPARADOR = re.compile(r'^[─━…‥\-—_=.\s]{5,}$')
MARCAS = {
    '(pergunta)': 'q', 'pergunta:': 'q', '(orientação)': 'a', 'orientação:': 'a', '(resposta)': 'a',
    '(ensinamento)': 'label', '(leitura de ensinamento:)': 'label', '(leitura de ensinamento)': 'label',
}
# parágrafo que é só a indicação da leitura (a fala que cita "⇒ X" continua como texto)
REF = re.compile(r'^(?:Ensaio|Leitura de Ensinamento|Dissertação|Leitura|Poema|Poemas|Artigo)\s*[:：]|^〔|^「'
                 r'|^Leitura d[oe]s? (?:artigo|ensinamento|ensaio)|^\[Refer'
                 r'|^\([^()]*?(?:artigo|dissertaç|goronbun|leitura|ensaio|ensinamento após|manuscrito)[^()]*?["“]', re.I)
TITULO_REF = re.compile(r'[「〔\[]\s*⇒?\s*["“]?([^」〕\]"”]+?)["”]?\s*[」〕\]]')


def vol_num(path):
    return int(re.search(r'Vol\.(\d+)', path).group(1))


def parse_volume(path, ano_padrao=None):
    v = vol_num(path)
    trechos = []
    atual = None
    ano_ctx, mes_ctx = ano_padrao, None
    dia_pendente = None  # cabeçalho de dia visto, aplica-se aos próximos trechos

    def fecha():
        if atual is not None:
            trechos.append(atual)

    for estilo, texto in paragraphs(path):
        if estilo == 'Heading1' or texto.startswith('御教え集'):
            continue
        if estilo.startswith('Heading') and not parse_linha_data(texto):
            fecha()
            atual = {'id': f'v{v:02d}-{len(trechos) + 1:03d}', 'vol': v, 'n': len(trechos) + 1,
                     'titulo': texto, 'data': None, 'data_fonte': None, 'local': None,
                     'dia_rotulo': None, 'paras': [], 'refs': []}
            atual['_desde_rodape'] = True
            if dia_pendente:
                atual['dia_rotulo'] = dia_pendente['rotulo']
                atual['local'] = dia_pendente['local']
                atual['_cab'] = dia_pendente
            continue

        cm = parse_cabecalho_mes(texto)
        if cm:
            ano_ctx, mes_ctx = cm[0], cm[1]
            if not cm[2]:
                continue
            texto = cm[2]  # "Ensinamentos de março de 1954 (Showa 29) 5 de março de 1954"
        d = parse_linha_data(texto)
        if d:
            if d['ano']:
                ano_ctx = d['ano']
            if d['tipo'] == 'cabecalho':
                dia_pendente = dict(d, rotulo=texto, ano=d['ano'] or ano_ctx)
                # novo dia: rodapés seguintes não retroagem para trechos de dias anteriores
                for t in trechos:
                    t.pop('_desde_rodape', None)
                # cabeçalho no meio de um trecho sem conteúdo ainda: vale para ele
                if atual is not None and not atual['paras']:
                    atual['dia_rotulo'] = texto
                    atual['local'] = d['local']
                    atual['_cab'] = dia_pendente
            elif atual is not None:
                ano = d['ano'] or ano_ctx
                if ano:
                    # o rodapé vale para o trecho atual e para os anteriores ainda sem rodapé
                    trechos_abertos = [t for t in trechos if t['data_fonte'] != 'rodape' and t.get('_desde_rodape')]
                    for t in trechos_abertos + [atual]:
                        if len(trechos_abertos) >= 6:
                            t['_incerta'] = f'um único rodapé datou {len(trechos_abertos) + 1} trechos seguidos'
                        if t['data_fonte'] != 'rodape':
                            t['data'] = iso(ano, d['mes'], d['dia'])
                            t['data_fonte'] = 'rodape'
                        t.pop('_desde_rodape', None)
                dia_pendente = None  # o cabeçalho já foi consumido por este dia
            continue
        if atual is None:
            continue  # texto antes do primeiro trecho
        if SEPARADOR.match(texto):
            continue
        tipo = MARCAS.get(texto.lower().strip())
        if tipo:
            atual['paras'].append({'t': tipo, 'x': texto})
            continue
        if REF.search(texto) and len(texto) < 300 or texto.startswith('⇒'):
            atual['paras'].append({'t': 'ref', 'x': texto})
            for m in TITULO_REF.finditer(texto):
                atual['refs'].append({'titulo': m.group(1).strip(' ⇒'), 'texto': texto})
            continue
        atual['paras'].append({'t': 'p', 'x': texto})
    fecha()

    # datas faltantes: cabeçalho do dia, senão herda do trecho anterior
    ultimo = None
    for t in trechos:
        cab = t.pop('_cab', None)
        t.pop('_desde_rodape', None)
        if t['data'] is None and cab and cab.get('ano'):
            t['data'] = iso(cab['ano'], cab['mes'], cab['dia'])
            t['data_fonte'] = 'cabecalho'
        if t['data'] is None and ultimo:
            t['data'] = ultimo
            t['data_fonte'] = 'herdada'
        ultimo = t['data'] or ultimo
    for t in trechos:
        t['formatos'] = formatos(t)
        t['conflito'] = t.pop('_incerta', None)
        if t['dia_rotulo'] and t['data_fonte'] == 'rodape':
            d = parse_linha_data(t['dia_rotulo'])
            if d and (d['dia'], d['mes']) != (int(t['data'][8:]), int(t['data'][5:7])):
                t['conflito'] = f"cabeçalho '{t['dia_rotulo']}' ≠ rodapé {t['data']}"
    return {'vol': v, 'arquivo': os.path.basename(path), 'trechos': trechos}


def formatos(t):
    tipos = {p['t'] for p in t['paras']}
    f = []
    if 'q' in tipos:
        f.append('pr')
    if 'ref' in tipos or any(p['x'].lower().startswith('(leitura') for p in t['paras']):
        f.append('leitura')
    if not f:
        f.append('assunto')
    return f


def main():
    os.makedirs(OUT, exist_ok=True)
    resumo = []
    ano_padrao = None
    for path in sorted(glob.glob(os.path.join(SRC, 'Mioshie-shu Vol*.docx')), key=vol_num):
        vol = parse_volume(path, ano_padrao)
        datas = [t['data'] for t in vol['trechos'] if t['data']]
        if datas:
            ano_padrao = int(datas[-1][:4])
        with open(os.path.join(OUT, f"vol{vol['vol']:02d}.json"), 'w', encoding='utf8') as f:
            json.dump(vol, f, ensure_ascii=False, indent=1)
        ts = vol['trechos']
        resumo.append((vol['vol'], len(ts), sum(1 for t in ts if not t['data']),
                       sum(1 for t in ts if t['data_fonte'] == 'herdada')))
    total = sum(r[1] for r in resumo)
    print('vol  trechos  sem_data  herdada')
    for r in resumo:
        print(f'{r[0]:3d} {r[1]:8d} {r[2]:9d} {r[3]:8d}')
    print('total', total)


if __name__ == '__main__':
    main()
