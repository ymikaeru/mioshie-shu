// Leitura na sequência original: um volume inteiro, dia a dia, com os títulos editoriais como marcadores.
MS.cabecalho('leitura.html');

(async () => {
  const params = new URLSearchParams(location.search);
  const idx = await MS.index();
  const vols = [...new Set(idx.trechos.map(t => t.v))];
  let v = Number(params.get('v')) || Number((location.hash.match(/#v(\d+)-/) || [])[1]) || vols[0];
  if (!vols.includes(v)) v = vols[0];
  const ts = MS.termos(params.get('q') || '');
  const dados = await MS.vol(v);
  document.title = `Vol. ${v} · Mioshie-shu`;

  // agrupa trechos consecutivos da mesma data (a ordem do volume é preservada)
  const dias = [];
  for (const t of dados.trechos) {
    const ultimo = dias[dias.length - 1];
    if (ultimo && ultimo.data === t.data) ultimo.trechos.push(t);
    else dias.push({ data: t.data, local: t.local, trechos: [t] });
  }

  const pos = vols.indexOf(v);
  document.getElementById('indice').innerHTML = `
    <div class="vols">
      ${pos > 0 ? `<a href="leitura.html?v=${vols[pos - 1]}" title="Volume anterior">‹</a>` : ''}
      <select id="sel-vol" aria-label="Volume">${vols.map(x => `<option value="${x}" ${x === v ? 'selected' : ''}>Volume ${x}</option>`).join('')}</select>
      ${pos < vols.length - 1 ? `<a href="leitura.html?v=${vols[pos + 1]}" title="Próximo volume">›</a>` : ''}
    </div>
    ${dias.map((d, i) => `<div class="dia"><a href="#dia-${i}" style="padding:0;border:0;color:inherit">${MS.dataExtenso(d.data)}</a></div>
      ${d.trechos.map(t => `<a href="#${t.id}" data-id="${t.id}">${MS.esc(t.titulo)}</a>`).join('')}`).join('')}`;
  document.getElementById('sel-vol').onchange = e => { location.href = `leitura.html?v=${e.target.value}`; };

  document.getElementById('texto').innerHTML = `
    <div class="cab-vol">御教え集 · Volume ${v} · ${dados.trechos.length} trechos em ${dias.length} ${dias.length === 1 ? 'dia' : 'dias'}</div>
    ${dias.map((d, i) => `
      <h2 class="dia-sep" id="dia-${i}">${MS.dataExtenso(d.data)}${d.local ? `<small>${MS.esc(d.local)}</small>` : ''}</h2>
      ${d.trechos.map(t => htmlTrecho(t, idx.porId[t.id])).join('')}`).join('')}
    <div class="nav-vol">
      ${pos > 0 ? `<a href="leitura.html?v=${vols[pos - 1]}">‹ Volume ${vols[pos - 1]}</a>` : '<span></span>'}
      ${pos < vols.length - 1 ? `<a href="leitura.html?v=${vols[pos + 1]}">Volume ${vols[pos + 1]} ›</a>` : ''}
    </div>`;

  function htmlTrecho(t, info) {
    let html = '', emPergunta = false, refMostrada = false;
    for (const p of t.paras) {
      if (p.t === 'q') { html += (emPergunta ? '</div>' : '') + '<p class="q">Pergunta</p><div class="bloco-q">'; emPergunta = true; continue; }
      if (p.t === 'a') { html += (emPergunta ? '</div>' : '') + '<p class="a">Orientação</p>'; emPergunta = false; continue; }
      if (p.t === 'label') { html += `<p class="label">${MS.esc(p.x.replace(/[()]/g, ''))}</p>`; continue; }
      if (p.t === 'ref') {
        const botoes = !refMostrada && info.a.length
          ? info.a.map(id => `<button data-art="${id}">Ler “${MS.esc(idx.artigo[id].t || idx.artigo[id].tj)}”</button>`).join('') : '';
        refMostrada = refMostrada || !!botoes;
        html += `<div class="ref">📰 ${MS.destacar(p.x, ts)}${botoes ? '<div style="margin-top:6px">' + botoes + '</div>' : ''}</div>`;
        continue;
      }
      html += `<p>${MS.destacar(p.x, ts)}</p>`;
    }
    if (emPergunta) html += '</div>';
    if (info.a.length && !refMostrada) {
      html += `<div class="ref">📰 Artigo lido: ${info.a.map(id => `<button data-art="${id}">${MS.esc(idx.artigo[id].t || idx.artigo[id].tj)}</button>`).join('')}</div>`;
    }
    const rel = info.r.map(id => idx.porId[id]).filter(Boolean);
    return `<section class="trecho" id="${t.id}">
      <div class="marcador"><span class="tit">${MS.destacar(t.titulo, ts)}</span><span class="edit" title="Título criado na tradução; o original registra apenas a data">título editorial</span></div>
      ${html}
      <div class="rodape-trecho">
        <span class="data-orig">(${MS.dataExtenso(t.data)})</span>
        ${MS.chipsFormato(idx, info)} ${MS.chipsTemas(idx, info)}
        ${info.inc ? `<span class="aviso" title="${MS.esc(info.inc)}">data a conferir</span>` : ''}
      </div>
      ${rel.length ? `<details class="rel"><summary>O mesmo assunto em outros dias (${rel.length})</summary><ul>
        ${rel.map(r => `<li><a href="${MS.link(r)}">${MS.dataExtenso(r.d)}</a> · ${MS.esc(r.t)} <span class="muted">(vol. ${r.v})</span></li>`).join('')}
      </ul></details>` : ''}
    </section>`;
  }

  document.getElementById('texto').addEventListener('click', e => {
    const b = e.target.closest('[data-art]');
    if (b) MS.abrirArtigo(b.dataset.art);
  });

  // foco no trecho do link e marcação do índice conforme a rolagem
  function focar() {
    document.querySelectorAll('.trecho.foco').forEach(x => x.classList.remove('foco'));
    const alvo = location.hash && document.getElementById(location.hash.slice(1));
    if (alvo) {
      alvo.scrollIntoView();
      if (alvo.classList.contains('trecho')) alvo.classList.add('foco');
    }
  }
  focar();
  addEventListener('hashchange', focar);

  const links = Object.fromEntries([...document.querySelectorAll('#indice a[data-id]')].map(a => [a.dataset.id, a]));
  const box = document.getElementById('indice');
  let atual;
  const obs = new IntersectionObserver(ents => {
    for (const e of ents) {
      if (!e.isIntersecting || !links[e.target.id]) continue;
      if (atual) atual.classList.remove('atual');
      atual = links[e.target.id];
      atual.classList.add('atual');
      if (atual.offsetTop < box.scrollTop || atual.offsetTop > box.scrollTop + box.clientHeight - 30) box.scrollTop = atual.offsetTop - 80;
    }
  }, { rootMargin: '-80px 0px -70% 0px' });
  document.querySelectorAll('.trecho').forEach(s => obs.observe(s));
})();
