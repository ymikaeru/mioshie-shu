// Utilidades compartilhadas por todas as páginas.
const MS = (() => {
  const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const cache = {};

  function json(url) {
    if (!cache[url]) cache[url] = fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.json(); });
    return cache[url];
  }

  let _idx;
  async function index() {
    if (_idx) return _idx;
    const d = await json('data/index.json');
    d.porId = Object.fromEntries(d.trechos.map(t => [t.id, t]));
    d.tema = Object.fromEntries(d.temas.map(t => [t.id, t]));
    d.formato = Object.fromEntries(d.formatos.map(f => [f.id, f]));
    d.artigo = Object.fromEntries(d.artigos.map(a => [a.id, a]));
    _idx = d;
    return d;
  }

  const vol = v => json(`data/vols/vol${String(v).padStart(2, '0')}.json`);
  const artigo = id => json(`data/artigos/${id}.json`);

  // texto completo de todos os trechos, sem acento, para a busca
  let _textos;
  async function textos() {
    if (_textos) return _textos;
    const idx = await index();
    const vs = [...new Set(idx.trechos.map(t => t.v))];
    const all = await Promise.all(vs.map(vol));
    _textos = {};
    for (const v of all) for (const t of v.trechos) {
      _textos[t.id] = t.paras.map(p => p.x).join('\n');
    }
    return _textos;
  }

  const dobra = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  // "purificação toxina" -> todos os termos; "\"mundo do dia\"" -> frase exata
  function termos(q) {
    const out = [];
    const re = /"([^"]+)"|(\S+)/g;
    let m;
    while ((m = re.exec(q))) out.push(dobra(m[1] || m[2]));
    return out.filter(Boolean);
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // destaca termos (comparação sem acento) preservando o texto original
  function destacar(texto, ts) {
    if (!ts || !ts.length) return esc(texto);
    const d = dobra(texto);
    const marcas = [];
    for (const t of ts) {
      let i = d.indexOf(t);
      while (i >= 0) { marcas.push([i, i + t.length]); i = d.indexOf(t, i + t.length); }
    }
    if (!marcas.length) return esc(texto);
    marcas.sort((a, b) => a[0] - b[0]);
    let out = '', pos = 0;
    for (const [a, b] of marcas) {
      if (a < pos) continue;
      out += esc(texto.slice(pos, a)) + '<mark>' + esc(texto.slice(a, b)) + '</mark>';
      pos = b;
    }
    return out + esc(texto.slice(pos));
  }

  // trecho curto do texto em volta do primeiro termo encontrado
  function contexto(texto, ts, tam = 260) {
    const d = dobra(texto);
    let i = -1;
    for (const t of ts || []) { i = d.indexOf(t); if (i >= 0) break; }
    if (i < 0) return destacar(texto.slice(0, tam).replace(/\n/g, ' ') + (texto.length > tam ? '…' : ''), ts);
    const ini = Math.max(0, i - tam / 3);
    const s = (ini > 0 ? '…' : '') + texto.slice(ini, ini + tam).replace(/\n/g, ' ') + (ini + tam < texto.length ? '…' : '');
    return destacar(s, ts);
  }

  function dataExtenso(iso) {
    if (!iso) return 'sem data';
    const [a, m, d] = iso.split('-').map(Number);
    return `${d === 1 ? '1º' : d} de ${MESES[m - 1]} de ${a}`;
  }
  const mesExtenso = ym => { const [a, m] = ym.split('-').map(Number); return `${MESES[m - 1]} de ${a}`; };
  const mesCurto = ym => { const [a, m] = ym.split('-').map(Number); return `${MESES_CURTOS[m - 1]} ${String(a).slice(2)}`; };

  const link = t => `leitura.html?v=${t.v}#${t.id}`;
  const grupoCls = (idx, temaId) => 'g-' + (idx.tema[temaId]?.grupo || '');

  function chipsTemas(idx, t) {
    return t.tm.map(id => `<a class="chip ${grupoCls(idx, id)}" href="explorar.html?tema=${id}">${esc(idx.tema[id]?.nome || id)}</a>`).join('');
  }
  function chipsFormato(idx, t) {
    return t.f.map(f => `<a class="chip fmt" href="explorar.html?fmt=${f}">${esc(idx.formato[f]?.nome || f)}</a>`).join('');
  }

  // meses cobertos pelo acervo, em ordem
  function meses(idx) {
    return [...new Set(idx.trechos.map(t => t.d.slice(0, 7)))].sort();
  }

  function cabecalho(ativo) {
    const itens = [
      ['index.html', 'Início'], ['leitura.html', 'Em sequência'], ['explorar.html', 'Explorar'],
      ['macro.html', 'Visão macro'], ['calendario.html', 'Calendário'], ['artigos.html', 'Artigos lidos'], ['glossario.html', 'Glossário'],
    ];
    const el = document.createElement('header');
    el.className = 'topo';
    el.innerHTML = `<div class="topo-in">
      <a class="marca" href="index.html"><b>Mioshie-shu</b> · estudo</a>
      <button class="menu-btn" aria-label="Menu">☰</button>
      <nav class="nav">${itens.map(([h, n]) => `<a href="${h}" class="${h === ativo ? 'ativo' : ''}">${n}</a>`).join('')}</nav>
      <button class="tema-btn" title="Alternar claro/escuro" aria-label="Alternar claro/escuro">◐</button>
      <button class="tema-btn sair-btn" title="Sair" aria-label="Sair">Sair</button>
    </div>`;
    document.body.prepend(el);
    el.querySelector('.sair-btn').onclick = () => {
      try { sessionStorage.removeItem('mioshie_shu_auth'); } catch (e) { /* sem storage */ }
      location.replace('login.html');
    };
    el.querySelector('.menu-btn').onclick = () => el.querySelector('.nav').classList.toggle('aberto');
    el.querySelector('.tema-btn:not(.sair-btn)').onclick = () => {
      const escuro = document.documentElement.dataset.theme === 'dark' ||
        (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.dataset.theme = escuro ? 'light' : 'dark';
      try { localStorage.setItem('ms-tema', document.documentElement.dataset.theme); } catch (e) { /* sem storage */ }
    };
  }

  try { const t = localStorage.getItem('ms-tema'); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* sem storage */ }

  // ---------- gaveta do artigo lido (usada na leitura e no explorar) ----------
  let gaveta, fundo;
  async function abrirArtigo(id) {
    const idx = await index();
    if (!gaveta) {
      fundo = document.createElement('div');
      fundo.className = 'fundo';
      fundo.hidden = true;
      gaveta = document.createElement('aside');
      gaveta.className = 'gaveta';
      gaveta.setAttribute('aria-label', 'Artigo lido');
      document.body.append(fundo, gaveta);
      fundo.onclick = fecharArtigo;
      document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharArtigo(); });
    }
    gaveta.innerHTML = '<div class="carregando">Carregando artigo…</div>';
    fundo.hidden = false;
    requestAnimationFrame(() => gaveta.classList.add('aberta'));
    const a = await artigo(id);
    gaveta.innerHTML = `<header>
        <h3>${esc(a.titulo || a.titulo_ja)}</h3>
        <a class="small" href="artigo.html?id=${a.id}">página do artigo ↗</a>
        <button class="fechar" aria-label="Fechar">×</button>
      </header>
      <div class="corpo">${htmlArtigo(a, idx)}</div>`;
    gaveta.querySelector('.fechar').onclick = fecharArtigo;
    ligarIdioma(gaveta, a);
  }
  function fecharArtigo() {
    if (!gaveta) return;
    gaveta.classList.remove('aberta');
    fundo.hidden = true;
  }

  function htmlArtigo(a, idx) {
    const temPt = a.paras && a.paras.length, temJa = a.paras_ja && a.paras_ja.length;
    const lidos = idx.artigo[a.id]?.lidos || [];
    const aviso = a.titulo_provisorio ? '<p class="aviso">Este artigo não consta no Anexo em português; título traduzido provisoriamente. Texto disponível só no original.</p>' : '';
    const origem = a.traducao_zenshu
      ? `<p class="small muted">Este artigo não consta no Anexo em português; tradução trazida do Mioshie Zenshu (${esc(a.traducao_zenshu)}).</p>`
      : a.traducao_de ? `<p class="small muted">Tradução do mesmo texto lido em outro volume (${esc(a.traducao_de)}).</p>` : '';
    return `<div class="small muted" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
        <span>Vol. ${a.vol}</span>${a.fonte ? `<span>${esc(a.fonte)}</span>` : ''}
        ${temPt && temJa ? `<span class="lang"><button data-l="pt" class="on">Português</button><button data-l="ja">日本語</button></span>` : ''}
      </div>
      ${aviso}${origem}
      <div class="artigo-txt" data-pt>${(a.paras || []).map(p => `<p>${esc(p)}</p>`).join('')}
        ${(a.complementos || []).map(c => `<div class="complemento"><h4>${esc(c.titulo)}</h4>${c.paras.map(p => `<p>${esc(p)}</p>`).join('')}</div>`).join('')}
      </div>
      <div class="artigo-txt jp" data-ja ${temPt ? 'hidden' : ''}>${a.titulo_ja ? `<h3>${esc(a.titulo_ja)}</h3>` : ''}${(a.paras_ja || []).map(p => `<p>${esc(p)}</p>`).join('')}</div>
      ${lidos.length ? `<h3 style="margin-top:1.6em">Lido e comentado em</h3><ul class="lidos">${lidos.map(i => {
        const t = idx.porId[i];
        return `<li><a href="${link(t)}">${dataExtenso(t.d)}</a> <span class="muted">· vol. ${t.v} · ${esc(t.t)}</span></li>`;
      }).join('')}</ul>` : ''}`;
  }

  function ligarIdioma(raiz) {
    raiz.querySelectorAll('.lang button').forEach(b => b.onclick = () => {
      raiz.querySelectorAll('.lang button').forEach(x => x.classList.toggle('on', x === b));
      raiz.querySelector('[data-pt]').hidden = b.dataset.l !== 'pt';
      raiz.querySelector('[data-ja]').hidden = b.dataset.l !== 'ja';
    });
  }

  return {
    json, index, vol, artigo, textos, dobra, termos, esc, destacar, contexto, dataExtenso, mesExtenso, mesCurto,
    link, grupoCls, chipsTemas, chipsFormato, meses, cabecalho, abrirArtigo, htmlArtigo, ligarIdioma, MESES,
  };
})();
