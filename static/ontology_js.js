// ═══════════════════════════════════════════════════════════════════════
// ONTOLOGIA — Geração + Queries SPARQL
// Substitui o bloco "── Ontologia OWL/RDF ──" existente em app.js
// ═══════════════════════════════════════════════════════════════════════

let lastTurtle = '';

// ── Sub-abas Turtle / SPARQL ──────────────────────────────────────────
function setOntoTab(target) {
  document.querySelectorAll('.onto-tab').forEach(btn => {
    const active = btn.dataset.onto === target;
    btn.classList.toggle('active', active);
    btn.style.color        = active ? 'var(--indigo)' : 'var(--muted)';
    btn.style.borderBottom = active ? '2px solid var(--indigo)' : '2px solid transparent';
  });
  document.querySelectorAll('.onto-pane').forEach(p => {
    p.style.display = p.id === `onto-${target}` ? 'block' : 'none';
  });
}

document.querySelectorAll('.onto-tab').forEach(btn =>
  btn.addEventListener('click', () => setOntoTab(btn.dataset.onto))
);

// ── Geração da ontologia ──────────────────────────────────────────────
if ($('btn-gen-ontology')) {

  $('btn-gen-ontology').addEventListener('click', async () => {
    const btn  = $('btn-gen-ontology');
    const name = $('ontology-name').value.trim() || 'GramaticaUtilizador';
    const src  = $('grammar').value.trim();

    $('ontology-banners').innerHTML = '';

    if (!src) {
      showBanners('ontology-banners', ['Introduz uma gramática primeiro.'], 'warn');
      return;
    }

    setLoading(btn, true);
    try {
      const d = await post('/api/ontology', { grammar: src, name });
      if (!d.ok) {
        showBanners('ontology-banners', d.errors || ['Erro a gerar ontologia.'], 'error');
        return;
      }

      lastTurtle = d.turtle;
      $('ontology-empty').style.display  = 'none';
      $('ontology-result').style.display = 'block';
      $('btn-dl-ontology').disabled = false;

      const lines   = d.turtle.split('\n').length;
      const triplos = (d.turtle.match(/^[^#@\s].*\.\s*$/gm) || []).length;
      $('ontology-stats').textContent =
        `${lines} linhas · ~${triplos} triplos · gramática "${name}"`;

      $('ontology-code').textContent = d.turtle;

      showBanners('ontology-banners', ['Ontologia gerada com sucesso.'], 'ok');

      // Carregar catálogo de queries
      loadSparqlCatalogue();

      // Mostrar sub-aba Turtle por defeito
      setOntoTab('turtle');
    } finally {
      setLoading(btn, false);
    }
  });

  $('btn-dl-ontology').addEventListener('click', () => {
    if (!lastTurtle) return;
    const name = $('ontology-name').value.trim() || 'grammar';
    const blob = new Blob([lastTurtle], { type: 'text/turtle' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `${name}.ttl`;
    a.click();
  });
}

// ── Catálogo SPARQL ───────────────────────────────────────────────────
let sparqlCatalogue = [];

async function loadSparqlCatalogue() {
  if (sparqlCatalogue.length) {
    renderSparqlCatalogue();
    return;
  }
  try {
    const r = await fetch('/api/ontology/catalogue');
    const d = await r.json();
    sparqlCatalogue = d.queries || [];
    renderSparqlCatalogue();
  } catch (_) {}
}

function renderSparqlCatalogue() {
  const el = $('sparql-catalogue');
  if (!el) return;
  el.innerHTML = sparqlCatalogue.map(q => `
    <button class="sparql-cat-btn"
            data-key="${esc(q.key)}"
            title="${esc(q.description)}"
            style="text-align:left;padding:6px 10px;height:auto;font-size:12px;
                   font-weight:500;background:var(--panel);border:1px solid var(--border);
                   border-radius:4px;color:var(--text);cursor:pointer;
                   transition:border-color .1s,background .1s;white-space:normal;
                   line-height:1.4">
      ${esc(q.label)}
    </button>`).join('');

  document.querySelectorAll('.sparql-cat-btn').forEach(btn => {
    btn.addEventListener('click', () => runSparqlQuery(btn.dataset.key, ''));
    btn.addEventListener('mouseenter', () => {
      btn.style.borderColor = 'var(--indigo-b)';
      btn.style.background  = 'var(--indigo-l)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.borderColor = 'var(--border)';
      btn.style.background  = 'var(--panel)';
    });
  });
}

// ── Execução de query ─────────────────────────────────────────────────
async function runSparqlQuery(key, customSparql) {
  const src  = $('grammar').value.trim();
  const name = ($('ontology-name').value || '').trim() || 'GramaticaUtilizador';

  $('sparql-banners').innerHTML = '';
  $('sparql-result-empty').style.display = 'none';
  $('sparql-result-wrap').style.display  = 'none';

  if (!src) {
    showBanners('sparql-banners', ['Introduz e analisa uma gramática primeiro.'], 'warn');
    $('sparql-result-empty').style.display = 'flex';
    return;
  }

  // Mudar para aba SPARQL
  setOntoTab('sparql');

  const body = { grammar: src, name };
  if (key)          body.query_key = key;
  if (customSparql) body.sparql    = customSparql;

  const d = await post('/api/ontology/query', body);

  if (!d.ok) {
    showBanners('sparql-banners', d.errors || ['Erro na query.'], 'error');
    $('sparql-result-empty').style.display = 'flex';
    return;
  }

  // Actualizar TTL se vier no resultado (gerado na query)
  if (d.turtle) {
    lastTurtle = d.turtle;
    if ($('ontology-code')) $('ontology-code').textContent = d.turtle;
    if ($('btn-dl-ontology')) $('btn-dl-ontology').disabled = false;
    $('ontology-empty').style.display  = 'none';
    $('ontology-result').style.display = 'block';
  }

  $('sparql-result-title').textContent = d.label || 'Resultado';
  $('sparql-result-desc').textContent  = d.description || '';
  $('sparql-result-count').textContent = `${d.rows.length} linha(s)`;

  // Cabeçalhos
  const labels = d.column_labels || d.columns || [];
  $('sparql-thead').innerHTML = `<tr>${labels.map(l => `<th>${esc(l)}</th>`).join('')}</tr>`;

  // Linhas
  if (!d.rows.length) {
    $('sparql-tbody').innerHTML = `
      <tr><td colspan="${labels.length}"
              style="text-align:center;color:var(--dim);font-size:12px;padding:16px">
        Sem resultados.
      </td></tr>`;
  } else {
    $('sparql-tbody').innerHTML = d.rows.map(row =>
      `<tr>${(d.columns || []).map(col => {
        const v = row[col] || '';
        // Colorir booleanos
        if (v === 'true')  return `<td style="color:var(--green);font-family:var(--mono);font-size:12px">✓</td>`;
        if (v === 'false') return `<td style="color:var(--muted);font-family:var(--mono);font-size:12px">—</td>`;
        return `<td style="font-family:var(--mono);font-size:12px">${esc(v)}</td>`;
      }).join('')}</tr>`
    ).join('');
  }

  $('sparql-result-wrap').style.display = 'block';
}

// Query ad-hoc
if ($('btn-sparql-custom')) {
  $('btn-sparql-custom').addEventListener('click', () => {
    const q = ($('sparql-custom').value || '').trim();
    if (!q) return;
    runSparqlQuery('', q);
  });
}