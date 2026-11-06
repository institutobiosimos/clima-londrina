"""Diagnóstico: descobre as camadas do painel de qualidade do ar do IAT (GeoPR) e mostra campos e amostras."""
import json, re, urllib.request, urllib.parse
P = 'https://geopr.iat.pr.gov.br/portal/sharing/rest/content/items/'
UA = {'User-Agent': 'clima-londrina-biosimos'}
def get(u, **q):
    q.setdefault('f', 'json')
    u = u + ('&' if '?' in u else '?') + urllib.parse.urlencode(q)
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90))
vistos, urls, itens = set(), set(), ['faf93ddb323f4dcf9fe2331bbee1e9c7']
while itens:
    i = itens.pop()
    if i in vistos: continue
    vistos.add(i)
    try:
        meta = get(P + i); data = get(P + i + '/data')
    except Exception as e:
        print('item', i, 'ERRO', e); continue
    print('ITEM', i, meta.get('type'), '|', meta.get('title'), '|', meta.get('url'))
    if meta.get('url'): urls.add(meta['url'])
    txt = json.dumps(data)
    for u in re.findall(r'https?://[^"\\]+?/(?:Feature|Map)Server(?:/\d+)?', txt): urls.add(u)
    for j in set(re.findall(r'"itemId"\s*:\s*"([0-9a-f]{32})"', txt)): itens.append(j)
for u in sorted(urls):
    try:
        d = get(u)
        print('\nSERVIÇO', u, '|', d.get('name') or d.get('serviceDescription', '')[:80])
        camadas = [u] if re.search(r'/\d+$', u) else [f"{u}/{l['id']}" for l in d.get('layers', []) + d.get('tables', [])]
        for c in camadas:
            m = get(c)
            print('  CAMADA', c, '|', m.get('name'), '| campos:', [f['name'] for f in m.get('fields', [])])
            try:
                n = get(c + '/query', where='1=1', returnCountOnly='true')
                am = get(c + '/query', where='1=1', outFields='*', resultRecordCount=3, returnGeometry='true', outSR=4326)
                print('    total', n.get('count'), '| amostra:', json.dumps([x.get('attributes') for x in am.get('features', [])], ensure_ascii=False)[:1500])
                lon = get(c + '/query', where="1=1", outFields='*', resultRecordCount=2000, returnGeometry='true', outSR=4326)
                ld = [x for x in lon.get('features', []) if 'ONDRINA' in json.dumps(x.get('attributes'), ensure_ascii=False).upper()]
                print('    Londrina:', len(ld), json.dumps(ld[:5], ensure_ascii=False)[:2500])
            except Exception as e:
                print('    consulta ERRO', e)
    except Exception as e:
        print('SERVIÇO', u, 'ERRO', e)
