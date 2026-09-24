"""Artigos lidos nos dias de Mioshie-shu: Anexo PT + original JP -> data/articles.json.

PT: Heading2 = volume ("御教え集 01"), Heading3 = artigo. JP: Heading1 = volume, Heading2 = artigo.
Onde as listas coincidem, o pareamento é pela ordem; nos demais volumes vale PAREAMENTO.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from docx_util import paragraphs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Conteudo Original Traduzido')
OUT = os.path.join(ROOT, 'data', 'articles.json')

Z2H = str.maketrans('０１２３４５６７８９（）', '0123456789()')


def vol_de(texto):
    return int(re.search(r'(\d+)', texto.translate(Z2H)).group(1))


FONTE_PT = re.compile(r'^\(.*(?:19[45]\d|Eik|Kyusei|Chijo|Tengoku|Civiliza|nº).*\)$')
FONTE_JA = re.compile(r'^[（(].*(?:号|昭和).*[）)]$')


# Artigos sem tradução no Anexo, pareados com a tradução do Zenshu (id conferido pelo texto JP).
# cópia local dos arquivos de new_mioshie_zenshu/data/teachings que contêm esses ensinamentos
ZENSHU_DIR = os.path.join(SRC, 'Zenshu')
ZENSHU_PT = {
    '悪の追放': 'a_aku10', '御説教': 'o_osekkyo', '総篇 健康と寿命': 'ke_kenkou03', '本教と社会事業': 'ho_honkyo06',
    '医学関係者に警告する': 'i_igaku07', '宗教と妨害': 'shi_syukyo23', '総篇 悪の発生と病': 'a_aku11',
    '⦿(ｽ)の文化': 'su_sunobunk',
}
# Lidos nos dias de visita mas ausentes dos dois Anexos: entram direto do Zenshu (PT + JP).
EXTRAS_ZENSHU = [(13, 'ko_kogai', '梗概（文明の創造）', ['Esboço'])]
# Artigos só em PT no Anexo: original JP do Zenshu. (id, 1º e último bloco da seção ou None = texto todo, título JP)
JP_ZENSHU = {
    (3, 'Diário de Johrei'): ('jorei_jorei128', None, '浄霊日記'),
    (27, 'O Princípio da Agricultura Natural'): ('ni_nihon25', (6, 10), '自然農法の原理'),
    (30, 'O princípio da Agricultura Natural'): ('ni_nihon25', (6, 10), '自然農法の原理'),
}
PUBLICACAO_PT = {'栄光': 'Eikō', '地上天国': 'Chijō Tengoku', '文明の創造': 'Criação da Civilização'}
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
         'outubro', 'novembro', 'dezembro']


def carregar_zenshu():
    ids = set(ZENSHU_PT.values()) | {x[1] for x in EXTRAS_ZENSHU} | {x[0] for x in JP_ZENSHU.values()}
    achados = {}
    if not os.path.isdir(ZENSHU_DIR):
        print(f'aviso: {ZENSHU_DIR} não encontrada; vol 13 fica só em JP')
        return achados
    for nome in os.listdir(ZENSHU_DIR):
        dados = json.load(open(os.path.join(ZENSHU_DIR, nome), encoding='utf8'))
        if isinstance(dados, list):
            achados.update({e['id']: e for e in dados if isinstance(e, dict) and e.get('id') in ids})
    return achados


def blocos_jp(e):
    """Parágrafos do texto japonês; sem a versão formatada, o campo 'content' separa parágrafos por espaço."""
    if e.get('content_jp_formatted'):
        return [x.strip() for x in e['content_jp_formatted'].split('\n\n') if x.strip()]
    return [x.strip() for x in re.split(r'[ 　]+', e.get('content') or '') if x.strip()]


def traducao_zenshu(e):
    linhas = [x.strip() for x in e['content_ptbr'].split('\n\n') if x.strip() and x.strip() != '***']
    titulo = linhas.pop(0).lstrip('# ').strip() if linhas and linhas[0].startswith('#') else e['title']
    paras = [re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', x) for x in linhas]
    pub = PUBLICACAO_PT.get(e.get('source_jp'), e.get('source_jp') or '')
    num = re.sub(r'号$', '', e.get('issue_page') or '')
    data = e.get('date_iso') or ''
    if len(data) == 10:
        a, m, d = data.split('-')
        data = f"{int(d)}{'º' if d == '01' else ''} de {MESES[int(m) - 1]} de {a}"
    if e['id'] in {x[1] for x in EXTRAS_ZENSHU}:
        data = ''  # data do Zenshu é estimada e posterior à leitura
    fonte = f"({pub}{', nº ' + num if num else ', inédito'}{', ' + data if data else ''})"
    return {'titulo': titulo, 'paras': paras, 'fonte': fonte, 'traducao_zenshu': e['id']}


def ler(path, h_vol, h_art, fonte_re):
    vols, atual, vol = {}, None, None
    for estilo, texto in paragraphs(path):
        if estilo == h_vol and '御教え集' in texto:
            vol = vol_de(texto)
            vols.setdefault(vol, [])
            atual = None
        elif estilo == h_art and vol is not None:
            atual = {'titulo': texto, 'paras': [], 'fonte': None}
            vols[vol].append(atual)
        elif atual is not None and not estilo.startswith('Heading'):
            if fonte_re.match(texto) and len(texto) < 140 and atual['fonte'] is None:
                # a tradução às vezes escreveu o ano Showa como 19xx ("Showa 27" -> "1927" em vez de 1952)
                if 'Eik' in texto:  # só Eikō (1949–1955); datas reais dos anos 1930 ficam intactas
                    texto = re.sub(r'\b19([2-3]\d)\)', lambda m: f'{1925 + int(m.group(1))})', texto)
                atual['fonte'] = texto
            atual['paras'].append(texto)
    return vols


# Pareamento revisado manualmente nos volumes em que PT e JP não seguem 1:1.
# (pt, ja, [complementos PT]); pt=None -> só JP; ja=None -> só PT.
# Complementos = relatos de fiéis ou subpartes que no PT viraram títulos próprios.
# Índices PT ausentes da lista (cabeçalhos vazios) e JP ausentes (leituras repetidas) são descartados.
PAREAMENTO = {
    2: [(0, 0), (1, 1, [2]), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8)],
    3: [(0, 0), (1, 1), (2, 2), (3, None), (4, 3), (5, 4), (6, 5), (7, 6, [8]), (9, 7), (10, 8, [11]), (12, 9)],
    4: [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7, [8])],
    5: [(0, 0), (1, 1, [2, 3]), (4, 2), (5, 3), (7, 4), (8, 5), (10, 6), (11, 7), (12, 8), (13, 9)],
    9: [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7), (7, 8, [8]), (9, 9), (10, 10), (11, 11)],
    10: [(0, 0), (1, 1, [2]), (3, 2), (4, 3), (None, 4), (5, 5), (6, 6), (7, 7)],
    12: [(0, 0), (None, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 7), (6, 8), (7, 9), (8, 10), (9, 11)],
    14: [(0, 0), (1, 1), (2, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (10, 9)],
    21: [(0, 0, [1, 2, 3]), (4, 1), (5, 2), (6, 3), (7, 4), (8, 5), (9, 6), (10, 7)],
    23: [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6, [7])],
    27: [(0, 0), (1, 1), (2, 2), (3, 3), (4, None)],
    30: [(0, 0), (1, 1), (2, None), (3, 2), (4, 3), (5, 4, [6]), (7, 5), (8, 6)],
}
TITULO_PT = {(14, 4): 'Fragmentos de Medicina (21): Tudo o que tem Nome de "Remédio" é Narcótico'}
# Vol 13 não está no Anexo PT. Os textos vêm da tradução do Zenshu (ZENSHU_PT); o título
# provisório abaixo continua valendo como apelido para ligar as citações dos volumes.
TITULO_PROVISORIO = {
    '悪の追放': 'A Expulsão do Mal', '御説教': 'Sermão', '総篇 健康と寿命': '[Coleção] Saúde e Longevidade',
    '本教と社会事業': 'Nossa Religião e a Obra Social', '医学関係者に警告する': 'Advertência aos Profissionais da Medicina',
    '宗教と妨害': 'Religião e Obstrução', '総篇 悪の発生と病': '[Coleção] A Origem do Mal e a Doença',
    '⦿(ｽ)の文化': 'A Cultura de ⦿ (Su)',
}
# Outras traduções do mesmo título usadas nas citações dos volumes.
ALIASES = {
    'Em Vez de Falar': ['Em Lugar de Minhas Palavras', 'Em vez da língua'],
    'Meus Estudos em Arte': ['Meu Treinamento Artístico'],
    'A Origem dos Micróbios': ['A Geração de Germes', 'O Surgimento dos Germes'],
    'Noventa e Nove por Cento e Um por Cento': ['99% e 1%'],
    'A Superstição do Ateísmo': ['Ateísmo e Superstição'],
    'Uma Pessoa Gera Cem': ['Um é Cem'],
    'A Razão pela qual os Mestres [Meijin] desapareceram (1)': ['O Motivo do Desaparecimento dos Mestres (1)'],
    'Rei Shu Tai Jū (O Espírito é o Principal, o Corpo é o Subordinado)': ['Espírito precede Matéria'],
    '[Coleção] Saúde e Longevidade': ['Doença e Longevidade'],
    '[Coleção] A Origem do Mal e a Doença': ['Humanidade e Medicina'],  # lido em v13-018 (conferido pelo conteúdo)
    'Capítulo da Religião: Deus Izunome': ['Izunome-no-Kami'],
    "Capítulo da Religião: Miroku San'e (Os Três Encontros de Miroku)": ['As Três Assembleias de Miroku'],
    'União entre o divino e o humano': ['União Deus-Homem (Shinjin Gōitsu)'],
}


def pares_do_volume(vol, n_pt, n_ja):
    if vol in PAREAMENTO:
        return [(x[0], x[1], x[2] if len(x) > 2 else []) for x in PAREAMENTO[vol]]
    if n_pt and n_ja and n_pt != n_ja:
        raise SystemExit(f'vol {vol}: {n_pt} PT x {n_ja} JP sem pareamento manual')
    return [(i if n_pt else None, i if n_ja else None, []) for i in range(max(n_pt, n_ja))]


def main():
    pt = ler(os.path.join(SRC, 'Anexo Ensinamentos Lidos em Mioshie-shu 1-33.docx'), 'Heading2', 'Heading3', FONTE_PT)
    ja = ler(os.path.join(SRC, 'Ensinamentos Lidos em  Mioshie-shu.docx'), 'Heading1', 'Heading2', FONTE_JA)
    zenshu = carregar_zenshu()
    artigos = []
    for vol in sorted(set(pt) | set(ja)):
        lpt, lja = pt.get(vol, []), ja.get(vol, [])
        for n, (i, j, comp) in enumerate(pares_do_volume(vol, len(lpt), len(lja)), 1):
            a = lpt[i] if i is not None else None
            b = lja[j] if j is not None else None
            artigos.append({
                'id': f'a{vol:02d}-{n:02d}', 'vol': vol,
                'titulo': TITULO_PT.get((vol, i), a['titulo']) if a else None,
                'fonte': a['fonte'] if a else None, 'paras': a['paras'] if a else [],
                'titulo_ja': b['titulo'] if b else None, 'fonte_ja': b['fonte'] if b else None,
                'paras_ja': b['paras'] if b else [],
                'complementos': [{'titulo': lpt[k]['titulo'], 'paras': lpt[k]['paras']} for k in comp if lpt[k]['paras']],
            })
    for vol, zid, titulo_ja, aliases in EXTRAS_ZENSHU:
        z = zenshu.get(zid)
        if not z:
            continue
        blocos = [x.strip() for x in z['content_jp_formatted'].split('\n\n') if x.strip()]
        inicio = next((i + 1 for i, b in enumerate(blocos) if '『' in b and len(b) < 80), 1)
        n = sum(1 for a in artigos if a['vol'] == vol) + 1
        artigos.append(dict(traducao_zenshu(z), id=f'a{vol:02d}-{n:02d}', vol=vol, titulo_ja=titulo_ja,
                            fonte_ja=blocos[inicio - 1] if inicio > 1 else None, paras_ja=blocos[inicio:],
                            complementos=[], aliases_extra=aliases))
    artigos.sort(key=lambda a: (a['vol'], a['id']))
    for a in artigos:
        alvo = JP_ZENSHU.get((a['vol'], a['titulo']))
        z = zenshu.get(alvo[0]) if alvo and not a['titulo_ja'] else None
        if not z:
            continue
        blocos = blocos_jp(z)
        fonte = next((b for b in blocos if '『' in b and len(b) < 80), None)
        if alvo[1]:
            corpo = blocos[alvo[1][0]:alvo[1][1] + 1]
        else:
            corpo = blocos[blocos.index(fonte) + 1:] if fonte else blocos[1:]
        corpo = [b for b in corpo if not ('『' in b and '発行' in b and len(b) < 80)]  # outras linhas de publicação
        a.update(titulo_ja=alvo[2], fonte_ja=fonte, paras_ja=corpo, original_zenshu=z['id'])
        # o Anexo omitiu o texto ("(Texto omitido)"): usa também a tradução do Zenshu
        if all(p.startswith('(') for p in a['paras']):
            a.update({k: v for k, v in traducao_zenshu(z).items() if k != 'fonte'}, titulo=a['titulo'])
    # leituras repetidas: artigo só-JP reaproveita a tradução do mesmo texto lido em outro dia
    por_ja = {a['titulo_ja']: a for a in artigos if a['titulo'] and a['titulo_ja']}
    for a in artigos:
        irmao = por_ja.get(a['titulo_ja']) if not a['titulo'] else None
        if irmao:
            a.update(titulo=irmao['titulo'], fonte=irmao['fonte'], paras=irmao['paras'], traducao_de=irmao['id'])
    for a in artigos:
        provisorio = TITULO_PROVISORIO.get(a['titulo_ja']) if not a['titulo'] else None
        a['aliases'] = ALIASES.get(a['titulo'] or provisorio, []) + a.pop('aliases_extra', [])
        z = zenshu.get(ZENSHU_PT.get(a['titulo_ja'])) if not a['titulo'] else None
        if z:
            a.update(traducao_zenshu(z))
            a['aliases'] = a['aliases'] + [provisorio]
        elif provisorio:
            a['titulo'] = provisorio
            a['titulo_provisorio'] = True
    with open(OUT, 'w', encoding='utf8') as f:
        json.dump(artigos, f, ensure_ascii=False, indent=1)
    so_pt = [a for a in artigos if not a['titulo_ja']]
    so_ja = [a for a in artigos if not a['titulo']]
    print(f'artigos: {len(artigos)}  pareados: {len(artigos) - len(so_pt) - len(so_ja)}  '
          f'só PT: {len(so_pt)}  só JP: {len(so_ja)}  complementos: {sum(len(a["complementos"]) for a in artigos)}')
    for a in so_pt + so_ja:
        print(' ', a['id'], a['titulo'] or '', '|', a['titulo_ja'] or '')


if __name__ == '__main__':
    main()
