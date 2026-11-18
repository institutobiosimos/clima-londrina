"""Vídeo "Simulação dos ventos" do Clima Londrina: partículas de vento em movimento sobre o modelo de ventilação, quadro a quadro.
Uso: simulacao_ventos.py URL_BASE PASTA_SAIDA
Gera PASTA_SAIDA/<trecho>/*.jpg (1920x1080, 30 fps). O workflow monta o mp4 com transições e trilha."""
import sys, os
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1], sys.argv[2]
AQUI = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
GL = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl']
FPS = 30
PRONTO = "() => typeof map !== 'undefined' && map.loaded() && typeof dadosGerais !== 'undefined' && dadosGerais && document.querySelector('.camada-row[data-id=\"vento-ventilacao\"]')"

CSS = """
.demo-marca, .demo-faixa, .demo-badge, #map-legend, .map-legend { display: none !important; }
.mapboxgl-canvas { filter: brightness(.72) saturate(.85); }
#sv-cap { position: fixed; left: 56px; bottom: 70px; z-index: 99995; font-family: 'Segoe UI','Noto Sans',Arial,sans-serif; color: #fff; max-width: 820px; }
#sv-cap h2 { margin: 0 0 8px; font-size: 52px; font-weight: 800; letter-spacing: .3px; text-shadow: 0 3px 14px rgba(0,0,0,.65); }
#sv-cap p { margin: 0; font-size: 26px; line-height: 1.35; background: rgba(8,30,24,.62); border-left: 6px solid #8bc34a; padding: 10px 16px; border-radius: 0 10px 10px 0; display: inline-block; }
#sv-marca { position: fixed; right: 30px; top: 26px; z-index: 99995; display: flex; align-items: center; gap: 12px; background: rgba(10,38,30,.72); padding: 8px 18px 8px 10px; border-radius: 999px; font: 700 20px 'Segoe UI','Noto Sans',Arial,sans-serif; color: #fff; }
#sv-marca img { height: 38px; background: #fff; border-radius: 50%; padding: 3px; }
#sv-fim { position: fixed; inset: 0; z-index: 99996; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px;
  background: radial-gradient(ellipse at center, rgba(8,30,24,.55), rgba(8,30,24,.9)); color: #fff; font-family: 'Segoe UI','Noto Sans',Arial,sans-serif; opacity: 0; }
#sv-fim img { height: 130px; background: #fff; border-radius: 24px; padding: 14px; }
#sv-fim h2 { margin: 0; font-size: 60px; font-weight: 800; } #sv-fim p { margin: 0; font-size: 28px; opacity: .9; }
"""

# partículas mais visíveis: rastro longo e cor clara, por quão bem o ar circula
PASSO = """() => {
window.passoSite = () => {
  const cv = ventoAnim.canvas, ctx = cv.getContext('2d'), dpr = window.devicePixelRatio || 1;
  ctx.globalCompositeOperation = 'destination-in'; ctx.fillStyle = 'rgba(0,0,0,0.955)'; ctx.fillRect(0, 0, cv.width, cv.height);
  ctx.globalCompositeOperation = 'source-over'; ctx.lineCap = 'round';
  const th = (ventoAnim.dir + 180) * Math.PI / 180, ux = Math.sin(th), uy = Math.cos(th), escala = Math.pow(2, 12 - map.getZoom());
  const base = 0.00011 * Math.max(0.5, Math.min(3, ventoAnim.kmh / 12)) * escala, kx = 1 / Math.cos(-23.3 * Math.PI / 180), d = 0.002;
  for (const p of ventoAnim.parts) {
    const v = vGrade(p.lon, p.lat);
    if (v < 0 || p.idade++ > 110) { Object.assign(p, novaParticula()); p.idade = 0; continue; }
    const gx = (vGrade(p.lon + d * kx, p.lat) - vGrade(p.lon - d * kx, p.lat)), gy = (vGrade(p.lon, p.lat + d) - vGrade(p.lon, p.lat - d));
    const lat_ = (-uy * gx + ux * gy) * 0.6, vel = base * (0.2 + 1.2 * v * v);
    const a = map.project([p.lon, p.lat]);
    p.lon += (ux * vel + (-uy) * lat_ * base) * kx; p.lat += uy * vel + ux * lat_ * base;
    const b = map.project([p.lon, p.lat]);
    ctx.strokeStyle = v > 0.6 ? 'rgba(225,248,255,0.95)' : v > 0.35 ? 'rgba(170,215,240,0.75)' : 'rgba(255,170,120,0.6)';
    ctx.lineWidth = (v > 0.6 ? 2.4 : 1.8) * dpr;
    ctx.beginPath(); ctx.moveTo(a.x * dpr, a.y * dpr); ctx.lineTo(b.x * dpr, b.y * dpr); ctx.stroke();
  }
};
}
"""

TRECHOS = [
    # nome, centro, zoom, pitch, bearing, camadas, título, texto, segundos
    ('01_cidade', [-51.165, -23.318], 11.7, 35, -10, ['vento-ventilacao'],
     'Por onde Londrina respira', 'O vento chega do leste e atravessa a cidade. Em azul, onde o ar circula bem; em vermelho, onde ele para.', 11),
    ('02_centro', [-51.172, -23.307], 13.4, 48, -20, ['vento-ventilacao', 'vento-barreiras'],
     'Onde o ar fica parado', 'Atrás das áreas densas e altas do centro, o vento perde força e o calor se acumula.', 10),
    ('03_canal', [-51.163, -23.331], 13.5, 50, 15, ['vento-ventilacao', 'vento-canais'],
     'Canais de ventilação', 'Fundos de vale, lagos e parques funcionam como corredores que levam ar fresco para dentro da cidade.', 10),
    ('04_fim', [-51.165, -23.318], 12.0, 40, -10, ['vento-ventilacao'], '', '', 5),
]

with sync_playwright() as p:
    b = p.chromium.launch(args=GL)
    ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1, locale='pt-BR')
    pg = ctx.new_page()
    pg.goto(f'{BASE}/demo/index.html')
    pg.wait_for_function(PRONTO, timeout=90000)
    pg.add_script_tag(path=os.path.join(AQUI, 'apresentacao_overlay.js'))
    pg.add_style_tag(content=CSS)
    pg.evaluate("() => { document.body.classList.add('v-cine'); map.resize(); }")
    pg.evaluate(PASSO)
    pg.evaluate("""() => {
        const m = document.createElement('div'); m.id = 'sv-marca'; m.innerHTML = '<img src="logo.png" alt=""><span>Clima Londrina · Instituto Biosimos</span>'; document.body.appendChild(m);
        const c = document.createElement('div'); c.id = 'sv-cap'; document.body.appendChild(c);
        const f = document.createElement('div'); f.id = 'sv-fim'; f.innerHTML = '<img src="logo.png" alt=""><h2>Clima Londrina</h2><p>Central de inteligência climática · Instituto Biosimos</p>'; document.body.appendChild(f);
    }""")
    pg.wait_for_timeout(1500)
    ativas = set()
    for nome, centro, zoom, pitch, bearing, camadas, titulo, texto, seg in TRECHOS:
        for c in list(ativas):
            if c not in camadas:
                pg.evaluate("i => document.querySelector(`.camada-row[data-id=\"${i}\"]`)?.click()", c); ativas.discard(c)
        for c in camadas:
            if c not in ativas:
                pg.evaluate("i => document.querySelector(`.camada-row[data-id=\"${i}\"]`)?.click()", c); ativas.add(c)
        pg.evaluate("async () => { if (ventoAnim.ativo) await ligarAnimacaoVento(false); }")
        pg.evaluate("([c,z,p,b]) => map.jumpTo({ center: c, zoom: z, pitch: p, bearing: b })", [centro, zoom, pitch, bearing])
        pg.wait_for_timeout(1000)
        try:
            pg.wait_for_function("() => map.loaded() && map.areTilesLoaded()", timeout=60000)
        except Exception:
            pass
        pg.wait_for_timeout(2500)
        pg.evaluate("""async () => {
            await ligarAnimacaoVento(true, dadosGerais.painel_vento); cancelAnimationFrame(ventoAnim.raf);
            ventoAnim.dir = 90; ventoAnim.kmh = 16;
            ventoAnim.parts = Array.from({ length: 5200 }, novaParticula);
            for (let i = 0; i < 120; i++) passoSite();
        }""")
        pg.evaluate("([t, x]) => { const c = document.getElementById('sv-cap'); c.innerHTML = t ? `<h2>${t}</h2><p>${x}</p>` : ''; }", [titulo, texto])
        d = f'{OUT}/{nome}'; os.makedirs(d, exist_ok=True)
        n = seg * FPS
        for i in range(n):
            if nome == '04_fim':
                pg.evaluate("o => { document.getElementById('sv-fim').style.opacity = o; document.getElementById('sv-marca').style.opacity = 1 - o; }", min(1, i / 30))
            op = max(0, min(1, (i - 10) / 20, (n - 1 - i) / 15))
            pg.evaluate("o => { document.getElementById('sv-cap').style.opacity = o; passoSite(); }", op)
            pg.screenshot(path=f'{d}/{i:04d}.jpg', type='jpeg', quality=93)
        print('trecho', nome, n, 'quadros', flush=True)
    b.close()
