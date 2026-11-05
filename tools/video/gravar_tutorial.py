"""Grava o vídeo tutorial do Clima Londrina (Playwright), com tempos ajustados à narração.
Uso: gravar_tutorial.py URL_BASE PASTA_SAIDA [duracoes.json] [libs_locais]
Gera PASTA_SAIDA/*.webm e PASTA_SAIDA/marcas.json (instante de início de cada fala, em segundos desde o início da gravação)."""
import sys, os, base64, glob, json, time
from playwright.sync_api import sync_playwright
BASE, OUT = sys.argv[1], sys.argv[2]
DUR = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else {}
LIBS = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720
CSS = """
#tut-cap{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;max-width:880px;background:rgba(19,61,48,.9);color:#fff;
 font:600 21px/1.35 'Segoe UI',Arial,sans-serif;padding:14px 22px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.35);text-align:center;transition:opacity .35s}
#tut-cap small{display:block;font-weight:400;font-size:15px;opacity:.85;margin-top:4px}
#tut-step{position:fixed;top:14px;right:16px;z-index:99999;background:#559a35;color:#fff;font:700 14px Arial;padding:6px 12px;border-radius:999px}
.tut-foco{outline:4px solid #ffca28 !important;outline-offset:3px;border-radius:8px;transition:outline .2s}
#tut-cursor{position:fixed;z-index:100000;width:22px;height:22px;border-radius:50%;background:rgba(255,202,40,.85);border:2px solid #fff;pointer-events:none;
 transform:translate(-50%,-50%);transition:left .6s ease,top .6s ease;left:-50px;top:-50px;box-shadow:0 0 0 6px rgba(255,202,40,.25)}
#tut-intro{position:fixed;inset:0;z-index:100001;background:linear-gradient(135deg,#0080c9,#215c4c 70%,#133d30);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Segoe UI',Arial;text-align:center;transition:opacity .8s}
#tut-intro h1{font-size:44px;margin:0 0 10px} #tut-intro p{font-size:22px;margin:4px;opacity:.9}
"""
marcas = {}
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'])
    ctx = b.new_context(viewport={'width': W, 'height': H}, record_video_dir=OUT, record_video_size={'width': W, 'height': H}, locale='pt-BR')
    pg = ctx.new_page(); T0 = time.time()
    if LIBS:
        pg.route('**/mapbox-gl.js', lambda r: r.fulfill(path=LIBS + '/mapbox-gl/dist/mapbox-gl.js', content_type='application/javascript'))
        pg.route('**/mapbox-gl.css', lambda r: r.fulfill(path=LIBS + '/mapbox-gl/dist/mapbox-gl.css', content_type='text/css'))
        pg.route('**/turf.min.js', lambda r: r.fulfill(path=LIBS + '/@turf/turf/turf.min.js', content_type='application/javascript'))
    pg.goto(BASE + '/index.html')
    pg.add_style_tag(content=CSS)
    pg.evaluate("""() => { const i=document.createElement('div'); i.id='tut-intro'; i.innerHTML='<img src="logo_biosimos.png" style="height:110px;margin-bottom:18px;background:#fff;border-radius:16px;padding:10px"><h1>Clima Londrina</h1><p>Como usar a central de inteligência climática</p><p style="font-size:17px;margin-top:22px">Instituto Biosimos</p>'; document.body.appendChild(i);
        const c=document.createElement('div'); c.id='tut-cap'; c.style.opacity=0; document.body.appendChild(c);
        const s=document.createElement('div'); s.id='tut-step'; s.style.display='none'; document.body.appendChild(s);
        const k=document.createElement('div'); k.id='tut-cursor'; document.body.appendChild(k); }""")
    pg.wait_for_timeout(2500)
    def fala(chave, minimo=3.0):
        """marca o início da fala e devolve um 'relógio' para esperar o fim dela"""
        marcas[chave] = round(time.time() - T0, 2)
        fim = time.time() + max(DUR.get(chave, minimo) + 0.6, minimo)
        return lambda extra=0: pg.wait_for_timeout(max(0, int((fim + extra - time.time()) * 1000)))
    def cap(txt, sub='', passo=''):
        pg.evaluate("([t,s,p])=>{const c=document.getElementById('tut-cap'); c.style.opacity=0; setTimeout(()=>{c.innerHTML=t+(s?'<small>'+s+'</small>':''); c.style.opacity=1},300);"
                    "const e=document.getElementById('tut-step'); e.style.display=p?'block':'none'; e.textContent=p;}", [txt, sub, passo])
    def foco(sel, on=True):
        pg.evaluate("([s,o])=>{document.querySelectorAll('.tut-foco').forEach(e=>e.classList.remove('tut-foco')); const e=document.querySelector(s); if(e&&o){e.classList.add('tut-foco'); e.scrollIntoView({block:'center',behavior:'smooth'});}}", [sel, on])
    def cursor_em(xy):
        pg.evaluate("([x,y])=>{const k=document.getElementById('tut-cursor'); k.style.left=x+'px'; k.style.top=y+'px'}", xy); pg.wait_for_timeout(700)
    def clicar(sel):
        el = pg.locator(sel).first; el.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        bb = el.bounding_box(); cursor_em([bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2]); el.click()
    def tela_mapa(lon, lat):
        return pg.evaluate("([a,b])=>{const p=map.project([a,b]); const r=document.getElementById('map').getBoundingClientRect(); return [p.x+r.x,p.y+r.y]}", [lon, lat])
    def camada(i, on=True):
        ativa = pg.evaluate("i=>opcionaisAtivas.has(i)", i)
        if ativa != on: clicar(f'.camada-row[data-id="{i}"]'); pg.wait_for_timeout(600)
    def popups_fora(): pg.evaluate("()=>document.querySelectorAll('.mapboxgl-popup').forEach(p=>p.remove())")
    N = '13'
    esp = fala('intro', 8); esp()
    pg.evaluate("()=>{const i=document.getElementById('tut-intro'); i.style.opacity=0; setTimeout(()=>i.remove(),900)}"); pg.wait_for_timeout(900)
    esp = fala('geral'); cap('Todo o município de Londrina: cidade e campo', 'Painel com os indicadores à esquerda, mapa com satélite recente à direita', f'1 / {N}'); esp()
    foco('.kpis'); esp = fala('resumo'); cap('O clima já mudou em Londrina', '+1,1 °C na média · dias ≥ 32 °C: de 8 para cerca de 40 por ano', f'2 / {N}'); esp()
    foco('#cardClima'); esp = fala('serie'); cap('Mais de 40 anos de dados climáticos', 'Temperatura, calor, noites quentes, chuvas fortes e ventos – a linha tracejada é a tendência', f'3 / {N}')
    pg.wait_for_timeout(3000); pg.evaluate("()=>{const g=document.querySelectorAll('#cardClima svg'); if(g[2]) g[2].scrollIntoView({block:'center',behavior:'smooth'})}"); esp()
    foco('#cardCamadas'); esp = fala('calor'); cap('Ilhas de calor', 'Temperatura da superfície no verão, medida por satélite (Landsat)', f'4 / {N}')
    pg.wait_for_timeout(1500); camada('calor'); pg.evaluate("()=>map.flyTo({center:[-51.165,-23.31],zoom:12.3,duration:2500})"); esp(0.5)
    foco('#cardRanking'); esp = fala('ranking'); cap('Ranking dos bairros', 'Clique no bairro para ver temperatura, diferença para a média e vegetação', f'5 / {N}')
    pg.wait_for_timeout(2000); clicar('#cardRanking .rk'); pg.wait_for_timeout(2600)
    c = pg.evaluate("()=>{const c=map.getCenter(); return [c.lng,c.lat]}"); xy = tela_mapa(*c); cursor_em(xy); pg.mouse.click(*xy); esp(1); popups_fora()
    camada('bairros-calor', False); camada('calor', False)
    foco('#cardCamadas'); esp = fala('vegetacao'); cap('Vegetação e sombra', 'Bairros mais arborizados são os mais frescos', f'6 / {N}')
    camada('vegetacao'); pg.evaluate("()=>map.flyTo({center:[-51.165,-23.31],zoom:12,duration:2000})"); esp(0.5); camada('vegetacao', False)
    esp = fala('alagamento'); cap('Áreas sujeitas a alagamento', 'Terrenos baixos junto aos córregos e a rede de drenagem natural', f'7 / {N}')
    camada('alagamento'); camada('drenagem'); esp(0.5); camada('alagamento', False); camada('drenagem', False)
    clicar('#centerMap'); pg.wait_for_timeout(1500)
    foco('.clima-campo'); esp = fala('campo'); cap('E no campo?', 'Mais dias ≥ 35 °C na safra de verão e balanço hídrico que passou a negativo', f'8 / {N}')
    pg.wait_for_timeout(5000); pg.evaluate("()=>{const g=[...document.querySelectorAll('#cardClima h3')].find(h=>h.textContent.includes('Balanço')); if(g) g.scrollIntoView({block:'start',behavior:'smooth'})}"); esp()
    foco('#cardRural'); esp = fala('rural'); cap('Vulnerabilidade climática das microbacias rurais', 'Relevo, vegetação nativa e várzeas – onde o clima pesa mais', f'9 / {N}')
    pg.wait_for_timeout(2500); clicar('#cardRural .rk'); pg.wait_for_timeout(2500)
    c = pg.evaluate("()=>{const c=map.getCenter(); return [c.lng,c.lat]}"); xy = tela_mapa(*c); cursor_em(xy); pg.mouse.click(*xy); esp(1); popups_fora()
    camada('rural-vulnerab', False); clicar('#centerMap'); pg.wait_for_timeout(1000)
    foco('#cardCamadas'); esp = fala('declividade'); cap('Relevo e uso do solo', 'Declividade (risco de erosão) e cobertura do solo MapBiomas', f'10 / {N}')
    camada('declividade'); pg.wait_for_timeout(int(max(3, DUR.get('declividade', 8) / 2) * 1000)); camada('declividade', False); camada('uso-solo'); esp(0.5); camada('uso-solo', False)
    foco('#cardZarc'); esp = fala('zarc'); cap('Calendário de plantio – ZARC', 'Épocas de plantio com menor risco climático, por cultura e tipo de solo', f'11 / {N}')
    pg.wait_for_timeout(4000); clicar('#cardZarc select[data-k=cult]'); pg.select_option('#cardZarc select[data-k=cult]', 'Milho 2ª Safra'); pg.wait_for_timeout(2500)
    pg.select_option('#cardZarc select[data-k=cult]', 'Trigo'); esp(0.5)
    foco('#cardImpactos'); esp = fala('impactos'); cap('Registre um impacto climático', 'Alagamentos, quedas de árvore, vendavais – os registros conferidos entram no mapa', f'12 / {N}')
    camada('impactos'); clicar('#centerMap'); esp(1)
    foco('x', False)
    esp = fala('fim', 5); cap('Clima Londrina', 'Instituto Biosimos · dados atualizados todos os meses', ''); esp(1.5)
    ctx.close(); b.close()
json.dump(marcas, open(os.path.join(OUT, 'marcas.json'), 'w'), indent=1)
print('ok', glob.glob(OUT + '/*.webm'), marcas)
