"""
Renderização SVG interativa da árvore de derivação.
"""

import uuid


def esc(s: str) -> str:
    return (
        str(s)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def _btn_style() -> str:
    return (
        "width:32px;height:32px;border-radius:6px;border:1px solid #e2e2dc;"
        "background:#fff;cursor:pointer;font-size:16px;"
        "display:inline-flex;align-items:center;justify-content:center;"
        "font-family:sans-serif;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.08);"
    )


def tree_to_svg(root) -> str:
    """Converte um TreeNode (ou objecto com .label / .children / .lexema) em HTML+SVG."""

    class Slot:
        __slots__ = ('label', 'lexema', 'depth', 'children', 'x')

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
    counter   = [0]

    def assign_x(s):
        if not s.children:
            s.x = float(counter[0]); counter[0] += 1
        else:
            for c in s.children:
                assign_x(c)
            s.x = sum(c.x for c in s.children) / len(s.children)

    assign_x(root_slot)

    all_slots: list = []

    def collect(s):
        all_slots.append(s)
        for c in s.children:
            collect(c)

    collect(root_slot)

    if not all_slots:
        return '<p style="color:#888;font-size:13px">Árvore vazia.</p>'

    n_leaves  = counter[0]
    max_depth = max(s.depth for s in all_slots)

    H_GAP, V_GAP, PAD  = 120, 90, 70
    RY, PAD_X, FONT, FONT_L = 16, 10, 12, 10

    W = max(500, n_leaves * H_GAP + PAD * 2)
    H = max(200, (max_depth + 1) * V_GAP + PAD * 2 + 40)

    def cx(s): return PAD + s.x * H_GAP
    def cy(s): return PAD + s.depth * V_GAP

    # Paleta de cores
    NT_F, NT_S, NT_T   = '#eef2ff', '#6366f1', '#3730a3'
    LF_F, LF_S, LF_T  = '#f0fdf4', '#16a34a', '#15803d'
    LF_V               = '#c2410c'
    EPS_F, EPS_S, EPS_T = '#f8fafc', '#94a3b8', '#64748b'
    EDGE               = '#cbd5e1'

    edges, nodes = [], []

    for s in all_slots:
        for c in s.children:
            edges.append(
                f'<line x1="{cx(s):.1f}" y1="{cy(s):.1f}" '
                f'x2="{cx(c):.1f}" y2="{cy(c):.1f}" '
                f'stroke="{EDGE}" stroke-width="1.8"/>'
            )

    for s in all_slots:
        x, y = cx(s), cy(s)
        if s.label == 'ε':
            fill, stroke, tc = EPS_F, EPS_S, EPS_T
        elif not s.children:
            fill, stroke, tc = LF_F, LF_S, LF_T
        else:
            fill, stroke, tc = NT_F, NT_S, NT_T

        rx = max(22, len(s.label) * FONT * 0.63 / 2 + PAD_X)
        nodes.append(
            f'<rect x="{x-rx:.1f}" y="{y-RY:.1f}" width="{rx*2:.1f}" height="{RY*2}"'
            f' rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
        )
        nodes.append(
            f'<text x="{x:.1f}" y="{y:.1f}" dy="0.35em" text-anchor="middle"'
            f' font-size="{FONT}" font-weight="600"'
            f' font-family="\'JetBrains Mono\',monospace" fill="{tc}">'
            f'{esc(s.label)}</text>'
        )
        if not s.children and s.lexema is not None:
            nodes.append(
                f'<text x="{x:.1f}" y="{y+RY+14:.1f}" text-anchor="middle"'
                f' font-size="{FONT_L}" font-family="\'JetBrains Mono\',monospace"'
                f' fill="{LF_V}">{esc(s.lexema)}</text>'
            )
        nodes.append(
            f'<title>{esc(s.label + (f" = {s.lexema}" if s.lexema else ""))}</title>'
        )

    inner = '\n'.join(edges + nodes)
    uid   = uuid.uuid4().hex[:8]

    return f"""<div id="tc{uid}" style="position:relative;border:1px solid #e2e2dc;
border-radius:6px;background:#fff;overflow:hidden;width:100%;height:460px;user-select:none;">
  <div style="position:absolute;top:8px;right:8px;z-index:10;display:flex;gap:5px;">
    <button onclick="tz{uid}(1.2)"  title="Zoom in"   style="{_btn_style()}">＋</button>
    <button onclick="tz{uid}(0.83)" title="Zoom out"  style="{_btn_style()}">－</button>
    <button onclick="tr{uid}()"     title="Reset"     style="{_btn_style()}">⌂</button>
    <button onclick="tm{uid}()" id="tb{uid}" title="Maximizar" style="{_btn_style()}">⛶</button>
  </div>
  <svg id="ts{uid}" width="{W}" height="{H}"
       style="display:block;cursor:grab;touch-action:none" xmlns="http://www.w3.org/2000/svg">
    <g id="tg{uid}">{inner}</g>
  </svg>
</div>
<script>
(function(){{
  var c=document.getElementById('tc{uid}');
  var s=document.getElementById('ts{uid}');
  var g=document.getElementById('tg{uid}');
  var W={W},H={H},sc=1,tx=0,ty=0,dr=false,lx=0,ly=0,max=false;
  function at(){{g.setAttribute('transform','translate('+tx+','+ty+') scale('+sc+')');}}
  function fit(){{
    var cw=c.clientWidth||700,ch=c.clientHeight||460;
    sc=Math.min(cw/W,ch/H,1)*0.92; tx=(cw-W*sc)/2; ty=(ch-H*sc)/2; at();
  }}
  setTimeout(fit,50);
  window.tz{uid}=function(f){{
    var cw=c.clientWidth||700,ch=c.clientHeight||460;
    tx=cw/2-(cw/2-tx)*f; ty=ch/2-(ch/2-ty)*f; sc*=f; at();
  }};
  window.tr{uid}=function(){{fit();}};
  s.addEventListener('wheel',function(e){{
    e.preventDefault();
    var f=e.deltaY<0?1.12:0.89,r=s.getBoundingClientRect();
    var mx=e.clientX-r.left,my=e.clientY-r.top;
    tx=mx-(mx-tx)*f; ty=my-(my-ty)*f; sc*=f; at();
  }},{{passive:false}});
  s.addEventListener('mousedown',function(e){{
    if(e.button)return; dr=true; lx=e.clientX; ly=e.clientY; s.style.cursor='grabbing';
  }});
  window.addEventListener('mousemove',function(e){{
    if(!dr)return; tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; at();
  }});
  window.addEventListener('mouseup',function(){{dr=false;s.style.cursor='grab';}});
  var t1x=0,t1y=0,tpd=0;
  s.addEventListener('touchstart',function(e){{
    if(e.touches.length===1){{t1x=e.touches[0].clientX;t1y=e.touches[0].clientY;}}
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