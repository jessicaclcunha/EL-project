import sys
import io
import re
import uuid
import traceback
from flask import Flask, render_template, request, jsonify, send_file

sys.path.insert(0, 'src')

from gp_parser   import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis import *
from gp_parser_rd import generate_rd_parser
from gp_parser_td import generate_table_parser, TableParser
from gp_visitor   import generate_visitor

app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyse', methods=['POST'])
def analyse():
    src = request.get_json().get('grammar', '')
    grammar  = parse_grammar(src)
    errors   = get_parse_errors()
    warnings = get_parse_warnings()
    if grammar is None:
        return jsonify({'ok': False, 'errors': errors})

    first       = compute_first(grammar)
    follow      = compute_follow(grammar, first)
    conflicts   = check_ll1(grammar, first, follow)
    suggestions = suggest_fixes(grammar, conflicts)
    table       = build_parse_table(grammar, first, follow)

    llk_result = None
    if conflicts:
        k, _ = check_llk(grammar, max_k=5)
        llk_result = k

    return jsonify({
        'ok':          True,
        'warnings':    warnings,
        'first':       {k: sorted(v) for k, v in first.items()},
        'follow':      {k: sorted(v) for k, v in follow.items()},
        'lookahead':   compute_lookahead(grammar, first, follow),
        'conflicts':   ser_conflicts(conflicts),
        'suggestions': ser_suggestions(suggestions),
        'table':       ser_table(table, grammar),
        'llk':         llk_result,
    })


@app.route('/api/apply_suggestions', methods=['POST'])
def apply_suggestions():
    body = request.get_json()
    src  = body.get('grammar', '')
    suggestions = body.get('suggestions', [])

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    replacements = {}
    for s in suggestions:
        for rule_str in s.get('new_rules', []):
            if rule_str.startswith('⚠'):
                continue
            if '->' in rule_str:
                nt = rule_str.split('->')[0].strip()
                replacements.setdefault(nt, []).append(rule_str)

    if not replacements:
        return jsonify({'ok': False, 'errors': ['Nenhuma sugestão aplicável.']})

    return jsonify({'ok': True, 'grammar': rebuild_grammar(src, replacements)})


def rebuild_grammar(src, replacements):
    lines = src.splitlines()
    TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\s*=\s*/")
    RULE_RE  = re.compile(r"^([A-Za-z][A-Za-z0-9_']*)\s*(->|→)")

    rule_lines, token_lines, in_tokens = [], [], False
    for line in lines:
        if not in_tokens and TOKEN_RE.match(line.strip()):
            in_tokens = True
        (token_lines if in_tokens else rule_lines).append(line)

    blocks = []
    i = 0
    while i < len(rule_lines):
        line = rule_lines[i]
        m = RULE_RE.match(line.strip())
        if m:
            nt = m.group(1)
            block_lines = [line]
            i += 1
            while i < len(rule_lines):
                nxt_s = rule_lines[i].strip()
                if nxt_s.startswith('|') or (rule_lines[i] and rule_lines[i][0] in (' ', '\t')):
                    block_lines.append(rule_lines[i])
                    i += 1
                else:
                    break
            blocks.append((nt, block_lines))
        else:
            blocks.append((None, [line]))
            i += 1

    pending  = dict(replacements)
    out_rules = []
    for (nt, block_lines) in blocks:
        if nt is not None and nt in pending:
            out_rules.extend(pending[nt])
            del pending[nt]
            for new_nt in list(pending.keys()):
                if new_nt.startswith(nt):
                    out_rules.extend(pending[new_nt])
                    del pending[new_nt]
        else:
            out_rules.extend(block_lines)

    for nt, rules in pending.items():
        out_rules.extend(rules)

    result_lines = out_rules
    if token_lines:
        if result_lines and result_lines[-1].strip():
            result_lines.append('')
        result_lines.extend(token_lines)
    return '\n'.join(result_lines)


@app.route('/api/generate', methods=['POST'])
def generate():
    src = request.get_json().get('grammar', '')
    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)

    conflicts = check_ll1(grammar, first, follow)
    if conflicts:
        return jsonify({
            'ok': False, 'has_conflicts': True,
            'errors': [f'A gramática tem {len(conflicts)} conflito(s) LL(1). Aplica as sugestões antes de gerar os parsers.'],
        })

    return jsonify({
        'ok': True,
        'rd':      generate_rd_parser(grammar, first, follow),
        'td':      generate_table_parser(grammar, first, follow),
        'visitor': generate_visitor(grammar),
    })


def _build_patterns(grammar):
    patterns = dict(grammar.get_token_patterns())
    for t in grammar.get_terminals():
        if t.startswith(("'", '"')):
            inner = t[1:-1]
            if inner not in patterns.values():
                patterns[inner] = re.escape(inner)
    return patterns


@app.route('/api/parse_phrase', methods=['POST'])
def parse_phrase():
    body = request.get_json()
    src, phrase = body.get('grammar', ''), body.get('phrase', '')

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table  = build_parse_table(grammar, first, follow)
    patterns = dict(grammar.get_token_patterns())
    for t in grammar.get_terminals():
        if t.startswith(("'", '"')):
            inner = t[1:-1]
            if inner not in patterns.values():
                patterns[inner] = re.escape(inner)

    try:
        parser = TableParser(grammar, table, phrase, patterns)
        tree   = parser.parse()
    except SyntaxError as e:
        return jsonify({'ok': False, 'errors': [str(e)]})

    return jsonify({'ok': True, 'tree_svg': tree_to_svg(tree), 'steps': parser.steps})


@app.route('/api/run_visitor', methods=['POST'])
def run_visitor():
    body         = request.get_json()
    src          = body.get('grammar', '')
    phrase       = body.get('phrase', '')
    visitor_code = body.get('visitor_code', '')

    # 1. Gramática
    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'error_kind': 'grammar', 'errors': get_parse_errors()})

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table  = build_parse_table(grammar, first, follow)
    patterns = dict(grammar.get_token_patterns())
    for t in grammar.get_terminals():
        if t.startswith(("'", '"')):
            inner = t[1:-1]
            if inner not in patterns.values():
                patterns[inner] = re.escape(inner)

    # 2. Frase
    try:
        parser = TableParser(grammar, table, phrase, patterns)
        tree   = parser.parse()
    except SyntaxError as e:
        return jsonify({
            'ok': False, 'error_kind': 'phrase',
            'errors': [f'Erro na frase de input: {e}'],
        })

    # 3. Compilar o visitor (capta SyntaxError com lineno exato)
    try:
        compiled = compile(visitor_code, '<visitor>', 'exec')
    except SyntaxError as e:
        line_no = e.lineno or 0
        line_txt = ''
        if line_no > 0:
            lines = visitor_code.splitlines()
            if 0 < line_no <= len(lines):
                line_txt = lines[line_no - 1]
        return jsonify({
            'ok': False, 'error_kind': 'compile',
            'errors': [
                f'Erro de sintaxe no visitor (linha {line_no}): {e.msg}',
                f'    {line_txt}' if line_txt else '',
            ],
            'line': line_no,
        })

    # 4. Executar a definição
    ns = {}
    try:
        exec(compiled, ns)
    except Exception as e:
        return jsonify({
            'ok': False, 'error_kind': 'define',
            'errors': [f'Erro ao definir o visitor: {type(e).__name__}: {e}'],
        })

    CodeGen = ns.get('CodeGen')
    if CodeGen is None:
        return jsonify({
            'ok': False, 'error_kind': 'missing_class',
            'errors': [
                'A classe CodeGen não foi encontrada.',
                'Confirma que o teu código define `class CodeGen(Visitor):`.',
            ],
        })

    # 5. Correr o visitor (filtra traceback para mostrar só o user code)
    try:
        visitor = CodeGen()
        result  = visitor.visit(tree)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        user_frames = [f for f in tb if f.filename == '<visitor>']

        msgs = [f'{type(e).__name__}: {e}']
        if user_frames:
            for f in user_frames:
                line_txt = ''
                lines = visitor_code.splitlines()
                if 0 < f.lineno <= len(lines):
                    line_txt = lines[f.lineno - 1].strip()
                msgs.append(f'  em {f.name}() — linha {f.lineno}')
                if line_txt:
                    msgs.append(f'    > {line_txt}')
        else:
            msgs.append('  (erro fora do código do utilizador)')

        return jsonify({
            'ok': False, 'error_kind': 'runtime',
            'errors': msgs,
            'line': user_frames[-1].lineno if user_frames else None,
        })

    return jsonify({
        'ok':       True,
        'output':   str(result),
        'tree_svg': tree_to_svg(tree),
    })


@app.route('/api/download/<ptype>', methods=['POST'])
def download(ptype):
    src = request.get_json().get('grammar', '')
    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()}), 400

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)

    if ptype == 'rd':
        code, name = generate_rd_parser(grammar, first, follow), 'rd.py'
    elif ptype == 'td':
        code, name = generate_table_parser(grammar, first, follow), 'td.py'
    elif ptype == 'visitor':
        code, name = generate_visitor(grammar), 'visitor.py'
    else:
        return jsonify({'ok': False, 'errors': ['Tipo inválido']}), 400

    buf = io.BytesIO(code.encode())
    buf.seek(0)
    return send_file(buf, mimetype='text/plain', as_attachment=True, download_name=name)


def is_epsilon(seq):
    return not seq.symbols or (len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon())


def compute_lookahead(grammar, first, follow):
    nts = grammar.get_nonterminals()
    result = []
    for rule in grammar.get_rules():
        nt = rule.get_head_name()
        for seq in rule.altlist.sequences:
            sf = first_of_seq(seq.symbols, first, nts)
            nullable = 'ε' in sf
            la = (sf - {'ε'}) | (follow.get(nt, set()) if nullable else set())
            prod_str = 'ε' if is_epsilon(seq) else ' '.join(s.get_value() for s in seq.symbols)
            result.append({'nt': nt, 'production': f'{nt} → {prod_str}',
                           'lookahead': sorted(la), 'nullable': nullable})
    return result


def ser_conflicts(conflicts):
    return [{'type': c['type'], 'nonterminal': c['nonterminal'], 'message': c.get('message', '')} for c in conflicts]


def ser_suggestions(suggestions):
    return [{'nonterminal': s['nonterminal'], 'technique': s['technique'],
             'aplicavel': s.get('aplicavel', True), 'message': s.get('message', ''),
             'new_rules': s['new_rules']} for s in suggestions]


def ser_table(table, grammar):
    nts       = sorted(grammar.get_nonterminals())
    terminals = sorted({t for (_, t) in table})
    rows = []
    for nt in nts:
        cells = {}
        for t in terminals:
            seqs = table.get((nt, t), [])
            if not seqs:
                continue
            seq = seqs[0]
            rhs = 'ε' if is_epsilon(seq) else ' '.join(s.get_value() for s in seq.symbols)
            cells[t] = f'{nt} → {rhs}' + (' ⚠' if len(seqs) > 1 else '')
        rows.append({'nt': nt, 'cells': cells})
    return {'terminals': terminals, 'rows': rows}


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))

def _btn_style():
    """Estilo CSS inline partilhado pelos botões de controlo da árvore."""
    return (
        "width:32px;height:32px;border-radius:6px;border:1px solid #e2e2dc;"
        "background:#fff;cursor:pointer;font-size:16px;"
        "display:inline-flex;align-items:center;justify-content:center;"
        "font-family:sans-serif;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.08);"
    )


def tree_to_svg(root):
    class Slot:
        def __init__(self, node, depth):
            self.label    = node.label
            self.lexema   = getattr(node, 'lexema', None)
            self.depth    = depth
            self.children = []
            self.x        = 0.0

    def build(node, depth):
        s = Slot(node, depth)
        for c in getattr(node, 'children', []):
            s.children.append(build(c, depth + 1))
        return s

    root_slot = build(root, 0)
    counter = [0]
    def assign_x(s):
        if not s.children:
            s.x = float(counter[0])
            counter[0] += 1
        else:
            for c in s.children:
                assign_x(c)
            s.x = sum(c.x for c in s.children) / len(s.children)
    assign_x(root_slot)
    
    all_slots = []
    def collect(s):
        all_slots.append(s)
        for c in s.children:
            collect(c)

    collect(root_slot)

    if not all_slots:
        return '<p style="color:#888;font-size:13px">Árvore vazia.</p>'

    n_leaves  = counter[0]
    max_depth = max(s.depth for s in all_slots)

    FONT   = 12     # px — fonte dos labels
    FONT_L = 10     # px — fonte dos lexemas
    RY     = 16     # meia-altura do rectângulo do nó
    PAD_X  = 10     # padding horizontal interno
    H_GAP  = 120    # espaçamento horizontal entre folhas
    V_GAP  = 90     # espaçamento vertical entre níveis
    PAD    = 70     # margem exterior do SVG

    W = max(500, int(n_leaves * H_GAP + PAD * 2))
    H = max(200, int((max_depth + 1) * V_GAP + PAD * 2 + 40))

    def cx(s): return PAD + s.x * H_GAP
    def cy(s): return PAD + s.depth * V_GAP

    NT_F  = '#eef2ff'; NT_S  = '#6366f1'; NT_T  = '#3730a3'
    LF_F  = '#f0fdf4'; LF_S  = '#16a34a'; LF_T  = '#15803d'
    LF_V  = '#c2410c'
    EPS_F = '#f8fafc'; EPS_S = '#94a3b8'; EPS_T = '#64748b'
    EDGE  = '#cbd5e1'

    edges = []
    nodes = []
    
    for s in all_slots:
        for c in s.children:
            edges.append(
                f'<line x1="{cx(s):.1f}" y1="{cy(s):.1f}" '
                f'x2="{cx(c):.1f}" y2="{cy(c):.1f}" '
                f'stroke="{EDGE}" stroke-width="1.8"/>'
            )

    for s in all_slots:
        x, y    = cx(s), cy(s)
        is_eps  = s.label == 'ε'
        is_leaf = not s.children
        if is_eps:    fill, stroke, tc = EPS_F, EPS_S, EPS_T
        elif is_leaf: fill, stroke, tc = LF_F, LF_S, LF_T
        else:         fill, stroke, tc = NT_F, NT_S, NT_T

        if is_eps:
            fill, stroke, tc = EPS_F, EPS_S, EPS_T
        elif is_leaf:
            fill, stroke, tc = LF_F, LF_S, LF_T
        else:
            fill, stroke, tc = NT_F, NT_S, NT_T

        char_w = FONT * 0.63
        rx = max(22, len(s.label) * char_w / 2 + PAD_X)

        nodes.append(
            f'<rect x="{x - rx:.1f}" y="{y - RY:.1f}" '
            f'width="{rx * 2:.1f}" height="{RY * 2}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
        )
        nodes.append(
            f'<text x="{x:.1f}" y="{y:.1f}" dy="0.35em" '
            f'text-anchor="middle" font-size="{FONT}" font-weight="600" '
            f'font-family="\'JetBrains Mono\',monospace" fill="{tc}">'
            f'{_esc(s.label)}</text>'
        )

        if is_leaf and s.lexema is not None:
            nodes.append(
                f'<text x="{x:.1f}" y="{y + RY + 14:.1f}" '
                f'text-anchor="middle" font-size="{FONT_L}" '
                f'font-family="\'JetBrains Mono\',monospace" fill="{LF_V}">'
                f'{_esc(s.lexema)}</text>'
            )

        tooltip = s.label + (f' = {s.lexema}' if s.lexema else '')
        nodes.append(f'<title>{_esc(tooltip)}</title>')

    inner_svg = '\n'.join(edges + nodes)

    uid = uuid.uuid4().hex[:8]

    return f"""<div id="tc{uid}" style="position:relative;border:1px solid #e2e2dc;
border-radius:6px;background:#fff;overflow:hidden;width:100%;height:460px;user-select:none;">

  <div style="position:absolute;top:8px;right:8px;z-index:10;display:flex;gap:5px;">
    <button onclick="tz{uid}(1.2)"  title="Zoom in"   style="{_btn_style()}">＋</button>
    <button onclick="tz{uid}(0.83)" title="Zoom out"  style="{_btn_style()}">－</button>
    <button onclick="tr{uid}()"     title="Reset"     style="{_btn_style()}">⌂</button>
    <button onclick="tm{uid}()" id="tb{uid}" title="Maximizar" style="{_btn_style()}">⛶</button>
  </div>

  <svg id="ts{uid}" width="{W}" height="{H}"
       style="display:block;cursor:grab;touch-action:none"
       xmlns="http://www.w3.org/2000/svg">
    <g id="tg{uid}">{inner_svg}</g>
  </svg>
</div>

<script>
(function(){{
  var c=document.getElementById('tc{uid}');
  var s=document.getElementById('ts{uid}');
  var g=document.getElementById('tg{uid}');
  var W={W},H={H},sc=1,tx=0,ty=0,dr=false,lx=0,ly=0,max=false;

  function at(){{ g.setAttribute('transform','translate('+tx+','+ty+') scale('+sc+')'); }}

  function fit(){{
    var cw=c.clientWidth||700, ch=c.clientHeight||460;
    sc=Math.min(cw/W, ch/H, 1)*0.92;
    tx=(cw-W*sc)/2; ty=(ch-H*sc)/2; at();
  }}
  setTimeout(fit,50);

  window.tz{uid}=function(f){{
    var cw=c.clientWidth||700,ch=c.clientHeight||460;
    tx=cw/2-(cw/2-tx)*f; ty=ch/2-(ch/2-ty)*f; sc*=f; at();
  }};
  window.tr{uid}=function(){{ fit(); }};

  s.addEventListener('wheel',function(e){{
    e.preventDefault();
    var f=e.deltaY<0?1.12:0.89;
    var r=s.getBoundingClientRect();
    var mx=e.clientX-r.left,my=e.clientY-r.top;
    tx=mx-(mx-tx)*f; ty=my-(my-ty)*f; sc*=f; at();
  }},{{passive:false}});

  s.addEventListener('mousedown',function(e){{
    if(e.button)return; dr=true; lx=e.clientX; ly=e.clientY; s.style.cursor='grabbing';
  }});
  window.addEventListener('mousemove',function(e){{
    if(!dr)return; tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; at();
  }});
  window.addEventListener('mouseup',function(){{ dr=false; s.style.cursor='grab'; }});

  var t1x=0,t1y=0,tpd=0;
  s.addEventListener('touchstart',function(e){{
    if(e.touches.length===1){{ t1x=e.touches[0].clientX; t1y=e.touches[0].clientY; }}
    else if(e.touches.length===2)
      tpd=Math.hypot(e.touches[1].clientX-e.touches[0].clientX,
                     e.touches[1].clientY-e.touches[0].clientY);
  }},{{passive:true}});
  s.addEventListener('touchmove',function(e){{
    e.preventDefault();
    if(e.touches.length===1){{
      tx+=e.touches[0].clientX-t1x; ty+=e.touches[0].clientY-t1y;
      t1x=e.touches[0].clientX; t1y=e.touches[0].clientY; at();
    }} else if(e.touches.length===2){{
      var pd=Math.hypot(e.touches[1].clientX-e.touches[0].clientX,
                        e.touches[1].clientY-e.touches[0].clientY);
      var f=pd/tpd; tpd=pd;
      var r=s.getBoundingClientRect();
      var mx=(e.touches[0].clientX+e.touches[1].clientX)/2-r.left;
      var my=(e.touches[0].clientY+e.touches[1].clientY)/2-r.top;
      tx=mx-(mx-tx)*f; ty=my-(my-ty)*f; sc*=f; at();
    }}
  }},{{passive:false}});

  window.tm{uid}=function(){{
    var btn=document.getElementById('tb{uid}');
    if(!max){{
      c.style.cssText+='position:fixed!important;top:10px!important;left:10px!important;'
        +'right:10px!important;bottom:10px!important;width:auto!important;'
        +'height:auto!important;z-index:9999!important;'
        +'box-shadow:0 8px 40px rgba(0,0,0,.3)!important;';
      btn.textContent='✕'; btn.title='Minimizar'; max=true;
    }} else {{
      c.style.position='relative';
      c.style.top=c.style.left=c.style.right=c.style.bottom='';
      c.style.width='100%'; c.style.height='460px';
      c.style.zIndex=''; c.style.boxShadow='';
      btn.textContent='⛶'; btn.title='Maximizar'; max=false;
    }}
    setTimeout(fit,30);
  }};
}})();
</script>"""


if __name__ == '__main__':
    app.run(debug=True)