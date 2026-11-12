"""Quem é afetado e quanto custa: população exposta ao calor e ao alagamento, prioridade por setor censitário,
expansão urbana 1985–2025 e histórico de desastres de Londrina.

Fontes (todas públicas):
 - IBGE, Censo 2022 – malha e agregados por setor censitário (população e faixas etárias)
 - GHSL / Comissão Europeia (JRC) – GHS-POP 2025 (população em grade de ~100 m) e GHS-BUILT-S 1985/2025 (área construída)
 - Atlas Digital de Desastres no Brasil (MIDR) – registros 1991–2025, valores corrigidos
 - Ipea – Índice de Vulnerabilidade Social (IVS) municipal
 - camadas já calculadas no próprio site (temperatura da superfície e áreas baixas sujeitas a alagamento)

Saídas em data/social/: setores_prioridade.geojson, expansao.png/.json, desastres.json, resumo_social.json
"""
import os, io, re, json, glob, zipfile, urllib.request, csv, math, datetime
import numpy as np, rasterio
from rasterio.features import geometry_mask, rasterize
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds as tr_bounds
from shapely.geometry import shape, mapping
from PIL import Image

COD = '4113700'
OUT = 'data/social'; TMP = '/tmp/social'
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
log = lambda *a: print(datetime.datetime.now().strftime('%H:%M:%S'), *a, flush=True)


def baixar(url, nome=None):
    dest = os.path.join(TMP, nome or url.rsplit('/', 1)[-1])
    if not os.path.exists(dest):
        log('baixando', url)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Instituto Biosimos - Clima Londrina)'})
        with urllib.request.urlopen(req, timeout=900) as r, open(dest + '.part', 'wb') as f:
            while True:
                b = r.read(1 << 20)
                if not b: break
                f.write(b)
        os.rename(dest + '.part', dest)
    return dest


def num(v):
    if v is None: return 0.0
    v = str(v).strip().replace('R$', '').strip()
    if v in ('', 'X', '-', '.', 'NA', 'nan', 'None'): return 0.0
    if ',' in v: v = v.replace('.', '').replace(',', '.')
    try: return float(v)
    except ValueError: return 0.0


mun = shape(json.load(open('data/base/municipio_londrina.geojson'))['features'][0]['geometry']).buffer(0)
pers = [shape(f['geometry']).buffer(0) for f in json.load(open('data/base/perimetros_urbanos.geojson'))['features']]
per = pers[0]
for p in pers[1:]: per = per.union(p)
W, S, E, N = mun.buffer(0.01).bounds

# ---------------------------------------------------------------- 1. setores censitários (Censo 2022)
F = 'https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios'
shp = baixar('https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/UF/PR_setores_CD2022.zip')
import shapefile  # pyshp
zp = zipfile.ZipFile(shp); base = [n[:-4] for n in zp.namelist() if n.lower().endswith('.shp')][0]
sf = shapefile.Reader(shp=io.BytesIO(zp.read(base + '.shp')), dbf=io.BytesIO(zp.read(base + '.dbf')), shx=io.BytesIO(zp.read(base + '.shx')), encoding='utf-8')
campos = [f[0] for f in sf.fields[1:]]
log('campos da malha', campos)
setores = {}
for sr in sf.iterShapeRecords():
    rec = dict(zip(campos, sr.record))
    if str(rec.get('CD_MUN')) != COD: continue
    g = shape(sr.shape.__geo_interface__).buffer(0)
    setores[str(rec['CD_SETOR'])] = {'geom': g, 'sit': str(rec.get('SITUACAO') or rec.get('CD_SIT') or ''), 'bairro': rec.get('NM_BAIRRO') or ''}
log('setores em Londrina', len(setores))
# shapefile do IBGE usa SIRGAS 2000 geográfico (≈ WGS84 para este uso)


def ler_agregado(zip_url, variaveis):
    z = zipfile.ZipFile(baixar(zip_url))
    nome = [n for n in z.namelist() if n.lower().endswith('.csv')][0]
    raw = z.read(nome)
    txt = raw.decode('utf-8-sig') if raw[:3] == b'\xef\xbb\xbf' or b'\xc3' in raw[:200000] else raw.decode('latin1')
    rd = csv.reader(io.StringIO(txt), delimiter=';'); cab = next(rd)
    cab = [c.strip().strip('"') for c in cab]; i_set = cab.index('CD_SETOR')
    idx = {v: cab.index(v) for v in variaveis if v in cab}
    log('agregado', nome, 'variáveis encontradas', list(idx))
    out = {}
    for lin in rd:
        cs = lin[i_set].strip().strip('"')
        if cs.startswith(COD): out[cs] = {v: num(lin[i]) for v, i in idx.items()}
    return out


bas = ler_agregado(f'{F}/Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip', ['V0001', 'V0002'])
dem = ler_agregado(f'{F}/Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip', ['V01031', 'V01040', 'V01041'])
for cs, s in setores.items():
    b, d = bas.get(cs, {}), dem.get(cs, {})
    s['pop'] = b.get('V0001', 0.0)
    s['crian'] = d.get('V01031', 0.0); s['idos'] = d.get('V01040', 0.0) + d.get('V01041', 0.0)
pop_total = sum(s['pop'] for s in setores.values())
log('população (Censo 2022)', int(pop_total))

# ---------------------------------------------------------------- 2. temperatura da superfície e áreas alagáveis (camadas do site)
def ler_png(js):
    m = json.load(open(js)); im = np.array(Image.open(m['imagem']).convert('RGBA'))
    c = m['cantos']; w, n, e, s = c[0][0], c[0][1], c[1][0], c[2][1]
    return m, im, tr_bounds(w, s, e, n, im.shape[1], im.shape[0])


if os.path.exists('data/calor/lst.tif'):
    with rasterio.open('data/calor/lst.tif') as src: lst = src.read(1).astype('float32'); t_lst = src.transform
    lst[lst <= -999] = np.nan
    if np.nanmax(lst) > 200: lst = lst / 10.0
    log('temperatura: GeoTIFF')
else:   # reconstrói a partir da imagem colorida (11 classes entre os percentis 3 e 97)
    m, im, t_lst = ler_png('data/calor/lst.json')
    pal = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']], 'float32')
    d = ((im[..., None, :3].astype('float32') - pal[None, None]) ** 2).sum(-1); k = d.argmin(-1)
    lst = (m['min'] + (np.minimum(k, 9.5) + 0.5) / 10 * (m['max'] - m['min'])).astype('float32')
    lst[im[..., 3] == 0] = np.nan
    log('temperatura: reconstruída da imagem (resolução de ~1,2 °C por classe)')
urb_mask = ~geometry_mask([mapping(per)], lst.shape, t_lst, invert=False)
media_urbana = float(np.nanmean(np.where(urb_mask, lst, np.nan)))
log('média urbana da superfície', round(media_urbana, 2))

mh, imh, t_h = ler_png('data/alagamento/hand.json')
cores_baixas = [(8, 48, 107), (33, 113, 181)]   # até 2 m acima do córrego
alag = np.zeros(imh.shape[:2], bool)
for c in cores_baixas: alag |= (imh[..., 0] == c[0]) & (imh[..., 1] == c[1]) & (imh[..., 2] == c[2]) & (imh[..., 3] > 0)

# ---------------------------------------------------------------- 3. GHSL (população 100 m e área construída)
G = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL'
def ghsl(prod, ano, tile='R12_C13'):
    nome = f'GHS_{prod}_E{ano}_GLOBE_R2023A_4326_3ss'
    z = baixar(f'{G}/GHS_{prod}_GLOBE_R2023A/{nome}/V1-0/tiles/{nome}_V1_0_{tile}.zip')
    zf = zipfile.ZipFile(z); tif = [n for n in zf.namelist() if n.endswith('.tif')][0]
    caminho = os.path.join(TMP, os.path.basename(tif))
    if not os.path.exists(caminho): open(caminho, 'wb').write(zf.read(tif))
    with rasterio.open(caminho) as src:
        win = from_bounds(W, S, E, N, src.transform).round_offsets().round_lengths()
        a = src.read(1, window=win).astype('float32'); t = src.window_transform(win); nd = src.nodata
    if nd is not None: a[a == nd] = 0
    a[a < 0] = 0
    return a, t


popg, t_pop = ghsl('POP', 2025)
log('GHSL POP 2025 na janela', popg.shape, int(popg[~geometry_mask([mapping(mun)], popg.shape, t_pop, invert=False)].sum()))
# áreas alagáveis e temperatura reamostradas para a grade de população (100 m)
alag_g = np.zeros(popg.shape, 'float32')
reproject(alag.astype('float32'), alag_g, src_transform=t_h, src_crs='EPSG:4326', dst_transform=t_pop, dst_crs='EPSG:4326', resampling=Resampling.average)
lst_g = np.full(popg.shape, np.nan, 'float32')
reproject(lst, lst_g, src_transform=t_lst, src_crs='EPSG:4326', dst_transform=t_pop, dst_crs='EPSG:4326', resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)

# ---------------------------------------------------------------- 4. indicadores por setor
feats = []
for cs, s in setores.items():
    g = s['geom']
    mk_l = ~geometry_mask([mapping(g)], lst.shape, t_lst, invert=False)
    t_med = float(np.nanmean(lst[mk_l])) if mk_l.any() and np.isfinite(lst[mk_l]).any() else None
    mk_p = ~geometry_mask([mapping(g)], popg.shape, t_pop, invert=False, all_touched=True)
    pg = popg[mk_p]; ag = alag_g[mk_p]
    frac_pop_alag = float((pg * ag).sum() / pg.sum()) if pg.sum() > 0 else (float(ag.mean()) if ag.size else 0.0)
    area_ha = g.area * (111.32 * 1000) ** 2 * math.cos(math.radians(g.centroid.y)) / 1e4
    s.update(t=t_med, dif=(t_med - media_urbana) if t_med is not None else None, frac_alag=frac_pop_alag,
             dens=s['pop'] / area_ha if area_ha > 0 else 0, sens=(s['crian'] + s['idos']) / s['pop'] if s['pop'] > 0 else 0, area_ha=area_ha)

# prioridade climática (setores urbanos habitados com temperatura medida): percentis de calor, população sensível e densidade
cand = [s for s in setores.values() if s['pop'] >= 50 and s['dif'] is not None and s['geom'].centroid.within(per.buffer(0.005))]
def pct(vals):
    o = np.argsort(np.argsort(vals)); return o / max(1, len(vals) - 1)
if cand:
    pc_t = pct([s['dif'] for s in cand]); pc_s = pct([s['sens'] for s in cand]); pc_d = pct([s['dens'] for s in cand])
    for s, a, b, c in zip(cand, pc_t, pc_s, pc_d):
        s['score'] = 0.5 * a + 0.25 * b + 0.25 * c
    q = np.quantile([s['score'] for s in cand], [0.2, 0.4, 0.6, 0.8])
    for s in cand: s['classe'] = int(np.searchsorted(q, s['score'])) + 1   # 1 (baixa) … 5 (muito alta)
NOMES = {1: 'Baixa', 2: 'Moderada', 3: 'Média', 4: 'Alta', 5: 'Muito alta'}
for cs, s in setores.items():
    if s['pop'] <= 0: continue
    p = {'Setor censitário': cs, 'Bairro (IBGE)': s['bairro'] or '–', 'População (Censo 2022)': int(s['pop']),
         'Crianças até 4 anos': int(s['crian']), 'Pessoas com 60 anos ou mais': int(s['idos']),
         'População sensível ao calor (%)': round(100 * s['sens'], 1), 'Densidade (hab/ha)': round(s['dens'], 1),
         'Moradores em áreas baixas sujeitas a alagamento (estimativa)': int(round(s['pop'] * s['frac_alag']))}
    if s['t'] is not None:
        p['Temperatura média da superfície (°C)'] = round(s['t'], 1); p['Diferença para a média urbana (°C)'] = round(s['dif'], 1)
    if 'classe' in s: p['Prioridade climática'] = NOMES[s['classe']]; p['classe'] = s['classe']
    feats.append({'type': 'Feature', 'properties': p, 'geometry': mapping(s['geom'].simplify(0.00008, preserve_topology=True))})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(f'{OUT}/setores_prioridade.geojson', 'w'), ensure_ascii=False, separators=(',', ':'))
log('setores gravados', len(feats))

calor2 = [s for s in setores.values() if s['dif'] is not None and s['dif'] >= 2]
calor1 = [s for s in setores.values() if s['dif'] is not None and s['dif'] >= 1]
expo = {
    'pop_total': int(pop_total),
    'pop_calor_2': int(sum(s['pop'] for s in calor2)), 'sens_calor_2': int(sum(s['crian'] + s['idos'] for s in calor2)),
    'pop_calor_1': int(sum(s['pop'] for s in calor1)),
    'pop_alagamento': int(round(sum(s['pop'] * s['frac_alag'] for s in setores.values()))),
    'setores_prioridade_muito_alta': sum(1 for s in setores.values() if s.get('classe') == 5),
    'pop_prioridade_muito_alta': int(sum(s['pop'] for s in setores.values() if s.get('classe') == 5)),
    'media_urbana_superficie': round(media_urbana, 1),
}
log('exposição', expo)

# ---------------------------------------------------------------- 5. expansão urbana (GHSL BUILT-S)
constr = {}
for ano in (1985, 2000, 2025):
    try: constr[ano] = ghsl('BUILT_S', ano)
    except Exception as e: log('BUILT_S', ano, 'falhou', e)
expansao = {}
if 1985 in constr and 2025 in constr:
    b85, tb = constr[1985]; b25, _ = constr[2025]
    dentro = ~geometry_mask([mapping(mun)], b85.shape, tb, invert=False)
    for ano, (a, _) in constr.items(): expansao[str(ano)] = round(float(a[dentro].sum()) / 1e6, 1)   # km² construídos
    cel = 8100.0   # área aproximada da célula (m²) – usada só como limiar relativo
    urb85 = b85 / cel >= 0.15; urb25 = b25 / cel >= 0.15
    img = np.zeros(b85.shape + (4,), 'uint8')
    img[urb85 & dentro] = (120, 120, 120, 150)
    if 2000 in constr:
        urb00 = constr[2000][0] / cel >= 0.15
        img[urb00 & ~urb85 & dentro] = (253, 174, 97, 200)
        img[urb25 & ~urb00 & dentro] = (215, 48, 39, 215)
    else:
        img[urb25 & ~urb85 & dentro] = (215, 48, 39, 215)
    Image.fromarray(img, 'RGBA').save(f'{OUT}/expansao.png', optimize=True)
    w_, s_, e_, n_ = rasterio.transform.array_bounds(b85.shape[0], b85.shape[1], tb)
    json.dump({'imagem': f'{OUT}/expansao.png', 'cantos': [[w_, n_], [e_, n_], [e_, s_], [w_, s_]], 'fonte': 'GHSL GHS-BUILT-S R2023A (JRC/Comissão Europeia)', 'km2': expansao},
              open(f'{OUT}/expansao.json', 'w'))
    log('área construída (km²)', expansao)

# ---------------------------------------------------------------- 6. Atlas Digital de Desastres
desastres = []
try:
    lista = urllib.request.urlopen(urllib.request.Request('https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml', headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read().decode('utf-8', 'ignore')
    arq = sorted(set(re.findall(r'/arquivos/[^"]+Consolidado\.csv', lista)))[-1]
    raw = open(baixar('https://atlasdigital.mdr.gov.br' + arq, 'atlas_desastres.csv'), 'rb').read()
    txt = raw.decode('utf-8') if b'\xc3\xa7' in raw[:5000000] else raw.decode('latin1')
    rd = csv.DictReader(io.StringIO(txt), delimiter=';')
    for r in rd:
        if str(r.get('Cod_IBGE_Mun', '')).strip()[:7] != COD and str(r.get('Cod_IBGE_Mun', '')).strip()[:6] != COD[:6]: continue
        desastres.append({
            'data': r.get('Data_Evento') or r.get('Data_Registro'), 'tipo': r.get('descricao_tipologia') or r.get('tipologia'),
            'grupo': r.get('grupo_de_desastre'), 'mortos': num(r.get('DH_MORTOS')), 'feridos': num(r.get('DH_FERIDOS')),
            'desabrigados': num(r.get('DH_DESABRIGADOS')), 'desalojados': num(r.get('DH_DESALOJADOS')),
            'afetados': num(r.get('DH_total_danos_humanos_diretos')) + num(r.get('DH_OUTROS AFETADOS')),
            'casas_danificadas': num(r.get('DM_Uni Habita Danificadas')), 'casas_destruidas': num(r.get('DM_Uni Habita Destruidas')),
            'danos_materiais': num(r.get('DM_total_danos_materiais')), 'prej_publico': num(r.get('PEPL_total_publico')),
            'prej_privado': num(r.get('PEPR_total_privado')), 'prej_agricultura': num(r.get('PEPR_Agricultura (R$)')),
            'prej_pecuaria': num(r.get('PEPR_Pecuária (R$)'))})
    log('desastres em Londrina', len(desastres))
except Exception as e:
    log('Atlas de Desastres falhou', e)
def ano_de(d):
    m = re.search(r'(19|20)\d\d', d or ''); return int(m.group(0)) if m else None
for d in desastres:
    d['ano'] = ano_de(d['data']); d['total_rs'] = d['danos_materiais'] + d['prej_publico'] + d['prej_privado']
desastres.sort(key=lambda d: (d['ano'] or 0, d['data'] or ''))
por_tipo = {}
for d in desastres:
    t = por_tipo.setdefault(d['tipo'] or 'Outro', {'eventos': 0, 'rs': 0.0, 'afetados': 0})
    t['eventos'] += 1; t['rs'] += d['total_rs']; t['afetados'] += d['afetados']
json.dump({'fonte': 'Atlas Digital de Desastres no Brasil (MIDR/S2iD), valores corrigidos pelo IGP-DI para dez/2022',
           'eventos': desastres, 'por_tipo': por_tipo}, open(f'{OUT}/desastres.json', 'w'), ensure_ascii=False, indent=0)

# ---------------------------------------------------------------- 7. IVS municipal (Ipea)
ivs = None
try:
    z = zipfile.ZipFile(baixar('https://ivs.ipea.gov.br/api/cockpit/storage/uploads/databases/basecompletamunicipal.zip'))
    import openpyxl
    for n in z.namelist():
        if not n.lower().endswith(('.xlsx', '.csv')): continue
        if n.lower().endswith('.csv'):
            linhas = list(csv.reader(io.StringIO(z.read(n).decode('latin1')), delimiter=';'))
        else:
            wb = openpyxl.load_workbook(io.BytesIO(z.read(n)), read_only=True, data_only=True)
            linhas = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        cab = [str(c or '').strip().lower() for c in linhas[0]]
        log('IVS arquivo', n, cab[:25])
        ic = next((i for i, c in enumerate(cab) if c in ('ibge', 'cod_ibge', 'codmun', 'cod_mun', 'municipio_codigo', 'codigo_ibge', 'ibge7', 'cod_municipio')), None)
        ii = next((i for i, c in enumerate(cab) if c == 'ivs'), None)
        ia = next((i for i, c in enumerate(cab) if c in ('ano', 'year')), None)
        if ic is None or ii is None: continue
        regs = [l for l in linhas[1:] if str(l[ic]).split('.')[0] in (COD, COD[:6])]
        regs = [l for l in regs if num(l[ii]) > 0]
        if regs:
            regs.sort(key=lambda l: num(l[ia]) if ia is not None else 0)
            ivs = {'valor': round(num(regs[-1][ii]), 3), 'ano': int(num(regs[-1][ia])) if ia is not None else None,
                   'serie': {str(int(num(l[ia]))): round(num(l[ii]), 3) for l in regs} if ia is not None else {}}
            break
    log('IVS', ivs)
except Exception as e:
    log('IVS falhou', e)
def faixa_ivs(v):
    return None if v is None else ('muito baixa' if v < .2 else 'baixa' if v < .3 else 'média' if v < .4 else 'alta' if v < .5 else 'muito alta')
if ivs: ivs['faixa'] = faixa_ivs(ivs['valor'])

anos = [d['ano'] for d in desastres if d['ano']]
resumo = {
    'atualizado': datetime.date.today().isoformat(), 'exposicao': expo, 'area_construida_km2': expansao, 'ivs': ivs,
    'desastres': {'eventos': len(desastres), 'desde': min(anos) if anos else None, 'ate': max(anos) if anos else None,
                  'prejuizo_total_rs': round(sum(d['total_rs'] for d in desastres)), 'prejuizo_agricola_rs': round(sum(d['prej_agricultura'] + d['prej_pecuaria'] for d in desastres)),
                  'afetados': int(sum(d['afetados'] for d in desastres)), 'desalojados_desabrigados': int(sum(d['desalojados'] + d['desabrigados'] for d in desastres)),
                  'casas_danificadas_destruidas': int(sum(d['casas_danificadas'] + d['casas_destruidas'] for d in desastres))},
    'fontes': ['IBGE – Censo Demográfico 2022, agregados por setor censitário', 'GHSL/JRC – GHS-POP 2025 e GHS-BUILT-S (R2023A)',
               'MIDR – Atlas Digital de Desastres no Brasil (1991–2025)', 'Ipea – Índice de Vulnerabilidade Social (IVS)']
}
json.dump(resumo, open(f'{OUT}/resumo_social.json', 'w'), ensure_ascii=False, indent=1)
log('resumo', json.dumps(resumo, ensure_ascii=False)[:1500])
