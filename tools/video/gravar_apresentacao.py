"""Grava o vídeo de apresentação do Clima Londrina (Playwright), com vinhetas animadas e tempos ajustados à narração.
Uso: gravar_apresentacao.py URL_BASE PASTA_SAIDA [duracoes.json] [libs_locais] [--quadros PASTA]
Gera PASTA_SAIDA/*.webm e PASTA_SAIDA/marcas.json (início de cada fala, em segundos desde o início da gravação).
Com --quadros, salva capturas de tela nos momentos principais (para conferência)."""
import sys, os, glob, json, time
from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:]]
QUADROS = None
if '--quadros' in args:
    i = args.index('--quadros'); QUADROS = args[i + 1]; del args[i:i + 2]; os.makedirs(QUADROS, exist_ok=True)
BASE, OUT = args[0], args[1]
DUR = json.load(open(args[2])) if len(args) > 2 and os.path.exists(args[2]) else {}
LIBS = args[3] if len(args) > 3 else None
AQUI = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720
CAPS = ['mudou', 'calor', 'verde', 'vento', 'agua', 'ar', 'campo', 'participa', 'oportunidades']
marcas = {}

with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'])
    ctx = b.new_context(viewport={'width': W, 'height': H}, record_video_dir=OUT, record_video_size={'width': W, 'height': H}, locale='pt-BR')
    pg = ctx.new_page()
    if LIBS:
        pg.route('**/mapbox-gl.js', lambda r: r.fulfill(path=LIBS + '/mapbox-gl/dist/mapbox-gl.js', content_type='application/javascript'))
        pg.route('**/mapbox-gl.css', lambda r: r.fulfill(path=LIBS + '/mapbox-gl/dist/mapbox-gl.css', content_type='text/css'))
        pg.route('**/turf.min.js', lambda r: r.fulfill(path=LIBS + '/@turf/turf/turf.min.js', content_type='application/javascript'))
    pg.goto(BASE + '/index.html')
    pg.wait_for_function("() => typeof map !== 'undefined' && map.loaded() && typeof dadosGerais !== 'undefined' && dadosGerais && document.querySelector('.camada-row[data-id=\"calor\"]')", timeout=60000)
    pg.add_script_tag(path=os.path.join(AQUI, 'apresentacao_overlay.js'))
    pg.evaluate("() => { document.body.classList.add('v-cine'); map.resize(); V.intro(); }")
    pg.evaluate("""async () => {
        const g = await (await fetch('data/calor/bairros_calor.geojson')).json();
        window.V_BAIRRO = n => { const f = g.features.find(f => f.properties.nome === n); return f ? turf.centerOfMass(f).geometry.coordinates : [-51.165, -23.31]; };
        map.jumpTo({ center: [-51.17, -23.33], zoom: 9.3, pitch: 0, bearing: 0 });
    }""")
    pg.wait_for_timeout(2500)
    T0 = time.time()
    nq = [0]

    def quadro(nome):
        if QUADROS: nq[0] += 1; pg.screenshot(path=f'{QUADROS}/{nq[0]:02d}_{nome}.png')

    def fala(chave, minimo=3.0):
        """marca o início da fala; devolve (esperar_fim, duração)"""
        marcas[chave] = round(time.time() - T0, 2)
        d = max(DUR.get(chave, minimo), minimo); fim = time.time() + d + 0.5
        if chave in CAPS: pg.evaluate("i => V.progresso(i, 9)", CAPS.index(chave))
        return (lambda extra=0: pg.wait_for_timeout(max(0, int((fim + extra - time.time()) * 1000)))), d

    def ate(t0, seg):
        """espera até t0 + seg segundos"""
        pg.wait_for_timeout(max(0, int((t0 + seg - time.time()) * 1000)))

    js = lambda s, a=None: pg.evaluate(s, a) if a is not None else pg.evaluate(s)
    def camada(i, on=True):
        js("([i,on]) => { if (opcionaisAtivas.has(i) !== on) document.querySelector(`.camada-row[data-id=\"${i}\"]`)?.click(); }", [i, on])
    def voar(c, z, pitch=0, bearing=0, dur=4000):
        js("([c,z,p,b,d]) => map.flyTo({ center: c, zoom: z, pitch: p, bearing: b, duration: d, essential: true })", [c, z, pitch, bearing, dur])
    def girar(graus, dur):
        js("([g,d]) => map.easeTo({ bearing: map.getBearing() + g, duration: d, easing: t => t })", [graus, dur])
    def painel(on, card=None):
        js("([on,card]) => { document.body.classList.toggle('v-painel', on); map.resize(); if (card) { const e = document.querySelector(card); if (e) { const sb = document.getElementById('sidebar'); sb.scrollTop = e.offsetTop - sb.offsetTop - 8; } } }", [on, card])

    CIDADE = [-51.165, -23.315]

    # ---------- abertura
    esp, d = fala('intro', 8)
    t = time.time(); quadro('intro'); pg.wait_for_timeout(1500)
    voar(CIDADE, 11.6, 50, -20, 7000); ate(t, d * .85)
    js("() => V.sairIntro()"); esp()

    # ---------- o clima já mudou
    esp, d = fala('mudou'); t = time.time()
    js("""() => { V._st = [{ v: 1.1, casas: 1, pre: '+', suf: ' °C', de: null }, { v: 40, de: null, pre: '8 → ' }, { v: 8.6, casas: 1, suf: ' °C' }];
        V.stats([{ rot: 'na temperatura média<br>desde os anos 1980', cor: 'quente' }, { rot: 'dias por ano com<br>máxima acima de 32 °C', pre: '8 → ', cor: 'quente' },
                 { rot: 'de diferença entre o bairro<br>mais quente e o mais fresco', cor: '' }]); }""")
    girar(25, int(d * 1000) + 1500)
    js("() => V.mostrarStat(0)"); ate(t, d * .38); js("() => V.mostrarStat(1)"); ate(t, d * .72); js("() => V.mostrarStat(2)"); ate(t, d * .78); quadro('numeros')
    esp(); js("() => V.sairStats()")

    # ---------- calor
    camada('calor')
    esp, d = fala('calor'); t = time.time()
    js("() => V.capitulo('01 · CALOR', 'Onde a cidade esquenta', 'Temperatura da superfície no verão, medida por satélite')")
    voar([-51.162, -23.312], 12.6, 55, 15, 6000); ate(t, d * .7); quadro('calor'); esp()

    esp, d = fala('bairros'); t = time.time()
    camada('bairros-calor')
    js("() => V.capitulo('01 · CALOR', '8,6 °C de diferença entre bairros', 'Ranking dos 66 bairros pela temperatura da superfície')")
    c1 = js("() => V_BAIRRO('Vila Casoni')"); c2 = js("() => V_BAIRRO('São Miguel')")
    voar(c1, 14.2, 50, 30, 3500); pg.wait_for_timeout(3000)
    js("(c) => V.alvo(c, 'Vila Casoni · entre os mais quentes', '41,8 °C')", c1); ate(t, d * .5); quadro('casoni')
    voar(c2, 14.0, 50, -10, 3500); pg.wait_for_timeout(3000)
    js("(c) => V.alvo(c, 'São Miguel · entre os mais frescos', '33,2 °C')", c2); esp(0.6); quadro('saomiguel')
    js("() => V.limparAlvos()")

    # ---------- verde
    camada('bairros-calor', False); camada('calor', False); camada('vegetacao')
    esp, d = fala('verde'); t = time.time()
    js("() => V.capitulo('02 · VERDE', 'O verde refresca a cidade', 'Cobertura vegetal medida por satélite (NDVI)')")
    voar([-51.165, -23.31], 12.3, 40, 0, 5000)
    js("() => { V.chips([{ v: '−4 °C', rot: 'nos bairros mais arborizados' }, { v: '+4 °C', rot: 'onde falta árvore' }]); }")
    ate(t, d * .35); js("() => V.mostrarChip(0)"); ate(t, d * .55); js("() => V.mostrarChip(1)"); quadro('verde'); esp(); js("() => V.sairChips()")

    # ---------- vento
    camada('vegetacao', False); camada('vento-ventilacao'); camada('vento-canais'); camada('vento-barreiras')
    esp, d = fala('vento'); t = time.time()
    js("() => V.capitulo('03 · VENTO', 'Por onde a cidade respira', 'Canais de ventilação e áreas de ar parado (modelo indicativo)')")
    voar([-51.16, -23.31], 12.0, 0, 0, 3000); pg.wait_for_timeout(3300)
    js("async () => { await ligarAnimacaoVento(true, dadosGerais.painel_vento); ventoAnim.dir = 90; ventoAnim.kmh = 16; }")
    js("() => V.chips([{ v: '15', rot: 'entradas de ar fresco' }, { v: '3', rot: 'grandes canais de ventilação' }, { v: '12', rot: 'áreas de ar parado' }])")
    ate(t, d * .45); js("() => V.mostrarChip(0)"); ate(t, d * .55); js("() => V.mostrarChip(1)"); ate(t, d * .78); js("() => V.mostrarChip(2)"); quadro('vento')
    esp(); js("() => { V.sairChips(); ligarAnimacaoVento(false); }")

    # ---------- água
    for c in ('vento-ventilacao', 'vento-canais', 'vento-barreiras'): camada(c, False)
    camada('alagamento'); camada('drenagem')
    esp, d = fala('agua'); t = time.time()
    js("() => V.capitulo('04 · ÁGUA', 'Onde a chuva forte alaga', 'Áreas baixas junto aos córregos e a rede de drenagem natural')")
    voar([-51.19, -23.305], 13.2, 55, 40, 5500); ate(t, d * .6); quadro('agua'); girar(-25, 5000); esp()

    # ---------- ar
    camada('alagamento', False); camada('drenagem', False); camada('ar-no2'); camada('ar-estacoes')
    painel(True, '#cardAr'); pg.wait_for_timeout(400)
    esp, d = fala('ar'); t = time.time()
    js("() => V.capitulo('05 · AR', 'O ar que respiramos', 'Estações do IAT todos os dias e NO₂ por satélite')")
    voar([-51.16, -23.31], 11.8, 0, 0, 3000); ate(t, d * .6); quadro('ar'); esp()

    # ---------- campo
    camada('ar-no2', False); camada('ar-estacoes', False); painel(False); camada('rural-vulnerab')
    esp, d = fala('campo'); t = time.time()
    js("() => V.capitulo('06 · CAMPO', 'O campo também sente', 'Vulnerabilidade climática das microbacias rurais')")
    voar([-51.17, -23.40], 9.9, 35, 0, 5000)
    js("() => V.chips([{ v: '176', rot: 'microbacias rurais' }, { v: '59', rot: 'com vulnerabilidade alta' }])")
    ate(t, d * .25); js("() => V.mostrarChip(0)"); ate(t, d * .4); js("() => V.mostrarChip(1)"); quadro('campo')
    ate(t, d * .62); js("() => V.sairChips()"); camada('rural-vulnerab', False); painel(True, '#cardZarc')
    js("() => V.capitulo('06 · CAMPO', 'Calendário de plantio – ZARC', 'Épocas de menor risco climático por cultura e solo')"); esp(); quadro('zarc')

    # ---------- participação
    painel(True, '#cardImpactos'); camada('impactos')
    esp, d = fala('participa'); t = time.time()
    js("() => V.capitulo('07 · PARTICIPAÇÃO', 'A população registra os impactos', 'Alagamentos, quedas de árvores e vendavais')")
    voar([-51.165, -23.31], 12.2, 0, 0, 3500); ate(t, d * .6); quadro('participa'); esp()

    # ---------- oportunidades
    camada('impactos', False); painel(False); js("() => V.semCapitulo()")
    camada('calor')
    esp, d = fala('oportunidades'); t = time.time()
    js("""() => V.lista('Oportunidades para o planejamento urbano', 'O que os dados permitem decidir melhor', [
        { ic: '🌳', t: 'Arborização onde faz mais calor', s: 'priorizar os bairros do topo do ranking' },
        { ic: '🌬️', t: 'Proteger canais de ventilação', s: 'fundos de vale e entradas de ar no Plano Diretor' },
        { ic: '🌊', t: 'Parques lineares nas áreas alagáveis', s: 'espaço para a água, não para a ocupação' },
        { ic: '🏙️', t: 'Altura das construções sem bloquear o vento', s: 'parâmetros urbanísticos guiados pelo modelo' },
        { ic: '🌾', t: 'Solo e água nas microbacias frágeis', s: 'conservação onde o risco rural é maior' },
        { ic: '📊', t: 'Monitorar e prestar contas', s: 'dados abertos atualizados todo mês' }])""")
    girar(30, int(d * 1000))
    ate(t, d * .14); js("() => V.mostrarItem(0)")
    for i, fr in enumerate([.27, .45, .62, .80]): ate(t, d * fr); js(f"() => V.mostrarItem({i + 1})")
    ate(t, d * .93); js("() => V.mostrarItem(5)"); quadro('oportunidades'); esp()

    # ---------- ganhos
    js("() => V.sairLista()"); pg.wait_for_timeout(700)
    esp, d = fala('ganhos'); t = time.time()
    js("""() => { V.lista('Ganhos para Londrina', 'Planejamento com evidências', [
        { ic: '🌡️', t: 'Cidade mais fresca e saudável' }, { ic: '🛡️', t: 'Menos perdas com enchentes' },
        { ic: '🎯', t: 'Investimento público guiado por dados' }, { ic: '💰', t: 'Mais força para captar recursos' }], true); }""")
    for i, fr in enumerate([.2, .42, .6, .8]): ate(t, d * fr); js(f"() => V.mostrarItem({i})")
    quadro('ganhos'); esp()

    # ---------- encerramento
    js("() => V.sairLista()"); camada('calor', False)
    esp, d = fala('fim', 6)
    js("() => V.fim()"); pg.wait_for_timeout(2500); quadro('fim'); esp(2.0)
    ctx.close(); b.close()

json.dump(marcas, open(os.path.join(OUT, 'marcas.json'), 'w'), indent=1)
print('ok', glob.glob(OUT + '/*.webm'), marcas)
