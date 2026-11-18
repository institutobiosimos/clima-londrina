"""Imagens e cenas em alta qualidade da plataforma Clima Londrina, para o site do Instituto Biosimos.
Uso: imagens_site.py URL_BASE PASTA_SAIDA
Gera PASTA_SAIDA/imagens/*.png (fotos em 3200x1800 e celular) e PASTA_SAIDA/cenas/<nome>/*.jpg (quadros 1920x1080 a 30 fps, montados em mp4 pelo workflow)."""
import sys, os
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1], sys.argv[2]
AQUI = os.path.dirname(os.path.abspath(__file__))
IMG, CEN = f'{OUT}/imagens', f'{OUT}/cenas'
os.makedirs(IMG, exist_ok=True); os.makedirs(CEN, exist_ok=True)
GL = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl']
CIDADE = [-51.165, -23.315]
PRONTO = "() => typeof map !== 'undefined' && map.loaded() && typeof dadosGerais !== 'undefined' && dadosGerais && document.querySelector('.camada-row[data-id=\"calor\"]')"


LIMPO = '.demo-marca, .demo-faixa, .demo-badge, #clienteSub, .footnote, #cardTermos, #cardPrograma { display: none !important; }'


def abrir(ctx, pagina='demo/index.html', cine=True):
    # sempre a versão demonstrativa (textos resumidos, sem detalhes de fontes e métodos), sem marca d'água
    pg = ctx.new_page()
    pg.goto(f'{BASE}/{pagina}')
    pg.wait_for_function(PRONTO, timeout=90000)
    pg.add_script_tag(path=os.path.join(AQUI, 'apresentacao_overlay.js'))
    pg.add_style_tag(content=LIMPO)
    if cine:
        pg.evaluate("() => { document.body.classList.add('v-cine'); map.resize(); }")
    pg.wait_for_timeout(1500)
    return pg


def camada(pg, i, on=True):
    pg.evaluate("([i,on]) => { if (opcionaisAtivas.has(i) !== on) document.querySelector(`.camada-row[data-id=\"${i}\"]`)?.click(); }", [i, on])


def ir(pg, c, z, pitch=0, bearing=0):
    pg.evaluate("([c,z,p,b]) => map.jumpTo({ center: c, zoom: z, pitch: p, bearing: b })", [c, z, pitch, bearing])


def esperar_mapa(pg, extra=2500):
    pg.wait_for_timeout(800)
    try:
        pg.wait_for_function("() => map.loaded() && map.areTilesLoaded()", timeout=60000)
    except Exception:
        pass
    pg.wait_for_timeout(extra)


def foto(pg, nome):
    pg.screenshot(path=f'{IMG}/{nome}.png'); print('foto', nome, flush=True)


def vento(pg, on=True, n=None):
    pg.evaluate("async ([on, n]) => { await ligarAnimacaoVento(on, dadosGerais.painel_vento); if (on) { ventoAnim.dir = 90; ventoAnim.kmh = 16; if (n) ventoAnim.parts = ventoAnim.parts.slice(0, n); } }", [on, n])


with sync_playwright() as p:
    b = p.chromium.launch(args=GL)

    # ---------- fotos em alta (1600x900 com densidade 2 = 3200x1800), só o mapa
    ctx = b.new_context(viewport={'width': 1600, 'height': 900}, device_scale_factor=2, locale='pt-BR')
    pg = abrir(ctx)
    camada(pg, 'calor'); ir(pg, CIDADE, 11.7, 0, 0); esperar_mapa(pg); foto(pg, '01_ilhas_de_calor_cidade')
    ir(pg, [-51.16, -23.305], 12.6, 55, -25); esperar_mapa(pg); foto(pg, '02_ilhas_de_calor_3d')
    camada(pg, 'calor', False); camada(pg, 'bairros-calor'); ir(pg, [-51.162, -23.312], 12.4, 30, -10); esperar_mapa(pg); foto(pg, '03_calor_por_bairro')
    camada(pg, 'bairros-calor', False)
    for c in ('vento-ventilacao', 'vento-canais', 'vento-barreiras'): camada(pg, c)
    ir(pg, CIDADE, 12.1, 35, -15); esperar_mapa(pg); foto(pg, '04_ventilacao_canais')
    vento(pg, True, 1600); pg.wait_for_timeout(5000); foto(pg, '05_vento_animado')
    vento(pg, False)
    for c in ('vento-ventilacao', 'vento-canais', 'vento-barreiras'): camada(pg, c, False)
    ctx.close()

    # ---------- telas da plataforma com o painel (como o usuário vê)
    ctx = b.new_context(viewport={'width': 1600, 'height': 900}, device_scale_factor=2, locale='pt-BR')
    pg = abrir(ctx, cine=False)
    pg.evaluate("() => { document.querySelectorAll('.mapboxgl-popup').forEach(e => e.remove()); }")
    camada(pg, 'calor'); ir(pg, CIDADE, 11.9, 0, 0); esperar_mapa(pg)
    pg.evaluate("() => { const e = document.getElementById('cardRanking'); const sb = document.getElementById('sidebar'); if (e && sb) sb.scrollTop = e.offsetTop - sb.offsetTop - 8; }")
    pg.wait_for_timeout(800); foto(pg, '06_plataforma_calor_ranking')
    camada(pg, 'calor', False)
    for c in ('vento-ventilacao', 'vento-canais'): camada(pg, c)
    vento(pg, True, 1400)
    pg.evaluate("() => { const e = document.getElementById('cardVento'); const sb = document.getElementById('sidebar'); if (e && sb) sb.scrollTop = e.offsetTop - sb.offsetTop - 8; }")
    esperar_mapa(pg, 4000); foto(pg, '07_plataforma_ventos')
    vento(pg, False)
    # gráficos do clima (recorte do quadro, fundo branco)
    for card, nome in (('#cardClima', '08_graficos_clima'), ('#cardRanking', '09_ranking_bairros'), ('#cardVento', '10_quadro_ventos')):
        el = pg.query_selector(card)
        if el:
            el.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
            el.screenshot(path=f'{IMG}/{nome}.png'); print('foto', nome, flush=True)
    ctx.close()

    # ---------- celular (versão demonstrativa, como o público vê)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True, locale='pt-BR')
    pg = abrir(ctx, 'demo/index.html', cine=False)
    camada(pg, 'calor'); ir(pg, CIDADE, 11.0, 0, 0)
    pg.evaluate("() => { const t = document.getElementById('panelToggle'); if (t && t.getAttribute('aria-expanded') === 'true') t.click(); }")
    esperar_mapa(pg); foto(pg, '11_celular_calor')
    ctx.close()

    # ---------- cenas em vídeo: quadro a quadro (1920x1080, 30 fps), sem interface; o mp4 é montado pelo ffmpeg
    FPS = 30

    def quadro_pronto(pg):
        pg.evaluate("() => new Promise(r => { if (map.loaded() && map.areTilesLoaded()) return r(); let ok = false; map.once('idle', () => { ok = true; r(); }); setTimeout(() => { if (!ok) r(); }, 8000); })")

    def cena(nome, seg, camera, com_vento=False, camadas=()):
        d = f'{CEN}/{nome}'; os.makedirs(d, exist_ok=True)
        ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1, locale='pt-BR')
        pg = abrir(ctx)
        for c in camadas: camada(pg, c)
        c0 = camera(0); ir(pg, *c0); esperar_mapa(pg, 3000)
        if com_vento:
            vento(pg, True, 2200)
            pg.evaluate("() => { cancelAnimationFrame(ventoAnim.raf); for (let i = 0; i < 90; i++) { passoVento(); cancelAnimationFrame(ventoAnim.raf); } }")
        n = int(seg * FPS)
        for i in range(n):
            t = i / max(1, n - 1)
            if not com_vento:  # mover o mapa apaga o rastro das partículas: no vento a câmera fica parada
                pg.evaluate("([c,z,p,b]) => map.jumpTo({ center: c, zoom: z, pitch: p, bearing: b })", list(camera(t)))
                quadro_pronto(pg)
            if com_vento:
                pg.evaluate("() => { passoVento(); cancelAnimationFrame(ventoAnim.raf); }")
            pg.screenshot(path=f'{d}/{i:04d}.jpg', type='jpeg', quality=92)
        ctx.close(); print('cena', nome, n, 'quadros', flush=True)

    suave = lambda t: t * t * (3 - 2 * t)
    mix = lambda a, b, t: a + (b - a) * t

    def cam_calor(t):
        u = suave(t)
        return ([mix(-51.165, -51.16, u), mix(-23.315, -23.305, u)], mix(11.2, 12.7, u), mix(0, 55, u), mix(0, -35, u))

    def cam_vento(t):
        return (CIDADE, 12.0, 30, -10)

    def cam_bairros(t):
        return ([-51.162, -23.312], 12.3, 45, mix(-40, 20, suave(t)))

    cena('cena_01_voo_ilhas_de_calor', 12, cam_calor, camadas=('calor',))
    cena('cena_02_vento_animado', 12, cam_vento, com_vento=True, camadas=('vento-ventilacao', 'vento-canais', 'vento-barreiras'))
    cena('cena_03_giro_bairros', 12, cam_bairros, camadas=('bairros-calor',))
    b.close()
