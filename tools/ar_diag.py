import json, urllib.request, urllib.parse, collections
UA = {'User-Agent': 'clima-londrina-biosimos'}
def get(u, **q):
    q.setdefault('f', 'json'); u = u + ('&' if '?' in u else '?') + urllib.parse.urlencode(q)
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90))
S = 'https://geopr.iat.pr.gov.br/server/rest/services'
h = get(S + '/Hosted')
print('Hosted com termos de ar:', [s['name'] for s in h.get('services', []) if any(k in s['name'].lower() for k in ('boletim', 'iqa', 'iqar', 'ar_', 'qualidade', 'estac', 'polu', 'vento', 'monit', 'linha', 'tempo', 'serie', 'hist'))])
B = S + '/Hosted/boletim_ultimas_24h/FeatureServer/0/query'
r = get(B, where="estacao like '%LONDRINA%'", outFields='*', returnGeometry='true', outSR=4326, orderByFields='hora')
por = collections.defaultdict(list)
for f in r['features']: por[f['attributes']['estacao']].append(f)
for est, fs in por.items():
    a = fs[0]['attributes']
    print('\nESTAÇÃO', est, '|', a['localizacao'], '|', fs[0]['geometry'])
    cols = [c for c in ('so2_iqa', 'no2_iqa', 'o3_iqa', 'co_iqa', 'mp10_iqa', 'mp2_5_iqa', 'pts_iqa', 'temp', 'umid') if any(f['attributes'][c] is not None for f in fs)]
    print('  medidos:', cols, '| registros:', len(fs))
    for f in fs[-24:]:
        x = f['attributes']; print('  ', x['hora'], x['iqa'], x['qualidade'], x['poluente'], x['conc'], {c: x[c] for c in cols})
print('\nTodas as estações:', sorted({f['attributes']['estacao'] for f in get(B, where='1=1', outFields='estacao', returnGeometry='false', returnDistinctValues='true')['features']}))
for s in h.get('services', []):
    print('svc', s['name'], s['type'])
