"""NO₂ troposférico (Sentinel-5P/TROPOMI) via Google Earth Engine: média dos últimos 12 meses no norte do Paraná
(data/ar/no2.png/json) e série mensal sobre a área urbana de Londrina (data/ar/no2_serie.json)."""
import json, os, sys, datetime as dt, numpy as np, ee
from PIL import Image
chave = os.environ.get('EE_CHAVE')
if not chave: print('EE_CHAVE ausente'); sys.exit(0)
info = json.loads(chave)
ee.Initialize(ee.ServiceAccountCredentials(info['client_email'], key_data=chave), project=info.get('project_id'))
os.makedirs('data/ar', exist_ok=True)
hoje = dt.date.today().replace(day=1); ini = (hoje - dt.timedelta(days=365)).replace(day=1)
col = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2').select('tropospheric_NO2_column_number_density')
W, S, E, N = -52.0, -24.0, -50.3, -22.7
reg = ee.Geometry.Rectangle([W, S, E, N])
med = col.filterDate(str(ini), str(hoje)).mean().multiply(1e6)  # µmol/m²
nx, ny = 170, 130
a = ee.data.computePixels({'expression': med, 'fileFormat': 'NUMPY_NDARRAY',
    'grid': {'dimensions': {'width': nx, 'height': ny}, 'affineTransform': {'scaleX': (E - W) / nx, 'shearX': 0, 'translateX': W, 'shearY': 0, 'scaleY': -(N - S) / ny, 'translateY': N}, 'crsCode': 'EPSG:4326'}})
v = a['tropospheric_NO2_column_number_density'].astype('float32')
lo, hi = np.nanpercentile(v, 5), np.nanpercentile(v, 99.5)
t = np.clip((v - lo) / (hi - lo), 0, 1)
pal = np.array([[255, 255, 204], [254, 217, 118], [253, 141, 60], [227, 26, 28], [128, 0, 38]], 'float32')
idx = t * (len(pal) - 1); i0 = np.floor(idx).astype(int).clip(0, len(pal) - 2); fr = (idx - i0)[..., None]
rgb = pal[i0] * (1 - fr) + pal[i0 + 1] * fr
img = np.dstack([rgb.astype('uint8'), (60 + 150 * t).astype('uint8')])
Image.fromarray(img, 'RGBA').resize((nx * 4, ny * 4), Image.BILINEAR).save('data/ar/no2.png', optimize=True)
json.dump({'imagem': 'data/ar/no2.png', 'cantos': [[W, N], [E, N], [E, S], [W, S]], 'periodo': f'{ini:%m/%Y}–{(hoje - dt.timedelta(days=1)):%m/%Y}',
           'min_umol_m2': round(float(lo), 1), 'max_umol_m2': round(float(hi), 1)}, open('data/ar/no2.json', 'w'))
urb = ee.Geometry.Rectangle([-51.24, -23.37, -51.08, -23.26])
ruralp = ee.Geometry.Rectangle([-51.35, -23.75, -51.15, -23.55])
serie = []
m = dt.date(2019, 1, 1)
while m < hoje:
    p = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    im = col.filterDate(str(m), str(p)).mean().multiply(1e6)
    u = im.reduceRegion(ee.Reducer.mean(), urb, 5000).get('tropospheric_NO2_column_number_density')
    r_ = im.reduceRegion(ee.Reducer.mean(), ruralp, 5000).get('tropospheric_NO2_column_number_density')
    serie.append({'mes': f'{m:%Y-%m}', 'cidade': u, 'rural': r_}); m = p
vals = ee.List([ee.Dictionary(x) for x in serie]).getInfo()
for x in vals:
    for k in ('cidade', 'rural'): x[k] = round(x[k], 1) if x.get(k) is not None else None
json.dump({'unidade': 'µmol/m² (coluna troposférica de NO₂)', 'serie': vals}, open('data/ar/no2_serie.json', 'w'), ensure_ascii=False)
print('NO2 ok', vals[-3:], lo, hi)
