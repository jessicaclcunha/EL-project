"""
gp_interpreter.py — Interpreta frases usando os parsers gerados.

parse_with_rd() usa o código produzido por generate_rd_parser(),
executado num namespace isolado. A assinatura pública é idêntica
à anterior para não quebrar app.py.
"""

from gp_parser_rd import generate_rd_parser


def steps_from_tree(tree, steps=None, counter=None):
    """Percorre a árvore gerada e reconstrói a lista de passos para a UI."""
    if steps is None:
        steps = []
    if counter is None:
        counter = [0]

    if tree.lexema is not None:
        counter[0] += 1
        steps.append({
            'step':   counter[0],
            'stack':  [],
            'input':  tree.lexema,
            'action': f'avança: {tree.label} = {tree.lexema!r}',
        })
    elif tree.label == 'ε':
        counter[0] += 1
        steps.append({
            'step':   counter[0],
            'stack':  [],
            'input':  'ε',
            'action': 'ε (produção vazia)',
        })
    else:
        children_labels = ' '.join(
            c.label for c in tree.children
        )
        counter[0] += 1
        steps.append({
            'step':   counter[0],
            'stack':  [],
            'input':  '',
            'action': f'produção: {tree.label} → {children_labels}',
        })
        for child in tree.children:
            steps_from_tree(child, steps, counter)
    return steps


def parse_with_rd(grammar, first, follow, phrase: str, patterns: dict):
    rd_code = generate_rd_parser(grammar, first, follow)

    # Executar o código gerado num namespace isolado
    ns = {}
    exec(compile(rd_code, '<rd_parser>', 'exec'), ns)

    # Tokenizar e parsear com as classes geradas
    lex    = ns['Lexer'](phrase)
    parser = ns['Parser'](lex.tokens)
    tree   = parser.parse()

    # Reconstruir steps a partir da árvore para a UI
    steps = steps_from_tree(tree)
    steps.append({
        'step':   len(steps) + 1,
        'stack':  [],
        'input':  '$',
        'action': 'ACEITE',
    })
    return tree, steps