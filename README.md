# Mioshie-shu · site de estudo

Os 33 volumes do Mioshie-shu (1951–1954) organizados para quatro formas de leitura:
**em sequência** (como no Zenshu), **por assunto**, **por tipo** (pergunta e resposta /
leitura e comentário / assunto do momento) e **por palavra**, com visão macro, calendário,
artigos lidos (PT + JP) e glossário.

## Abrir
Dê dois cliques em `INICIAR.bat` (precisa de Python), ou rode `python -m http.server 8765`
nesta pasta e abra http://localhost:8765. Abrir o `index.html` direto do disco não funciona,
porque o navegador bloqueia o carregamento dos dados. Para publicar, basta enviar a pasta
para o GitHub Pages (todos os arquivos são estáticos).

## Acesso
Todas as páginas pedem a senha em `login.html` (a mesma do Mioshie Zenshu). O código guarda só o hash
SHA-256 da senha (`HASH` em `login.html` e na linha de trava no início de cada página). Para trocar a senha,
gere o novo hash (`python -c "import hashlib;print(hashlib.sha256('NOVA'.encode()).hexdigest())"`) e substitua
o valor antigo em todos os `.html`. A trava é só no navegador, como no Zenshu: impede a navegação casual,
mas quem souber o endereço dos arquivos em `data/` ainda consegue baixá-los.

## Regerar os dados (após mudar os .docx)
```
python scripts/parse_volumes.py     # docx -> data/vols/volNN.json (sequência, datas, formatos)
python scripts/parse_anexo.py       # Anexo PT + original JP -> data/articles.json
python scripts/build_index.py       # data/index.json, data/artigos/, reports/
```
- **Temas**: `data/tags.json` (classificação por IA, revisável). A taxonomia fica em `data/taxonomy.json`.
  Revise pelo `reports/classificacao.html`; depois de editar, rode `build_index.py`.
- **Glossário**: `data/glossario.json` (termo, variantes, definição).
- **Pareamento PT/JP dos artigos** e títulos alternativos: constantes `PAREAMENTO` e `ALIASES` em `scripts/parse_anexo.py`.
- **Vol 13 e o 梗概 ("Esboço")** não constam no Anexo PT. Os textos vêm de `Conteudo Original Traduzido/Zenshu/`,
  que tem cópias de 5 arquivos de `new_mioshie_zenshu/data/teachings` (constantes `ZENSHU_PT` e `EXTRAS_ZENSHU`).
  Se a tradução for revisada no Zenshu, copie os arquivos de novo e rode `parse_anexo.py` e `build_index.py`.
- **Validação**: `reports/validacao.html` lista datas a conferir, citações sem artigo e artigos sem comentário ligado.

Trechos novos só recebem tema depois de uma nova classificação (`scripts/classify_batches.py preparar`,
classificar os lotes, depois `aplicar`).
