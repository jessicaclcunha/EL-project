import sys
import io
import os
import traceback

from flask import Flask, render_template, request, jsonify, send_file

sys.path.insert(0, 'src')

from gp_parser      import parse_grammar, get_parse_errors, get_parse_warnings
from gp_analysis    import *
from gp_parser_rd   import generate_rd_parser
from gp_parser_td   import generate_table_parser, TableParser
from gp_visitor     import generate_visitor
from gp_ontology    import generate_ontology
from gp_interpreter import parse_with_rd
from gp_helpers     import *
from gp_db  import visitor_save, visitor_list, visitor_load, visitor_delete
from gp_svg import tree_to_svg

app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/')
def index():
    return render_template('index.html')



@app.route('/api/analyse', methods=['POST'])
def analyse():
    src     = request.get_json().get('grammar', '')
    grammar = parse_grammar(src)
    errors  = get_parse_errors()
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
        'ok':           True,
        'warnings':     warnings,
        'first':        {k: sorted(v) for k, v in first.items()},
        'follow':       {k: sorted(v) for k, v in follow.items()},
        'lookahead':    compute_lookahead_table(grammar, first, follow),
        'conflicts':    ser_conflicts(conflicts),
        'suggestions':  ser_suggestions(suggestions),
        'table':        ser_table(table, grammar),
        'llk':          llk_result,
        'grammar_hash': grammar_hash(src),
    })





@app.route('/api/apply_suggestions', methods=['POST'])
def apply_suggestions():
    body        = request.get_json()
    src         = body.get('grammar', '')
    suggestions = body.get('suggestions', [])

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    replacements = {}
    for s in suggestions:
        for rule_str in s.get('new_rules', []):
            if rule_str.startswith('⚠') or '->' not in rule_str:
                continue
            nt = rule_str.split('->')[0].strip()
            replacements.setdefault(nt, []).append(rule_str)

    if not replacements:
        return jsonify({'ok': False, 'errors': ['Nenhuma sugestão aplicável.']})

    return jsonify({'ok': True, 'grammar': rebuild_grammar(src, replacements)})




@app.route('/api/generate', methods=['POST'])
def generate():
    src     = request.get_json().get('grammar', '')
    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)

    conflicts = check_ll1(grammar, first, follow)
    if conflicts:
        return jsonify({
            'ok':            False,
            'has_conflicts': True,
            'errors': [
                f'A gramática tem {len(conflicts)} conflito(s) LL(1). '
                'Aplica as sugestões antes de gerar os parsers.'
            ],
        })

    return jsonify({
        'ok':      True,
        'rd':      generate_rd_parser(grammar, first, follow),
        'td':      generate_table_parser(grammar, first, follow),
        'visitor': generate_visitor(grammar),
    })




@app.route('/api/parse_phrase', methods=['POST'])
def parse_phrase():
    body        = request.get_json()
    src         = body.get('grammar', '')
    phrase      = body.get('phrase', '')
    parser_type = body.get('parser_type', 'td')

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first    = compute_first(grammar)
    follow   = compute_follow(grammar, first)
    table    = build_parse_table(grammar, first, follow)
    patterns = build_patterns(grammar)

    try:
        if parser_type == 'rd':
            tree, steps = parse_with_rd(grammar, first, follow, phrase, patterns)
        else:
            parser = TableParser(grammar, table, phrase, patterns)
            tree   = parser.parse()
            steps  = parser.steps
    except SyntaxError as e:
        return jsonify({'ok': False, 'errors': [str(e)]})

    return jsonify({
        'ok':          True,
        'tree_svg':    tree_to_svg(tree),
        'steps':       steps,
        'parser_type': parser_type,
    })




@app.route('/api/download/<ptype>', methods=['POST'])
def download(ptype):
    src     = request.get_json().get('grammar', '')
    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()}), 400

    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)

    mapping = {
        'rd':      (generate_rd_parser(grammar, first, follow),    'rd.py'),
        'td':      (generate_table_parser(grammar, first, follow), 'td.py'),
        'visitor': (generate_visitor(grammar),                     'visitor.py'),
    }
    if ptype not in mapping:
        return jsonify({'ok': False, 'errors': ['Tipo inválido']}), 400

    code, name = mapping[ptype]
    buf = io.BytesIO(code.encode())
    buf.seek(0)
    return send_file(buf, mimetype='text/plain', as_attachment=True, download_name=name)




@app.route('/api/ontology', methods=['POST'])
def ontology():
    body    = request.get_json()
    src     = body.get('grammar', '')
    name    = body.get('name', 'GramaticaUtilizador')

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'errors': get_parse_errors()})

    first     = compute_first(grammar)
    follow    = compute_follow(grammar, first)
    conflicts = check_ll1(grammar, first, follow)
    table     = build_parse_table(grammar, first, follow)
    ttl       = generate_ontology(grammar, first, follow, table, conflicts,
                                  grammar_name=name)

    if body.get('download'):
        buf = io.BytesIO(ttl.encode())
        buf.seek(0)
        return send_file(buf, mimetype='text/turtle',
                         as_attachment=True, download_name=f'{name}.ttl')

    return jsonify({'ok': True, 'turtle': ttl, 'triples_estimate': ttl.count('\n')})




@app.route('/api/run_visitor', methods=['POST'])
def run_visitor():
    body         = request.get_json()
    src          = body.get('grammar', '')
    phrase       = body.get('phrase', '')
    visitor_code = body.get('visitor_code', '')

    grammar = parse_grammar(src)
    if grammar is None:
        return jsonify({'ok': False, 'error_kind': 'grammar',
                        'errors': get_parse_errors()})

    first    = compute_first(grammar)
    follow   = compute_follow(grammar, first)
    table    = build_parse_table(grammar, first, follow)
    patterns = build_patterns(grammar)

    try:
        parser = TableParser(grammar, table, phrase, patterns)
        tree   = parser.parse()
    except SyntaxError as e:
        return jsonify({'ok': False, 'error_kind': 'phrase',
                        'errors': [f'Erro na frase de input: {e}']})

    try:
        compiled = compile(visitor_code, '<visitor>', 'exec')
    except SyntaxError as e:
        line_no  = e.lineno or 0
        lines    = visitor_code.splitlines()
        line_txt = lines[line_no - 1] if 0 < line_no <= len(lines) else ''
        return jsonify({
            'ok': False, 'error_kind': 'compile',
            'errors': [
                f'Erro de sintaxe no visitor (linha {line_no}): {e.msg}',
                f'    {line_txt}' if line_txt else '',
            ],
            'line': line_no,
        })

    ns = {}
    try:
        exec(compiled, ns)
    except Exception as e:
        return jsonify({'ok': False, 'error_kind': 'define',
                        'errors': [f'Erro ao definir o visitor: {type(e).__name__}: {e}']})

    CodeGen = ns.get('CodeGen')
    if CodeGen is None:
        return jsonify({
            'ok': False, 'error_kind': 'missing_class',
            'errors': [
                'A classe CodeGen não foi encontrada.',
                'Confirma que o teu código define `class CodeGen(Visitor):`.',
            ],
        })

    try:
        result = CodeGen().visit(tree)
    except Exception as e:
        tb          = traceback.extract_tb(e.__traceback__)
        user_frames = [f for f in tb if f.filename == '<visitor>']
        msgs        = [f'{type(e).__name__}: {e}']
        for f in user_frames:
            lines    = visitor_code.splitlines()
            line_txt = lines[f.lineno - 1].strip() if 0 < f.lineno <= len(lines) else ''
            msgs.append(f'  em {f.name}() — linha {f.lineno}')
            if line_txt:
                msgs.append(f'    > {line_txt}')
        if not user_frames:
            msgs.append('  (erro fora do código do utilizador)')
        return jsonify({
            'ok': False, 'error_kind': 'runtime',
            'errors': msgs,
            'line': user_frames[-1].lineno if user_frames else None,
        })

    return jsonify({'ok': True, 'output': str(result), 'tree_svg': tree_to_svg(tree)})




@app.route('/api/visitor/save', methods=['POST'])
def api_visitor_save():
    body         = request.get_json()
    name         = (body.get('name') or '').strip()
    code         = body.get('code', '')
    ghash        = body.get('grammar_hash', '')

    if not name:
        return jsonify({'ok': False, 'errors': ['Nome em falta.']})
    if not ghash:
        return jsonify({'ok': False, 'errors': ['grammar_hash em falta — analisa a gramática primeiro.']})
    try:
        visitor_save(name, code, ghash)
    except Exception as e:
        return jsonify({'ok': False, 'errors': [f'Erro ao guardar: {e}']})
    return jsonify({'ok': True, 'name': name})


@app.route('/api/visitor/list', methods=['GET'])
def api_visitor_list():
    ghash = request.args.get('grammar_hash', '')
    if not ghash:
        return jsonify({'ok': True, 'visitors': []})
    try:
        names = visitor_list(ghash)
    except Exception as e:
        return jsonify({'ok': False, 'visitors': [], 'errors': [str(e)]})
    return jsonify({'ok': True, 'visitors': names})


@app.route('/api/visitor/load', methods=['POST'])
def api_visitor_load():
    body  = request.get_json()
    name  = (body.get('name') or '').strip()
    ghash = body.get('grammar_hash', '')
    try:
        code = visitor_load(name, ghash)
    except Exception as e:
        return jsonify({'ok': False, 'errors': [str(e)]})
    if code is None:
        return jsonify({'ok': False, 'errors': [f'Visitor "{name}" não encontrado.']})
    return jsonify({'ok': True, 'name': name, 'code': code})


@app.route('/api/visitor/delete', methods=['POST'])
def api_visitor_delete():
    body  = request.get_json()
    name  = (body.get('name') or '').strip()
    ghash = body.get('grammar_hash', '')
    try:
        visitor_delete(name, ghash)
    except Exception as e:
        return jsonify({'ok': False, 'errors': [str(e)]})
    return jsonify({'ok': True})




VISITOR_EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'examples', 'visitors')


@app.route('/api/visitor/examples', methods=['GET'])
def api_visitor_examples():
    """Lista os visitors de exemplo disponíveis na pasta examples/visitors/."""
    if not os.path.isdir(VISITOR_EXAMPLES_DIR):
        return jsonify({'ok': True, 'examples': []})
    result = []
    for fname in sorted(os.listdir(VISITOR_EXAMPLES_DIR)):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(VISITOR_EXAMPLES_DIR, fname)
        with open(path, encoding='utf-8') as f:
            code = f.read()
        label = fname[:-3]
        for line in code.splitlines():
            if line.startswith('# label:'):
                label = line[len('# label:'):].strip()
                break
        result.append({'key': fname[:-3], 'label': label, 'code': code})
    return jsonify({'ok': True, 'examples': result})



if __name__ == '__main__':
    app.run(debug=True)