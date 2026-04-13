let ready    = false;
let grammar  = '';
let lastSugg = [];
let visitorSkeleton = '';
let lastTurtle = '';

let visitorEditor = null;

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

window.addEventListener('DOMContentLoaded', () => {
  const ta = $('visitor-code');
  if (!ta || typeof CodeMirror === 'undefined') return;
  visitorEditor = CodeMirror.fromTextArea(ta, {
    mode: 'python', theme: 'dracula', lineNumbers: true,
    indentUnit: 4, tabSize: 4, indentWithTabs: false,
    lineWrapping: false, autofocus: false,
    extraKeys: {
      Tab:         cm => cm.execCommand('indentMore'),
      'Shift-Tab': cm => cm.execCommand('indentLess'),
    },
  });
  visitorEditor.setSize('100%', '400px');
});

function getVisitorCode() {
  return visitorEditor ? visitorEditor.getValue() : $('visitor-code').value;
}
function setVisitorCode(code) {
  if (visitorEditor) visitorEditor.setValue(code);
  else $('visitor-code').value = code;
}


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
    .map(m => `<div class="banner ${type}"><span>${icons[type]}</span><span>${m}</span></div>`)
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


// ── analisar ──────────────────────────────────────────────────────────
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

    const warnings = d.warnings || [];
    if (warnings.length > 0) showBanners('ff-banners', warnings, 'warn');

    const $banners = $('ff-banners');
    if (d.conflicts.length === 0) {
      $banners.innerHTML += `<div class="banner ok"><span>✓</span><span>Gramática LL(1) válida — sem conflitos.</span></div>`;
    } else {
      let msg = `${d.conflicts.length} conflito(s) LL(1) detectado(s).`;
      if (d.llk !== null && d.llk !== undefined) {
        msg += `  A gramática <strong>É LL(${d.llk})</strong>.`;
      } else {
        msg += `  A gramática <strong>não é LL(k)</strong> para k ≤ 5.`;
      }
      $banners.innerHTML += `<div class="banner warn"><span>⚠</span><span>${msg}</span></div>`;
    }

    const nts = Object.keys(d.first).sort();
    $('ff-tbody').innerHTML = nts.map(nt => `
      <tr>
        <td class="nt">${esc(nt)}</td>
        <td class="set">{ ${(d.first[nt]  || []).map(esc).join(', ') || '—'} }</td>
        <td class="set">{ ${(d.follow[nt] || []).map(esc).join(', ') || '—'} }</td>
      </tr>`).join('');

    $('la-tbody').innerHTML = d.lookahead.map(row => `
      <tr>
        <td class="nt">${esc(row.nt)}</td>
        <td class="prod">${esc(row.production)}</td>
        <td class="la">{ ${row.lookahead.map(esc).join(', ') || '—'} }</td>
        <td class="nullable">${row.nullable ? 'sim' : ''}</td>
      </tr>`).join('');

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

$('btn-apply').addEventListener('click', async () => {
  const btn = $('btn-apply');
  setLoading(btn, true);
  try {
    const d = await post('/api/apply_suggestions', {
      grammar: $('grammar').value, suggestions: lastSugg,
    });
    if (!d.ok) { alert(d.errors.join('\n')); return; }
    $('grammar').value = d.grammar;
    $('btn-analyse').click();
  } finally {
    setLoading(btn, false);
  }
});

function buildTable({ terminals, rows }) {
  $('table-empty').style.display  = 'none';
  $('table-result').style.display = 'block';
  let html = `<thead><tr><th>NT \\ T</th>${terminals.map(t => `<th>${esc(t)}</th>`).join('')}</tr></thead><tbody>`;
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

    if (d.visitor) {
      visitorSkeleton = d.visitor;
      setVisitorCode(d.visitor);
      if (visitorEditor) setTimeout(() => visitorEditor.refresh(), 50);
      $('visitor-empty').style.display  = 'none';
      $('visitor-result').style.display = 'block';
    }

    showTab('parsers');
  } finally {
    setLoading(btn, false);
  }
});

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


// ── Sub-abas ──────────────────────────────────────────────────────────
function setActiveSubTab(target) {
  document.querySelectorAll('.sub-tab').forEach(b => {
    const active = b.dataset.sub === target;
    b.dataset.active     = active ? 'true' : 'false';
    b.style.color        = active ? 'var(--indigo)' : 'var(--muted)';
    b.style.borderBottom = active ? '2px solid var(--indigo)' : '2px solid transparent';
  });
  document.querySelectorAll('.sub-pane').forEach(p => {
    p.style.display = p.id === `sub-${target}` ? 'block' : 'none';
  });
  if (target === 'visitor' && visitorEditor) {
    setTimeout(() => visitorEditor.refresh(), 10);
  }
}
document.querySelectorAll('.sub-tab').forEach(btn => {
  btn.addEventListener('click', () => setActiveSubTab(btn.dataset.sub));
});
setActiveSubTab('parsing');


// ── Testar frase ──────────────────────────────────────────────────────
async function runPhrase() {
  const btn    = $('btn-phrase');
  const phrase = $('phrase-input').value.trim();
  $('phrase-banners').innerHTML = '';
  $('phrase-result').style.display = 'none';
  $('phrase-empty').style.display  = 'flex';

  if (!ready) {
    showBanners('phrase-banners', ['Analisa a gramática primeiro (sem conflitos).'], 'warn');
    return;
  }
  if (!phrase) return;

  setLoading(btn, true);
  try {
    const d = await post('/api/parse_phrase', { grammar, phrase });
    if (!d.ok) { showBanners('phrase-banners', d.errors, 'error'); return; }

    showBanners('phrase-banners', ['Frase reconhecida com sucesso.'], 'ok');
    $('phrase-empty').style.display  = 'none';
    $('phrase-result').style.display = 'block';
    $('tree-svg-wrap').innerHTML     = d.tree_svg;

    $('steps-tbody').innerHTML = d.steps.map(s => {
      const cls = s.action === 'ACEITE'           ? 's-ok'
                : s.action.startsWith('produção') ? 's-prod' : 's-adv';
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
  if (e.key !== 'Enter') return;
  const visitorTab    = document.querySelector('.sub-tab[data-sub="visitor"]');
  const visitorActive = visitorTab && visitorTab.dataset.active === 'true';
  if (visitorActive) runVisitor(); else runPhrase();
});


// ── Visitor (com melhor feedback de erros) ────────────────────────────
async function runVisitor() {
  const btn          = $('btn-run-visitor');
  const phrase       = $('phrase-input').value.trim();
  const visitor_code = getVisitorCode();

  $('visitor-banners').innerHTML = '';
  $('visitor-output-wrap').style.display = 'none';

  if (!ready) {
    showBanners('visitor-banners', ['Analisa a gramática primeiro (sem conflitos).'], 'warn');
    return;
  }
  if (!phrase) {
    showBanners('visitor-banners', ['Introduz uma frase no campo acima.'], 'warn');
    return;
  }

  setLoading(btn, true);
  try {
    const d = await post('/api/run_visitor', { grammar, phrase, visitor_code });

    if (!d.ok) {
      showVisitorError(d);
      if (d.line && visitorEditor) {
        visitorEditor.focus();
        visitorEditor.setCursor({ line: d.line - 1, ch: 0 });
        visitorEditor.addLineClass(d.line - 1, 'background', 'cm-error-line');
        setTimeout(() => visitorEditor.removeLineClass(d.line - 1, 'background', 'cm-error-line'), 3000);
      }
      return;
    }

    showBanners('visitor-banners', ['Visitor executado com sucesso.'], 'ok');
    $('visitor-output-wrap').style.display = 'block';
    $('visitor-output').textContent = d.output;
  } finally {
    setLoading(btn, false);
  }
}

function showVisitorError(d) {
  const titles = {
    grammar:        'Erro na gramática',
    phrase:         'Erro na frase de input',
    compile:        'Erro de sintaxe no código do visitor',
    define:         'Erro ao carregar o visitor',
    missing_class:  'Classe em falta',
    runtime:        'Erro durante a execução do visitor',
  };
  const title = titles[d.error_kind] || 'Erro';
  const lines = (d.errors || []).filter(s => s);
  $('visitor-banners').innerHTML = `
    <div class="banner error" style="flex-direction:column;align-items:flex-start;gap:6px">
      <div style="display:flex;align-items:center;gap:8px"><span>✕</span><strong>${esc(title)}</strong></div>
      <pre style="margin:4px 0 0;font-family:var(--mono);font-size:12px;line-height:1.5;white-space:pre-wrap;color:#7f1d1d">${
        lines.map(esc).join('\n')
      }</pre>
    </div>`;
}

$('btn-run-visitor').addEventListener('click', runVisitor);

$('btn-reset-visitor').addEventListener('click', () => {
  if (visitorSkeleton) setVisitorCode(visitorSkeleton);
});
$('btn-dl-visitor').addEventListener('click', () => dlParser('visitor'));


// ── Ontologia OWL/RDF ────────────────────────────────────────────────
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

      const lines    = d.turtle.split('\n').length;
      const triplos  = (d.turtle.match(/^[^#@\s].*\.\s*$/gm) || []).length;
      $('ontology-stats').textContent =
        `${lines} linhas · ~${triplos} triplos · gramática "${name}"`;

      $('ontology-code').textContent = d.turtle;

      showBanners('ontology-banners', ['Ontologia gerada com sucesso.'], 'ok');
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


// ── tabs principais + exemplo ─────────────────────────────────────────
document.querySelectorAll('.tab').forEach(t =>
  t.addEventListener('click', () => showTab(t.dataset.tab)));

$('btn-example').addEventListener('click', () => {
  $('grammar').value = EXAMPLE;
});