"""Reconhecimento das linhas de data dos volumes (cabeçalho do dia e rodapé do trecho)."""
import re
import unicodedata

MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
MES_RE = '(' + '|'.join(MESES) + ')'

UNID = {'um': 1, 'primeiro': 1, 'dois': 2, 'três': 3, 'tres': 3, 'quatro': 4, 'cinco': 5,
        'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9}
BASE = {'dez': 10, 'onze': 11, 'doze': 12, 'treze': 13, 'catorze': 14, 'quatorze': 14,
        'quinze': 15, 'dezesseis': 16, 'dezessete': 17, 'dezoito': 18, 'dezenove': 19,
        'vinte': 20, 'trinta': 30}
BASE.update(UNID)
DIA_PALAVRA = r'(?:vinte|trinta)(?: e (?:um|dois|três|tres|quatro|cinco|seis|sete|oito|nove))?|' + \
    '|'.join(sorted((k for k in BASE if k not in ('vinte', 'trinta')), key=len, reverse=True))
DIA = r'(\d{1,2})\s*º?|(' + DIA_PALAVRA + ')'

# "5 de agosto", "Cinco de agosto", "26 e 27 de julho", "1º de agosto"
DIA_MES = re.compile(r'^(?:' + DIA + r')(?: e (?:\d{1,2}|' + DIA_PALAVRA + r'))?\s*de ' + MES_RE, re.I)
ANO_RE = re.compile(r'Showa\s*(\d{1,2})|\b(19[45]\d)\b', re.I)
PUBLICACAO = re.compile(r'Kyo|Kyō|Kyô|Publicad|Colet[aâ]nea|Ensinamentos? (?:Vol|nº)|Cole[cç][aã]o|Refer[eê]ncia|Eik[oō]', re.I)


def _dia(m):
    if m.group(1):
        return int(m.group(1))
    palavra = m.group(2).lower()
    if ' e ' in palavra:
        a, b = palavra.split(' e ')
        return BASE[a] + UNID[b]
    return BASE[palavra]


def _ano(texto):
    m = ANO_RE.search(texto)
    if not m:
        return None
    if m.group(2):
        return int(m.group(2))
    return 1925 + int(m.group(1))


def parse_linha_data(texto):
    """Devolve dict {tipo: 'rodape'|'cabecalho', dia, mes, ano|None, local} ou None.

    rodapé  = linha inteira entre parênteses: "(1º de agosto de 1951)"
    cabeçalho = linha curta sem parênteses: "1º de agosto", "20 de outubro (No Teatro de Kyoto)"
    Linhas de publicação ("(Kyo nº 2, 25 de outubro de 1951)") são ignoradas.
    """
    t = texto.strip()
    if len(t) > 90 or PUBLICACAO.search(t):
        return None
    rodape = t.startswith('(') and t.endswith(')')
    corpo = t[1:-1].strip() if rodape else t
    m = DIA_MES.match(corpo)
    if not m:
        return None
    resto = corpo[m.end():].strip()
    local = None
    # o que sobra só pode ser ano / Showa / local entre parênteses / "(continuação)"
    loc = re.search(r'\(([^)]*)\)\s*$', resto)
    if loc and not ANO_RE.fullmatch(loc.group(1).strip()) and not re.fullmatch(r'Showa \d+', loc.group(1).strip()):
        local = loc.group(1).strip()
        resto = resto[:loc.start()].strip()
    sobra = ANO_RE.sub('', resto)
    sobra = re.sub(r'[\s,\-—\[\]()de.]+', '', sobra)
    if sobra and sobra.lower() != 'continuação':
        return None
    mes = MESES.index(m.group(3).lower()) + 1
    return {'tipo': 'rodape' if rodape else 'cabecalho', 'dia': _dia(m), 'mes': mes,
            'ano': _ano(resto), 'local': local if local and local.lower() != 'continuação' else None}


CAB_MES = re.compile(r'^Ensinamentos de ' + MES_RE + r' de (?:Showa \d+ \((\d{4})\)|(\d{4}))', re.I)
# docstring abaixo: devolve (ano, mes, resto_da_linha)


def parse_cabecalho_mes(texto):
    """'Ensinamentos de agosto de 1951' -> (1951, 8)."""
    m = CAB_MES.match(texto.strip())
    if not m:
        return None
    resto = re.sub(r'^\s*\((?:Showa \d+|\d{4})\)', '', texto.strip()[m.end():]).strip()
    return int(m.group(2) or m.group(3)), MESES.index(m.group(1).lower()) + 1, resto


def iso(ano, mes, dia):
    return f'{ano:04d}-{mes:02d}-{dia:02d}'


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
