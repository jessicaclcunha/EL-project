import sys
import io
import re

from flask import Flask, render_template, request, jsonify, send_file

sys.path.insert(0, 'src')

from gp_parser   import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis import *
from gp_parser_rd import generate_rd_parser
from gp_parser_td import generate_table_parser, TableParser

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
    body        = request.get_json()
    src         = body.get('grammar', '')
    suggestions = body.get('suggestions', [])

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    # Construir mapa NT → novas linhas de regra
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
    """
    Reconstrói a gramática substituindo as regras dos NTs afectados pelas sugestões.
    """
    lines = src.splitlines()

    # --- Separar regras de tokens ---
    TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\s*=\s*/")
    RULE_RE  = re.compile(r"^([A-Za-z][A-Za-z0-9_']*)\s*(->|→)")

    rule_lines  = []
    token_lines = []
    in_tokens   = False

    for line in lines:
        stripped = line.strip()
        if not in_tokens and TOKEN_RE.match(stripped):
            in_tokens = True
        if in_tokens:
            token_lines.append(line)
        else:
            rule_lines.append(line)

    # --- Agrupar rule_lines em blocos por NT ---
    blocks = []
    i = 0
    while i < len(rule_lines):
        line     = rule_lines[i]
        stripped = line.strip()
        m = RULE_RE.match(stripped)
        if m:
            nt          = m.group(1)
            block_lines = [line]
            i += 1
            # absorver continuações (linhas com | ou indentadas)
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

    # --- 3Reconstruir blocos de regras ---
    pending = dict(replacements)   # nt → [linhas]
    inserted = set()
    out_rules = []

    for (nt, block_lines) in blocks:
        if nt is not None and nt in pending:
            # Substituir este bloco pelas novas regras
            out_rules.extend(pending[nt])
            inserted.add(nt)
            del pending[nt]

            # Inserir imediatamente os NTs novos introduzidos por este NT
            still_pending = list(pending.keys())
            for new_nt in still_pending:
                if new_nt.startswith(nt):
                    out_rules.extend(pending[new_nt])
                    inserted.add(new_nt)
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
            'ok': False,
            'has_conflicts': True,
            'errors': [
                f'A gramática tem {len(conflicts)} conflito(s) LL(1). '
                f'Aplica as sugestões de correção antes de gerar os parsers.',
            ],
        })

    return jsonify({
        'ok': True,
        'rd': generate_rd_parser(grammar, first, follow),
        'td': generate_table_parser(grammar, first, follow),
    })


@app.route('/api/parse_phrase', methods=['POST'])
def parse_phrase():
    body   = request.get_json()
    src    = body.get('grammar', '')
    phrase = body.get('phrase', '')

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table  = build_parse_table(grammar, first, follow)

    try:
        parser = TableParser(grammar, table, phrase)
        tree   = parser.parse()
    except SyntaxError as e:
        return jsonify({'ok': False, 'errors': [str(e)]})

    return jsonify({
        'ok':      True,
        'tree_svg': tree_to_svg(tree),
        'steps':    parser.steps,
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
    else:
        return jsonify({'ok': False, 'errors': ['Tipo inválido']}), 400

    buf = io.BytesIO(code.encode())
    buf.seek(0)
    return send_file(buf, mimetype='text/plain',
                     as_attachment=True, download_name=name)


def is_epsilon(seq):
    return not seq.symbols or (
        len(seq.symbols) == 1 and seq.symbols[0].get_is_epsilon()
    )


def compute_lookahead(grammar, first, follow):
    nts    = grammar.get_nonterminals()
    result = []
    for rule in grammar.get_rules():
        nt = rule.get_head_name()
        for seq in rule.altlist.sequences:
            sf       = first_of_seq(seq.symbols, first, nts)
            nullable = 'ε' in sf
            la       = (sf - {'ε'}) | (follow.get(nt, set()) if nullable else set())
            prod_str = 'ε' if is_epsilon(seq) else ' '.join(s.get_value() for s in seq.symbols)
            result.append({
                'nt':         nt,
                'production': f'{nt} → {prod_str}',
                'lookahead':  sorted(la),
                'nullable':   nullable,
            })
    return result


def ser_conflicts(conflicts):
    return [
        {'type': c['type'], 'nonterminal': c['nonterminal'],
         'message': c.get('message', '')}
        for c in conflicts
    ]


def ser_suggestions(suggestions):
    return [
        {
            'nonterminal': s['nonterminal'],
            'technique':   s['technique'],
            'aplicavel':   s.get('aplicavel', True),
            'message':     s.get('message', ''),
            'new_rules':   s['new_rules'],
        }
        for s in suggestions
    ]


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



def tree_to_svg(root):
    class Slot:
        def __init__(self, node, depth):
            self.nt     = node.label
            self.lexema = getattr(node, 'lexema', None)
            self.depth  = depth
            self.children = []
            self.x = 0.0

    def build(node, depth):
        s = Slot(node, depth)
        for c in getattr(node, 'children', []):
            s.children.append(build(c, depth + 1))
        return s

    root_slot = build(root, 0)

    counter = [0]
    def assign_x(s):
        if not s.children:
            s.x = counter[0]; counter[0] += 1
        else:
            for c in s.children: assign_x(c)
            s.x = sum(c.x for c in s.children) / len(s.children)
    assign_x(root_slot)

    all_slots = []
    def collect(s):
        all_slots.append(s)
        for c in s.children: collect(c)
    collect(root_slot)

    if not all_slots:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40"></svg>'

    max_depth = max(s.depth for s in all_slots)
    max_x     = max(s.x     for s in all_slots)

    R     = 20
    H_GAP = 68
    V_GAP = 82    # mais espaço vertical para caber o valor abaixo
    PAD   = 44

    W = max(int((max_x + 1) * H_GAP + PAD * 2), 200)
    H = max(int((max_depth + 1) * V_GAP + PAD * 2), 100)

    def cx(s): return PAD + s.x * H_GAP
    def cy(s): return PAD + s.depth * V_GAP

    BG      = '#ffffff'
    EDGE    = '#d1d5db'
    # nó NT
    NT_F    = '#eef2ff'; NT_S = '#6366f1'; NT_T = '#3730a3'
    # nó folha — anel verde, tipo em verde escuro, valor em laranja
    LF_F    = '#f0fdf4'; LF_S = '#16a34a'; LF_T = '#15803d'
    LF_VAL  = '#c2410c'   # cor do valor (lexema)
    # epsilon
    EPS_F   = '#f9fafb'; EPS_S = '#9ca3af'; EPS_T = '#6b7280'

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f"style=\"background:{BG};font-family:'JetBrains Mono',monospace\">"
    ]

    # arestas
    for s in all_slots:
        for c in s.children:
            out.append(
                f'<line x1="{cx(s):.1f}" y1="{cy(s):.1f}" '
                f'x2="{cx(c):.1f}" y2="{cy(c):.1f}" '
                f'stroke="{EDGE}" stroke-width="1.5"/>'
            )

    # nós
    for s in all_slots:
        x, y    = cx(s), cy(s)
        is_eps  = s.nt == 'ε'
        is_leaf = not s.children

        if is_eps:
            fill, stroke, tc = EPS_F, EPS_S, EPS_T
        elif is_leaf:
            fill, stroke, tc = LF_F, LF_S, LF_T
        else:
            fill, stroke, tc = NT_F, NT_S, NT_T

        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )

        # label principal (tipo / NT) — dentro do círculo
        lbl = s.nt if len(s.nt) <= 8 else s.nt[:7] + '…'
        out.append(
            f'<text x="{x:.1f}" y="{y:.1f}" dy="0.35em" '
            f'text-anchor="middle" font-size="9.5" font-weight="500" fill="{tc}">'
            f'{_esc(lbl)}</text>'
        )

        # valor (lexema) — abaixo do círculo, outra cor
        if is_leaf and s.lexema is not None:
            val = s.lexema if len(s.lexema) <= 10 else s.lexema[:9] + '…'
            out.append(
                f'<text x="{x:.1f}" y="{y + R + 10:.1f}" '
                f'text-anchor="middle" font-size="9" fill="{LF_VAL}">'
                f'{_esc(val)}</text>'
            )

        out.append(f'<title>{_esc(s.nt)}{(" = " + s.lexema) if s.lexema else ""}</title>')

    out.append('</svg>')
    return '\n'.join(out)


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


if __name__ == '__main__':
    app.run(debug=True)