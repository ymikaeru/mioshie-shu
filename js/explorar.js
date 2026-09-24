// Explorar: busca em todo o texto + filtros combinados (tema, tipo, ano, mês, volume, termo do glossário).
MS.cabecalho('explorar.html');

(async () => {
  const idx = await MS.index();
  const meses = MS.meses(idx);
  const anos = [...new Set(meses.map(m => m.slice(0, 4)))];
  const vols = [...new Set(idx.trechos.map(t => t.v))];
  const glossario = Object.fromEntries(idx.glossario.map(g => [g.termo, new Set(g.ids)]));

  // ---------- estado (espelhado na URL) ----------
  const p = new URLSearchParams(location.search);
  const estado = {
    q: p.get('q') || '',
    temas: (p.get('tema') || '').split(',').filter(x => idx.tema[x]),
    fmt: (p.get('fmt') || '').split(',').filter(x => idx.formato[x]),
    ano: p.get('ano') || '', mes: p.get('mes') || '', vol: p.get('vol') || '',
    g: glossario[p.get('g')] ? p.get('g') : '',
    ids: p.get('ids') ? new Set(p.get('ids').split(',')) : null,
    idsRotulo: p.get('rotulo') || '',
    ordem: p.get('ordem') || 'crono', modo: p.get('modo') || 'lista',
  };
  const $ = id => document.getElementById(id);
  $('q').value = estado.q;
  $('ordem').value = estado.ordem;

  function paraUrl() {
    const u = new URLSearchParams();
    if (estado.q) u.set('q', estado.q);
    if (estado.temas.length) u.set('tema', estado.temas.join(','));
    if (estado.fmt.length) u.set('fmt', estado.fmt.join(','));
    for (const k of ['ano', 'mes', 'vol', 'g']) if (estado[k]) u.set(k, estado[k]);
    if (estado.ids) { u.set('ids', [...estado.ids].join(',')); if (estado.idsRotulo) u.set('rotulo', estado.idsRotulo); }
    if (estado.ordem !== 'crono') u.set('ordem', estado.ordem);
    if (estado.modo !== 'lista') u.set('modo', estado.modo);
    history.replaceState(null, '', 'explorar.html' + (u.toString() ? '?' + u : ''));
  }

  // ---------- filtragem ----------
  let textos = null, dobrados = null, cabecas = null;
  async function filtrar() {
    const ts = MS.termos(estado.q);
    if (ts.length && !textos) {
      $('conta').textContent = 'Buscando no texto completo…';
      textos = await MS.textos();
      dobrados = {};
      cabecas = {};
      for (const t of idx.trechos) {
        dobrados[t.id] = MS.dobra(textos[t.id]);
        cabecas[t.id] = MS.dobra(t.t + ' ' + t.kw.join(' '));
      }
    }
    // pontuação da busca, calculada uma vez para todos os trechos
    let notas = null;
    if (ts.length) {
      notas = new Map();
      for (const t of idx.trechos) {
        let s = 0;
        for (const x of ts) {
          const noCab = cabecas[t.id].includes(x), noCorpo = dobrados[t.id].includes(x);
          if (!noCab && !noCorpo) { s = 0; break; }
          s += (noCab ? 5 : 0) + Math.min(dobrados[t.id].split(x).length - 1, 10);
        }
        if (s > 0) notas.set(t.id, s);
      }
    }
    const passa = (t, ignorar) => {
      if (notas && !notas.has(t.id)) return false;
      if (ignorar !== 'tema' && estado.temas.some(x => !t.tm.includes(x))) return false;
      if (ignorar !== 'fmt' && estado.fmt.length && !estado.fmt.some(x => t.f.includes(x))) return false;
      if (ignorar !== 'ano' && estado.ano && !t.d.startsWith(estado.ano)) return false;
      if (estado.mes && !t.d.startsWith(estado.mes)) return false;
      if (ignorar !== 'vol' && estado.vol && String(t.v) !== estado.vol) return false;
      if (estado.g && !glossario[estado.g].has(t.id)) return false;
      if (estado.ids && !estado.ids.has(t.id)) return false;
      return true;
    };
    const res = idx.trechos.filter(t => passa(t));
    if (estado.ordem === 'rel' && notas) res.sort((a, b) => notas.get(b.id) - notas.get(a.id));
    // contagens para as facetas: cada faceta ignora o próprio filtro
    const facetas = { tema: {}, fmt: {}, ano: {}, vol: {} };
    const soma = (o, k) => { o[k] = (o[k] || 0) + 1; };
    for (const t of idx.trechos) {
      if (passa(t, 'tema')) t.tm.forEach(x => soma(facetas.tema, x));
      if (passa(t, 'fmt')) t.f.forEach(x => soma(facetas.fmt, x));
      if (passa(t, 'ano')) soma(facetas.ano, t.d.slice(0, 4));
      if (passa(t, 'vol')) soma(facetas.vol, t.v);
    }
    return { res, ts, facetas };
  }

  // ---------- desenho ----------
  function desenharFiltros(f) {
    const n = x => x ? `<span class="n">${x}</span>` : '<span class="n">0</span>';
    $('filtros').innerHTML = `
      <h4>Tipo de ensinamento</h4>
      ${idx.formatos.map(x => `<label><input type="checkbox" data-fmt="${x.id}" ${estado.fmt.includes(x.id) ? 'checked' : ''}> ${MS.esc(x.nome)} ${n(f.fmt[x.id])}</label>`).join('')}
      <h4>Data</h4>
      <select id="f-ano" aria-label="Ano"><option value="">Todos os anos</option>${anos.map(a => `<option ${estado.ano === a ? 'selected' : ''} value="${a}">${a} (${f.ano[a] || 0})</option>`).join('')}</select>
      <div style="height:6px"></div>
      <select id="f-mes" aria-label="Mês"><option value="">Todos os meses</option>${meses.filter(m => !estado.ano || m.startsWith(estado.ano)).map(m => `<option ${estado.mes === m ? 'selected' : ''} value="${m}">${MS.mesExtenso(m)}</option>`).join('')}</select>
      <h4>Volume</h4>
      <select id="f-vol" aria-label="Volume"><option value="">Todos os volumes</option>${vols.map(v => `<option ${estado.vol === String(v) ? 'selected' : ''} value="${v}">Volume ${v} (${f.vol[v] || 0})</option>`).join('')}</select>
      <h4>Assuntos <span class="muted" style="text-transform:none;letter-spacing:0;font-weight:400">(todos os marcados)</span></h4>
      ${idx.grupos.map(g => `<div class="g-${g.id}" style="margin-bottom:6px">
        ${idx.temas.filter(t => t.grupo === g.id).map(t => `<label title="${MS.esc(t.descricao)}"><input type="checkbox" data-tema="${t.id}" ${estado.temas.includes(t.id) ? 'checked' : ''} style="accent-color:var(--cor)"> ${MS.esc(t.nome)} ${n(f.tema[t.id])}</label>`).join('')}
      </div>`).join('')}`;
  }

  function desenharAtivos() {
    const chips = [];
    if (estado.q) chips.push(['q', `Busca: “${estado.q}”`]);
    estado.temas.forEach(t => chips.push(['tema:' + t, idx.tema[t].nome, MS.grupoCls(idx, t)]));
    estado.fmt.forEach(f => chips.push(['fmt:' + f, idx.formato[f].nome, 'fmt']));
    if (estado.ano) chips.push(['ano', estado.ano]);
    if (estado.mes) chips.push(['mes', MS.mesExtenso(estado.mes)]);
    if (estado.vol) chips.push(['vol', 'Volume ' + estado.vol]);
    if (estado.g) chips.push(['g', 'Termo: ' + estado.g]);
    if (estado.ids) chips.push(['ids', estado.idsRotulo || `${estado.ids.size} trechos selecionados`]);
    $('ativos').innerHTML = chips.map(([k, r, cls]) => `<span class="chip x ${cls || ''}" data-tira="${k}" title="Remover filtro">${MS.esc(r)} ✕</span>`).join('') +
      (chips.length > 1 ? '<span class="chip x kw" data-tira="*">Limpar tudo</span>' : '');
    $('ativos').style.marginBottom = chips.length ? '6px' : '0';
  }

  function desenharLinha(res) {
    const filtrado = estado.q || estado.temas.length || estado.fmt.length || estado.g || estado.ids;
    if (!filtrado || !res.length || estado.mes) { $('linha').hidden = true; return; }
    const c = {};
    res.forEach(t => { const m = t.d.slice(0, 7); c[m] = (c[m] || 0) + 1; });
    const max = Math.max(...Object.values(c));
    $('linha').hidden = false;
    $('linha').innerHTML = `<div class="small muted">Distribuição no tempo · clique num mês para filtrar</div>
      <div class="mini-linha">${meses.map(m => `<i title="${MS.mesExtenso(m)}: ${c[m] || 0}" data-mes="${m}" style="height:${(c[m] || 0) / max * 100}%;cursor:${c[m] ? 'pointer' : 'default'}"></i>`).join('')}</div>
      <div class="mini-eixo"><span>${MS.mesCurto(meses[0])}</span><span>${MS.mesCurto(meses[Math.floor(meses.length / 2)])}</span><span>${MS.mesCurto(meses[meses.length - 1])}</span></div>`;
  }

  let ultimo = { res: [], ts: [] }, mostrados = 0;
  const PASSO_LISTA = 40, PASSO_LER = 12;

  function linkTrecho(t) {
    return `leitura.html?v=${t.v}${estado.q ? '&q=' + encodeURIComponent(estado.q) : ''}#${t.id}`;
  }

  function cartao(t, ts) {
    const txt = textos ? textos[t.id] : null;
    const artigos = t.a.map(id => `<a class="chip kw" href="#" data-art="${id}">📰 ${MS.esc(idx.artigo[id].t || idx.artigo[id].tj)}</a>`).join('');
    return `<div class="res">
      <div class="meta"><span>${MS.dataExtenso(t.d)}</span><span>· vol. ${t.v}</span>${MS.chipsFormato(idx, t)}${t.inc ? '<span class="aviso">data a conferir</span>' : ''}</div>
      <h3><a href="${linkTrecho(t)}">${MS.destacar(t.t, ts)}</a></h3>
      ${txt && ts.length ? `<div class="trecho-txt">${MS.contexto(txt, ts)}</div>` : ''}
      <div class="chips">${MS.chipsTemas(idx, t)}${artigos}</div>
    </div>`;
  }

  async function blocoLeitura(lista, ts) {
    const porVol = {};
    await Promise.all([...new Set(lista.map(t => t.v))].map(async v => { porVol[v] = await MS.vol(v); }));
    let html = '', dataAnt = null;
    for (const t of lista) {
      const cheio = porVol[t.v].trechos.find(x => x.id === t.id);
      if (t.d !== dataAnt) html += `<h2 class="dia-sep">${MS.dataExtenso(t.d)} <small>vol. ${t.v}</small></h2>`;
      dataAnt = t.d;
      html += `<section class="trecho">
        <div class="marcador"><span class="tit">${MS.destacar(t.t, ts)}</span><span class="edit">título editorial</span>
          <a class="small" href="${linkTrecho(t)}">ver no volume ↗</a></div>
        ${cheio.paras.map(p => p.t === 'q' ? '<p class="q">Pergunta</p>' : p.t === 'a' ? '<p class="a">Orientação</p>'
          : p.t === 'ref' ? `<div class="ref">📰 ${MS.destacar(p.x, ts)}</div>` : `<p>${MS.destacar(p.x, ts)}</p>`).join('')}
        <div class="rodape-trecho">${MS.chipsTemas(idx, t)}${t.a.map(id => `<a class="chip kw" href="#" data-art="${id}">📰 Ler “${MS.esc(idx.artigo[id].t || idx.artigo[id].tj)}”</a>`).join('')}</div>
      </section>`;
    }
    return `<div class="texto">${html}</div>`;
  }

  async function mostrarMais() {
    const { res, ts } = ultimo;
    const passo = estado.modo === 'ler' ? PASSO_LER : PASSO_LISTA;
    const fatia = res.slice(mostrados, mostrados + passo);
    document.querySelector('#resultados .mais')?.remove();
    const html = estado.modo === 'ler' ? await blocoLeitura(fatia, ts) : fatia.map(t => cartao(t, ts)).join('');
    $('resultados').insertAdjacentHTML('beforeend', html);
    mostrados += fatia.length;
    if (mostrados < res.length) {
      $('resultados').insertAdjacentHTML('beforeend', `<button class="mais">Mostrar mais (${res.length - mostrados} restantes)</button>`);
    }
  }

  let geracao = 0;
  async function atualizar() {
    const minha = ++geracao;
    paraUrl();
    desenharAtivos();
    const r = await filtrar();
    if (minha !== geracao) return;
    ultimo = r;
    desenharFiltros(r.facetas);
    desenharLinha(r.res);
    document.querySelectorAll('.seg button').forEach(b => b.classList.toggle('on', b.dataset.modo === estado.modo));
    $('conta').textContent = `${r.res.length.toLocaleString('pt-BR')} ${r.res.length === 1 ? 'trecho' : 'trechos'}`;
    $('resultados').innerHTML = r.res.length ? '' : '<p class="muted">Nenhum trecho com esses critérios.</p>';
    mostrados = 0;
    if (r.res.length) await mostrarMais();
  }

  // ---------- eventos ----------
  let espera;
  $('q').addEventListener('input', () => {
    clearTimeout(espera);
    espera = setTimeout(() => { estado.q = $('q').value.trim(); atualizar(); }, 350);
  });
  $('form-busca').addEventListener('submit', e => { e.preventDefault(); estado.q = $('q').value.trim(); atualizar(); });
  $('btn-filtros').onclick = () => $('filtros').classList.toggle('aberto');
  $('ordem').onchange = e => { estado.ordem = e.target.value; atualizar(); };
  document.querySelectorAll('.seg button').forEach(b => b.onclick = () => { estado.modo = b.dataset.modo; atualizar(); });

  $('filtros').addEventListener('change', e => {
    const el = e.target;
    if (el.dataset.tema) estado.temas = el.checked ? [...estado.temas, el.dataset.tema] : estado.temas.filter(x => x !== el.dataset.tema);
    if (el.dataset.fmt) estado.fmt = el.checked ? [...estado.fmt, el.dataset.fmt] : estado.fmt.filter(x => x !== el.dataset.fmt);
    if (el.id === 'f-ano') { estado.ano = el.value; if (estado.mes && !estado.mes.startsWith(el.value)) estado.mes = ''; }
    if (el.id === 'f-mes') estado.mes = el.value;
    if (el.id === 'f-vol') estado.vol = el.value;
    atualizar();
  });

  $('ativos').addEventListener('click', e => {
    const k = e.target.closest('[data-tira]')?.dataset.tira;
    if (!k) return;
    if (k === '*') {
      Object.assign(estado, { q: '', temas: [], fmt: [], ano: '', mes: '', vol: '', g: '', ids: null, idsRotulo: '' });
      $('q').value = '';
    } else if (k === 'q') { estado.q = ''; $('q').value = ''; }
    else if (k.startsWith('tema:')) estado.temas = estado.temas.filter(x => x !== k.slice(5));
    else if (k.startsWith('fmt:')) estado.fmt = estado.fmt.filter(x => x !== k.slice(4));
    else if (k === 'ids') { estado.ids = null; estado.idsRotulo = ''; }
    else estado[k] = '';
    atualizar();
  });

  $('linha').addEventListener('click', e => {
    const m = e.target.dataset.mes;
    if (!m || e.target.style.height === '0%') return;
    estado.mes = m;
    estado.ano = m.slice(0, 4);
    atualizar();
  });

  $('resultados').addEventListener('click', e => {
    if (e.target.closest('.mais')) { mostrarMais(); return; }
    const a = e.target.closest('[data-art]');
    if (a) { e.preventDefault(); MS.abrirArtigo(a.dataset.art); }
  });

  atualizar();
})();
