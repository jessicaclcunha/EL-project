let ready    = false;
let grammar  = '';
let lastSugg = [];

const EXAMPLE = `start: Program

Program   -> StmtList
StmtList  -> Stmt StmtListR
StmtListR -> SEMI Stmt StmtListR | epsilon
Stmt      -> ID ASSIGN Expr
Expr      -> Term ExprR
ExprR     -> PLUS Term ExprR | epsilon
Term      -> ID | NUMBER

ID     = /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER = /[0-9]+/
PLUS   = /\\+/
SEMI   = /;/
ASSIGN = /:=/`;


const $ = id => document.getElementById(id);

function showTab(id) {
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.dataset.tab === id));
  document.querySelectorAll('.panel').forEach(p =>
    p.classList.toggle('active', p.id === `panel-${id}`));
}

function setLoading(btn, on) {
  if (!btn._lbl) btn._lbl = btn.innerHTML;
  btn.disabled  = on;
  btn.innerHTML = on ? `<span class="spin"></span>${btn._lbl}` : btn._lbl;
}

function showBanners(id, items, type) {
  const icons = { ok: '✓', warn: '⚠', error: '✕' };
  $(id).innerHTML = items
    .map(m => `<div class="banner ${type}">
                 <span>${icons[type]}</span><span>${m}</span>
               </div>`)
    .join('');
}

async function post(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


$('btn-analyse').addEventListener('click', async () => {
  const btn = $('btn-analyse');
  const src = $('grammar').value.trim();
  if (!src) return;

  setLoading(btn, true);
  $('ff-banners').innerHTML = '';
  ready = false;
  $('btn-generate').disabled = true;

  try {
    const d = await post('/api/analyse', { grammar: src });

    $('ff-empty').style.display  = 'none';
    $('ff-result').style.display = 'block';

    if (!d.ok) {
      showBanners('ff-banners', d.errors, 'error');
      $('ff-tbody').innerHTML = '';
      $('la-tbody').innerHTML = '';
      showTab('ff');
      return;
    }

    // banners
    const warnings = d.warnings || [];
    if (warnings.length > 0) {
      showBanners('ff-banners', warnings, 'warn');
    }
 
    // Banner principal: OK ou conflito (em separado, abaixo dos avisos)
    const $banners = $('ff-banners');
    if (d.conflicts.length === 0) {
      // Gramática LL(1) sem conflitos → verde
      $banners.innerHTML += `<div class="banner ok"><span>✓</span><span>Gramática LL(1) válida — sem conflitos.</span></div>`;
    } else {
      // Conflitos: mostrar quantos + resultado LL(k)
      let msg = `${d.conflicts.length} conflito(s) LL(1) detectado(s).`;
      if (d.llk !== null && d.llk !== undefined) {
        msg += `  A gramática <strong>É LL(${d.llk})</strong>.`;
      } else {
        msg += `  A gramática <strong>não é LL(k)</strong> para k ≤ 5.`;
      }
      $banners.innerHTML += `<div class="banner warn"><span>⚠</span><span>${msg}</span></div>`;
    }

    // FIRST / FOLLOW
    const nts = Object.keys(d.first).sort();
    $('ff-tbody').innerHTML = nts.map(nt => `
      <tr>
        <td class="nt">${esc(nt)}</td>
        <td class="set">{ ${(d.first[nt]  || []).map(esc).join(', ') || '—'} }</td>
        <td class="set">{ ${(d.follow[nt] || []).map(esc).join(', ') || '—'} }</td>
      </tr>`).join('');

    // Lookahead — tabela separada na mesma página
    $('la-tbody').innerHTML = d.lookahead.map(row => `
      <tr>
        <td class="nt">${esc(row.nt)}</td>
        <td class="prod">${esc(row.production)}</td>
        <td class="la">{ ${row.lookahead.map(esc).join(', ') || '—'} }</td>
        <td class="nullable">${row.nullable ? 'sim' : ''}</td>
      </tr>`).join('');

    // conflitos
    const badge = $('badge');
    if (d.conflicts.length > 0) {
      badge.style.display = 'inline';
      badge.textContent   = d.conflicts.length;

      $('conf-empty').style.display  = 'none';
      $('conf-result').style.display = 'block';
      $('conf-list').innerHTML = d.conflicts.map(c => `
        <div class="card">
          <div class="card-label red">${esc(c.type)}</div>
          <div class="card-nt">${esc(c.nonterminal)}</div>
          ${c.message ? `<div class="card-msg">${esc(c.message)}</div>` : ''}
        </div>`).join('');

      lastSugg = d.suggestions;
      if (d.suggestions.length > 0) {
        $('sugg-section').style.display = 'block';
        $('sugg-list').innerHTML = d.suggestions.map(s => `
          <div class="card">
            <div class="card-label indigo">${esc(s.technique)}</div>
            <div class="card-nt">${esc(s.nonterminal)}</div>
            <div class="card-rules">${esc(s.new_rules.join('\n'))}</div>
          </div>`).join('');
      }
    } else {
      badge.style.display = 'none';
      $('conf-empty').style.display  = 'flex';
      $('conf-result').style.display = 'none';
      $('btn-generate').disabled = false;
      ready   = true;
      grammar = src;
    }

    buildTable(d.table);
    showTab('ff');

  } finally {
    setLoading(btn, false);
  }
});

// ── aplicar sugestões ─────────────────────────────────────────────────
$('btn-apply').addEventListener('click', async () => {
  const btn = $('btn-apply');
  setLoading(btn, true);
  try {
    const d = await post('/api/apply_suggestions', {
      grammar:     $('grammar').value,
      suggestions: lastSugg,
    });
    if (!d.ok) { alert(d.errors.join('\n')); return; }
    $('grammar').value = d.grammar;
    $('btn-analyse').click();
  } finally {
    setLoading(btn, false);
  }
});

// ── tabela LL(1) ──────────────────────────────────────────────────────
function buildTable({ terminals, rows }) {
  $('table-empty').style.display  = 'none';
  $('table-result').style.display = 'block';

  let html = `<thead><tr>
    <th>NT \\ T</th>
    ${terminals.map(t => `<th>${esc(t)}</th>`).join('')}
  </tr></thead><tbody>`;

  for (const row of rows) {
    html += `<tr><td class="ll-hd">${esc(row.nt)}</td>`;
    for (const t of terminals) {
      const v   = row.cells[t] || '';
      const cls = v ? (v.includes('⚠') ? 'll-bad' : 'll-ok') : '';
      html += `<td class="${cls}">${esc(v)}</td>`;
    }
    html += '</tr>';
  }
  $('ll-table').innerHTML = html + '</tbody>';
}

// ── gerar parsers ─────────────────────────────────────────────────────
$('btn-generate').addEventListener('click', async () => {
  const btn = $('btn-generate');
  setLoading(btn, true);
  try {
    const d = await post('/api/generate', { grammar });
    if (!d.ok) { alert(d.errors.join('\n')); return; }

    $('parsers-empty').style.display  = 'none';
    $('parsers-result').style.display = 'block';
    $('code-rd').textContent = d.rd;
    $('code-td').textContent = d.td;
    hljs.highlightElement($('code-rd'));
    hljs.highlightElement($('code-td'));
    showTab('parsers');
  } finally {
    setLoading(btn, false);
  }
});

// selector rd / td
document.querySelectorAll('.ps-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.ps-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.parser-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`pane-${btn.dataset.parser}`).classList.add('active');
  });
});

async function dlParser(type) {
  const r = await fetch(`/api/download/${type}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grammar }),
  });
  if (!r.ok) { alert('Erro ao descarregar.'); return; }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(await r.blob());
  a.download = `${type}.py`;
  a.click();
}
$('btn-dl-rd').addEventListener('click', () => dlParser('rd'));
$('btn-dl-td').addEventListener('click', () => dlParser('td'));

// ── testar frase ──────────────────────────────────────────────────────
async function runPhrase() {
  const btn    = $('btn-phrase');
  const phrase = $('phrase-input').value.trim();
  $('phrase-banners').innerHTML = '';
  $('phrase-result').style.display = 'none';

  if (!ready) {
    showBanners('phrase-banners',
      ['Analisa a gramática primeiro (sem conflitos).'], 'warn');
    return;
  }
  if (!phrase) return;

  setLoading(btn, true);
  try {
    const d = await post('/api/parse_phrase', { grammar, phrase });

    if (!d.ok) {
      showBanners('phrase-banners', d.errors, 'error');
      return;
    }

    showBanners('phrase-banners', ['Frase reconhecida com sucesso.'], 'ok');
    $('phrase-result').style.display = 'block';

    $('tree-svg-wrap').innerHTML = d.tree_svg;

    $('steps-tbody').innerHTML = d.steps.map(s => {
      const cls = s.action === 'ACEITE'            ? 's-ok'
                : s.action.startsWith('produção')   ? 's-prod'
                : 's-adv';
      return `<tr>
        <td>${s.step}</td>
        <td style="font-family:var(--mono);font-size:12px">${(s.stack || []).map(esc).join(' ')}</td>
        <td style="font-family:var(--mono)">${esc(s.input)}</td>
        <td class="${cls}">${esc(s.action)}</td>
      </tr>`;
    }).join('');

  } finally {
    setLoading(btn, false);
  }
}

$('btn-phrase').addEventListener('click', runPhrase);
$('phrase-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') runPhrase();
});

// ── tabs + exemplo ────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(t =>
  t.addEventListener('click', () => showTab(t.dataset.tab)));

$('btn-example').addEventListener('click', () => {
  $('grammar').value = EXAMPLE;
});