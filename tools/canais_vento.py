"""Canais de ventilação (corredores de vento) de Londrina – modelo indicativo.
Combina:
  * direção dos ventos predominantes (rosa dos ventos ERA5 dos últimos 10 anos, data/clima/clima_londrina.json);
  * rugosidade da superfície (z0): cobertura do solo MapBiomas 2023 + altura média das edificações (GHSL GHS-BUILT-H 2018, 100 m);
  * relevo: fundos de vale alinhados ao vento canalizam o ar (Copernicus DEM / HAND de /tmp/terreno, gerados por alagamento_hand.py).
Para cada direção, calcula a rugosidade média "a barlavento" (os ~1,5 km de onde o vento vem) de cada ponto: onde o ar chega
passando por superfícies lisas (vales, parques, lagos, lavouras) o potencial de ventilação é alto; atrás de áreas densas e altas, é baixo.
Saídas em data/vento/: ventilacao.png/json (mapa contínuo), corredores.geojson (principais canais), barreiras.geojson,
direcoes.geojson (setas de direção predominante) e resumo.json."""
import json, os, math, zipfile, io, urllib.request, numpy as np, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import geometry_mask, shapes
from rasterio.transform import from_bounds as tfb
from shapely.geometry import shape, mapping, Point, LineString
from shapely.ops import unary_union
from scipy import ndimage
from PIL import Image
os.makedirs('data/vento', exist_ok=True)

with rasterio.open('/tmp/terreno/dem.tif') as f: dem = f.read(1); tr = f.transform; crs = f.crs; H, W = dem.shape
with rasterio.open('/tmp/terreno/hand.tif') as f: hand = f.read(1)
lat0 = tr.f + tr.e * H / 2
px = abs(tr.a) * 111320 * math.cos(math.radians(lat0)); py = abs(tr.e) * 110540   # tamanho do pixel em metros

# ---------- direções predominantes ----------
rosa = json.load(open('data/clima/clima_londrina.json'))['rosa_ventos']
ANG = {'N': 0, 'NE': 45, 'L': 90, 'SE': 135, 'S': 180, 'SO': 225, 'O': 270, 'NO': 315}
freq = {s: sum(v) for s, v in rosa['percentual'].items()}
top = sorted(freq.items(), key=lambda x: -x[1])[:3]
tot = sum(v for _, v in top); DIRS = [(s, ANG[s], v / tot) for s, v in top]
print('direções', DIRS, flush=True)

# ---------- rugosidade z0 (m) ----------
mb = json.load(open('data/mapbiomas/cobertura_2023.json')); (w0, n0), _, (e0, s0), _ = mb['cantos']
rgb = np.array(Image.open(mb['imagem']).convert('RGBA'))
Z0COR = {(31, 141, 73): 1.0,    # formação florestal
         (81, 151, 153): 0.05,  # campo alagado / várzea
         (194, 123, 160): 0.06, (208, 130, 222): 0.06, (255, 239, 195): 0.08,  # soja, outras lavouras, mosaico
         (237, 222, 142): 0.03,  # pastagem
         (122, 89, 0): 0.9,      # silvicultura
         (212, 39, 30): 0.7,     # área urbanizada (substituída pela altura quando houver)
         (37, 50, 228): 0.0002,  # água
         (219, 77, 79): 0.3}     # outras áreas não vegetadas
z0mb = np.full(rgb.shape[:2], 0.1, 'float32')
for c, v in Z0COR.items(): z0mb[(rgb[..., 0] == c[0]) & (rgb[..., 1] == c[1]) & (rgb[..., 2] == c[2])] = v
urbmb = ((rgb[..., 0] == 212) & (rgb[..., 1] == 39) & (rgb[..., 2] == 30)).astype('float32')
z0 = np.zeros((H, W), 'float32'); urb = np.zeros((H, W), 'float32')
src_tr = tfb(w0, s0, e0, n0, rgb.shape[1], rgb.shape[0])
reproject(z0mb, z0, src_transform=src_tr, src_crs='EPSG:4326', dst_transform=tr, dst_crs=crs, resampling=Resampling.average)
reproject(urbmb, urb, src_transform=src_tr, src_crs='EPSG:4326', dst_transform=tr, dst_crs=crs, resampling=Resampling.average)
z0[z0 <= 0] = 0.1
# altura das edificações (GHSL) – z0 urbano ≈ 0,1 × altura média (regra de Grimmond & Oke)
alt = np.zeros((H, W), 'float32'); tem_alt = False
GHSL = ('https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_H_GLOBE_R2023A/GHS_BUILT_H_AGBH_E2018_GLOBE_R2023A_54009_100/'
        'V1-0/GHS_BUILT_H_AGBH_E2018_GLOBE_R2023A_54009_100_V1_0.zip')
try:
    if not os.path.exists('/tmp/ghsl.zip'):
        urllib.request.urlretrieve(GHSL, '/tmp/ghsl.zip')
    nome = [n for n in zipfile.ZipFile('/tmp/ghsl.zip').namelist() if n.endswith('.tif')][0]
    with rasterio.open(f'/vsizip//tmp/ghsl.zip/{nome}') as src:
        from rasterio.warp import transform_bounds
        from rasterio.windows import from_bounds
        b = transform_bounds(crs, src.crs, tr.c, tr.f + tr.e * H, tr.c + tr.a * W, tr.f)
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, boundless=True, fill_value=0).astype('float32')
        reproject(arr, alt, src_transform=src.window_transform(win), src_crs=src.crs, dst_transform=tr, dst_crs=crs, resampling=Resampling.bilinear)
    tem_alt = alt.max() > 1
    print('GHSL altura: máx', float(alt.max()), 'média urbana', float(alt[urb > 0.5].mean()) if (urb > 0.5).any() else None, flush=True)
except Exception as e:
    print('GHSL indisponível:', e, flush=True)
if tem_alt:
    zurb = np.clip(0.1 * alt, 0.3, 3.0)
    z0 = np.where(urb > 0.3, urb * zurb + (1 - urb) * z0, z0)
lnz = np.log(np.clip(z0, 0.0002, 3.0))

# ---------- rugosidade média a barlavento ----------
FETCH, PASSO = 1500, 60
def barlavento(ang):
    """média ponderada de ln z0 nos FETCH metros de onde o vento vem (pesos maiores perto do ponto)"""
    th = math.radians(ang)  # direção DE ONDE vem o vento
    acc = np.zeros_like(lnz); ws = 0.0
    for d in range(0, FETCH + 1, PASSO):
        # saída[r, c] = ln z0 no ponto d metros a barlavento: coluna + d·sen θ / px, linha − d·cos θ / py
        w = math.exp(-d / 700)
        acc += w * ndimage.shift(lnz, (d * math.cos(th) / py, -d * math.sin(th) / px), order=1, mode='nearest'); ws += w
    return acc / ws

# relevo: vales com encostas paralelas ao vento canalizam o ar
dems = ndimage.gaussian_filter(np.nan_to_num(dem, nan=np.nanmean(dem)), 5)
gy, gx = np.gradient(dems, py, px)
aspecto = np.arctan2(-gx, gy)   # direção para onde a encosta desce (radianos a partir do norte)
vale = np.clip(1 - hand / 12, 0, 1)

lnmin, lnmax = math.log(0.03), math.log(1.5)
V = np.zeros_like(lnz)
for s, ang, w in DIRS:
    rb = barlavento(ang)
    v = np.clip((lnmax - rb) / (lnmax - lnmin), 0, 1)
    alinh = np.abs(np.sin(aspecto - math.radians(ang)))   # 1 = encostas paralelas ao vento
    V += w * np.clip(0.75 * v + 0.25 * vale * alinh, 0, 1)
V = ndimage.gaussian_filter(V, 1.2)

# ---------- recorte: cidade (perímetros urbanos + 1,5 km) ----------
mun = shape(json.load(open('data/base/municipio_londrina.geojson'))['features'][0]['geometry']).buffer(0)
per = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open('data/base/perimetros_urbanos.geojson'))['features']])
sede = max(per.geoms, key=lambda g: g.area) if per.geom_type == 'MultiPolygon' else per
area = sede.buffer(0.015).intersection(mun)
dentro = geometry_mask([mapping(area)], (H, W), tr, invert=True)
dentro_urb = geometry_mask([mapping(sede)], (H, W), tr, invert=True)
vals = V[dentro_urb]
p15, p35, p70 = np.percentile(vals, [15, 35, 70])   # classes relativas à própria cidade
print('percentis', p15, p35, p70, flush=True)

# imagem contínua: vermelho (pouca ventilação) → amarelo → azul (canal de ventilação)
def rampa(x):
    pts = [(0.0, (178, 24, 43)), (0.3, (244, 165, 130)), (0.55, (253, 245, 200)), (0.8, (146, 197, 222)), (1.0, (33, 102, 172))]
    out = np.zeros(x.shape + (3,), 'float32')
    for (a, ca), (b, cb) in zip(pts[:-1], pts[1:]):
        m = (x >= a) & (x <= b); t = ((x - a) / (b - a))[m][:, None]
        out[m] = np.array(ca) * (1 - t) + np.array(cb) * t
    return out.astype('uint8')
q = np.interp(V, [np.percentile(vals, 2), p35, p70, np.percentile(vals, 98)], [0, 0.4, 0.65, 1])
img = np.zeros((H, W, 4), 'uint8'); img[..., :3] = rampa(np.clip(q, 0, 1)); img[..., 3] = np.where(dentro, 175, 0)
Image.fromarray(img, 'RGBA').save('data/vento/ventilacao.png', optimize=True)
w_, s_, e_, n_ = rasterio.transform.array_bounds(H, W, tr)
json.dump({'imagem': 'data/vento/ventilacao.png', 'cantos': [[w_, n_], [e_, n_], [e_, s_], [w_, s_]]}, open('data/vento/ventilacao.json', 'w'))

# ---------- vetorização dos corredores e barreiras ----------
mbs = [(f['properties'].get('nome') or '', shape(f['geometry']).buffer(0)) for f in json.load(open('data/base/microbacias.geojson'))['features']]
def rio_proximo(g):
    melhor = max(((n, m.intersection(g).area) for n, m in mbs if n and m.intersects(g)), key=lambda x: x[1], default=(None, 0))[0]
    return melhor.replace('Microbacia do ', '').replace('Microbacia da ', '') if melhor else None
bairros = [(f['properties'].get('nome') or '', shape(f['geometry']).buffer(0)) for f in json.load(open('data/base/bairros.geojson'))['features']]
def bairros_de(g):
    ov = sorted(((n, b.intersection(g).area) for n, b in bairros if n and b.intersects(g)), key=lambda x: -x[1])
    return [n for n, a in ov if a > 0.00002][:6]
ha = px * py / 1e4
def vetoriza(mask, minimo_ha, tipo):
    mask = ndimage.binary_opening(mask, iterations=1)
    lab, n = ndimage.label(mask)
    tam = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)) * ha
    manter = np.isin(lab, [i + 1 for i, t in enumerate(tam) if t >= minimo_ha])
    feats = []
    for geom, v in shapes(manter.astype('uint8'), mask=manter, transform=tr):
        g = shape(geom).buffer(0).simplify(0.0002)
        if g.is_empty: continue
        a = g.area * (111320 * math.cos(math.radians(lat0))) * 110540 / 1e4
        if a < minimo_ha: continue
        m = geometry_mask([mapping(g)], (H, W), tr, invert=True)
        p = {'Tipo': tipo, 'Área (ha)': round(a), 'Potencial de ventilação (0–100)': round(float(V[m].mean()) * 100)}
        rp = rio_proximo(g)
        if rp: p['Microbacia'] = rp
        bb = bairros_de(g)
        if bb: p['Bairros'] = ', '.join(bb)
        p['Altura média das edificações (m)'] = round(float(alt[m][urb[m] > 0.3].mean()), 1) if tem_alt and (urb[m] > 0.3).any() else None
        p['Área urbanizada (%)'] = round(float((urb[m] > 0.5).mean()) * 100)
        feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {k: v for k, v in p.items() if v is not None}})
    feats.sort(key=lambda f: -f['properties']['Área (ha)'])
    return feats
cor = vetoriza((V >= p70) & dentro_urb, 10, 'Canal de ventilação')
bar = vetoriza((V <= p15) & dentro_urb & (urb > 0.5), 15, 'Área de ar estagnado (barreira à ventilação)')
for f in cor:
    if f['properties']['Área urbanizada (%)'] < 15: f['properties']['Tipo'] = 'Entrada de ar fresco (área aberta dentro do perímetro)'
    else: f['properties']['Tipo'] = 'Canal de ventilação urbano'
cor.sort(key=lambda f: (f['properties']['Tipo'] != 'Canal de ventilação urbano', -f['properties']['Área (ha)']))
for i, f in enumerate(cor): f['properties'] = {'Nome': ('Canal' if 'Canal' in f['properties']['Tipo'] else 'Entrada de ar') + (f" – {f['properties']['Microbacia']}" if 'Microbacia' in f['properties'] else f' {i + 1}') + (f" ({f['properties']['Bairros'].split(', ')[0]})" if 'Canal' in f['properties']['Tipo'] and 'Bairros' in f['properties'] else ''), **f['properties']}
for i, f in enumerate(bar): f['properties'] = {'Nome': 'Ar estagnado' + (f" – {f['properties']['Bairros'].split(', ')[0]}" if 'Bairros' in f['properties'] else ''), **f['properties']}
json.dump({'type': 'FeatureCollection', 'features': cor}, open('data/vento/corredores.geojson', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump({'type': 'FeatureCollection', 'features': bar}, open('data/vento/barreiras.geojson', 'w'), ensure_ascii=False, separators=(',', ':'))

# setas de direção predominante: entram na cidade pelo lado de onde o vento vem; comprimento proporcional à frequência
c = sede.centroid; setas = []
NOME = {'N': 'Norte', 'NE': 'Nordeste', 'L': 'Leste', 'SE': 'Sudeste', 'S': 'Sul', 'SO': 'Sudoeste', 'O': 'Oeste', 'NO': 'Noroeste'}
kx = 1 / math.cos(math.radians(c.y))
for s_, ang, w in DIRS:
    th = math.radians(ang)                       # de onde vem
    ini = (c.x + 0.115 * kx * math.sin(th), c.y + 0.115 * math.cos(th))
    comp = 0.03 + 0.06 * w / DIRS[0][2]
    fim = (ini[0] - comp * kx * math.sin(th), ini[1] - comp * math.cos(th))
    vai = th + math.pi
    p1 = (fim[0] + 0.009 * kx * math.sin(vai + math.radians(150)), fim[1] + 0.009 * math.cos(vai + math.radians(150)))
    p2 = (fim[0] + 0.009 * kx * math.sin(vai - math.radians(150)), fim[1] + 0.009 * math.cos(vai - math.radians(150)))
    setas.append({'type': 'Feature', 'geometry': {'type': 'MultiLineString', 'coordinates': [[list(ini), list(fim)], [list(p1), list(fim), list(p2)]]},
                  'properties': {'Direção': f'Vento de {NOME[s_]}', 'Frequência (% dos dias)': round(freq[s_], 1)}})
json.dump({'type': 'FeatureCollection', 'features': setas}, open('data/vento/direcoes.geojson', 'w'), ensure_ascii=False)
res = {'direcoes': [{'setor': s, 'frequencia_pct': round(freq[s], 1)} for s, _, _ in DIRS], 'periodo_rosa': rosa.get('periodo'),
       'canais_urbanos': sum(1 for f in cor if 'Canal' in f['properties']['Tipo']), 'entradas_ar': sum(1 for f in cor if 'Entrada' in f['properties']['Tipo']), 'area_canais_ha': sum(f['properties']['Área (ha)'] for f in cor), 'barreiras': len(bar),
       'altura_edificacoes': bool(tem_alt)}
json.dump(res, open('data/vento/resumo.json', 'w'), ensure_ascii=False, indent=1)
print(res); print([f['properties'] for f in cor[:8]]); print([f['properties'] for f in bar[:5]])
