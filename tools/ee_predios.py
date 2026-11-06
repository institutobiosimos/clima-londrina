"""Altura e ocupação das edificações a partir do Google Earth Engine (Google Open Buildings 2.5D Temporal, 2023, 4 m).
Autentica com a conta de serviço guardada no segredo EE_CHAVE (JSON) e produz, na mesma grade do DEM
(/tmp/terreno/dem.tif, ~30 m): /tmp/terreno/predios_ocupacao.tif (fração 0–1 coberta por edificações) e
/tmp/terreno/predios_altura.tif (altura média das edificações presentes, m). Também gera data/vento/predios.png/json
(mapa de altura das edificações na área urbana) e data/vento/predios_resumo.json."""
import json, os, sys, numpy as np, rasterio, ee
from PIL import Image
chave = os.environ.get('EE_CHAVE')
if not chave:
    print('EE_CHAVE ausente – pulando'); sys.exit(0)
info = json.loads(chave)
ee.Initialize(ee.ServiceAccountCredentials(info['client_email'], key_data=chave), project=info.get('project_id', 'biosimos-clima'))
print('Earth Engine OK:', info['client_email'], flush=True)

with rasterio.open('/tmp/terreno/dem.tif') as f: tr = f.transform; H, W = f.height, f.width; perfil = f.profile
col = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1').filterDate('2023-01-01', '2024-01-01')
bb = ee.Geometry.Rectangle([tr.c, tr.f + tr.e * H, tr.c + tr.a * W, tr.f])
col = col.filterBounds(bb)
print('imagens 2023:', col.size().getInfo(), flush=True)
proj = col.first().projection()
mos = col.mosaic().setDefaultProjection(proj)
pres = mos.select('building_presence').gt(0.5).unmask(0)
alt = mos.select('building_height').unmask(0)
base = ee.Image.cat([pres.rename('ocup'), alt.multiply(pres).rename('hsoma')]).float().setDefaultProjection(proj)
ocup = np.zeros((H, W), 'float32'); hsoma = np.zeros((H, W), 'float32')
T = 200
for r0 in range(0, H, T):
    for c0 in range(0, W, T):
        h, w = min(T, H - r0), min(T, W - c0)
        x0, y0 = tr.c + c0 * tr.a, tr.f + r0 * tr.e
        ret = ee.Geometry.Rectangle([x0, y0 + h * tr.e, x0 + w * tr.a, y0], 'EPSG:4326', False)
        img = base.clip(ret).reduceResolution(ee.Reducer.mean(), maxPixels=4096)
        req = {'expression': img, 'fileFormat': 'NUMPY_NDARRAY',
               'grid': {'dimensions': {'width': w, 'height': h},
                        'affineTransform': {'scaleX': tr.a, 'shearX': 0, 'translateX': tr.c + c0 * tr.a,
                                            'shearY': 0, 'scaleY': tr.e, 'translateY': tr.f + r0 * tr.e},
                        'crsCode': 'EPSG:4326'}}
        for tent in range(3):
            try:
                a = ee.data.computePixels(req); break
            except Exception as e:
                print('tentativa', tent, r0, c0, str(e)[:200], flush=True)
                if tent == 2: raise
        ocup[r0:r0 + h, c0:c0 + w] = a['ocup']; hsoma[r0:r0 + h, c0:c0 + w] = a['hsoma']
    print('linhas', r0, flush=True)
altura = np.where(ocup > 0.02, hsoma / np.maximum(ocup, 1e-6), 0).astype('float32')
perfil.update(dtype='float32', nodata=None, compress='deflate')
with rasterio.open('/tmp/terreno/predios_ocupacao.tif', 'w', **perfil) as f: f.write(ocup.astype('float32'), 1)
with rasterio.open('/tmp/terreno/predios_altura.tif', 'w', **perfil) as f: f.write(altura, 1)

# mapa de altura para o site (só onde há ocupação relevante)
os.makedirs('data/vento', exist_ok=True)
CL = [(0, 4, (255, 245, 204, 0)), (4, 8, (254, 217, 118, 150)), (8, 15, (253, 141, 60, 185)), (15, 30, (227, 26, 28, 210)), (30, 999, (128, 0, 38, 235))]
im = np.zeros((H, W, 4), 'uint8')
for lo, hi, c in CL: im[(altura >= lo) & (altura < hi) & (ocup > 0.08)] = c
Image.fromarray(im, 'RGBA').save('data/vento/predios.png', optimize=True)
w_, s_, e_, n_ = rasterio.transform.array_bounds(H, W, tr)
json.dump({'imagem': 'data/vento/predios.png', 'cantos': [[w_, n_], [e_, n_], [e_, s_], [w_, s_]]}, open('data/vento/predios.json', 'w'))
m = ocup > 0.08
res = {'fonte': 'Google Open Buildings 2.5D Temporal (2023) via Google Earth Engine', 'area_ocupada_ha': round(float(ocup.sum() * abs(tr.a * tr.e) * 111320 * 110540 * 0.917 / 1e4)),
       'altura_media_m': round(float(altura[m].mean()), 1), 'celulas_acima_30m': int((altura >= 30).sum()), 'altura_max_celula_m': round(float(altura.max()), 1)}
json.dump(res, open('data/vento/predios_resumo.json', 'w'), ensure_ascii=False, indent=1); print(res)
