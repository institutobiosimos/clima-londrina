"""Qualidade do ar em Londrina – estações automáticas do IAT (boletim das últimas 24 h, serviço público GeoPR).
Roda todo dia: acrescenta as últimas 24 h ao histórico (data/ar/historico.csv, sem duplicar) e gera
data/ar/estacoes.geojson (situação mais recente de cada estação) e data/ar/resumo.json (médias e contagem por classe)."""
import csv, json, os, urllib.request, urllib.parse, datetime as dt
os.makedirs('data/ar', exist_ok=True)
URL = 'https://geopr.iat.pr.gov.br/server/rest/services/Hosted/boletim_ultimas_24h/FeatureServer/0/query'
q = {'where': "estacao like '%LONDRINA%'", 'outFields': '*', 'returnGeometry': 'true', 'outSR': 4326, 'orderByFields': 'hora', 'f': 'json'}
r = json.load(urllib.request.urlopen(urllib.request.Request(URL + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'clima-londrina-biosimos'}), timeout=90))
CAMPOS = ['estacao', 'data_hora_utc', 'iqa', 'qualidade', 'poluente', 'conc', 'so2_iqa', 'no2_iqa', 'o3_iqa', 'co_iqa', 'mp10_iqa', 'mp2_5_iqa', 'temp', 'umid']
H = 'data/ar/historico.csv'
hist = {}
if os.path.exists(H):
    for x in csv.DictReader(open(H, encoding='utf-8')): hist[(x['estacao'], x['data_hora_utc'])] = x
novos = 0; ultimo = {}
for f in r['features']:
    a = f['attributes']
    t = dt.datetime.fromtimestamp(a['hora'] / 1000, dt.timezone.utc).strftime('%Y-%m-%dT%H:00Z')
    lin = {k: ('' if a.get(k) is None else str(a.get(k)).strip()) for k in CAMPOS if k in a}
    lin.update(estacao=a['estacao'].strip(), data_hora_utc=t)
    if (lin['estacao'], t) not in hist: novos += 1
    hist[(lin['estacao'], t)] = lin
    ultimo[lin['estacao']] = (f, a, t)
with open(H, 'w', newline='', encoding='utf-8') as fo:
    w = csv.DictWriter(fo, CAMPOS); w.writeheader()
    for k in sorted(hist, key=lambda k: (k[1], k[0])): w.writerow({c: hist[k].get(c, '') for c in CAMPOS})
MEDE = {'LONDRINA': 'SO₂, MP2,5, temperatura e umidade', 'LONDRINA UEL': 'MP2,5, temperatura e umidade'}
feats = []
for est, (f, a, t) in ultimo.items():
    feats.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [f['geometry']['x'], f['geometry']['y']]},
                  'properties': {'nome': 'Estação de qualidade do ar – ' + ('Centro' if est == 'LONDRINA' else 'UEL' if est == 'LONDRINA UEL' else est.title()), 'Estação': est.title().replace('Uel', 'UEL'), 'estacao': est, 'Local': a.get('localizacao'), 'Mede': MEDE.get(est, ''),
                                 'Qualidade do ar (última hora)': (a.get('qualidade') or '').strip().capitalize(), 'Índice (IQAr)': a.get('iqa'),
                                 'Poluente que define o índice': (a.get('poluente') or '').strip(), 'Hora (UTC)': t, 'Fonte': 'IAT – rede de monitoramento automático'}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open('data/ar/estacoes.geojson', 'w'), ensure_ascii=False)
# resumo do histórico
from collections import Counter, defaultdict
cl = defaultdict(Counter); dias = defaultdict(set); iqa = defaultdict(list)
for (e, t), x in hist.items():
    q_ = (x.get('qualidade') or '').strip().upper()
    if q_ and q_ != 'SEM DADOS': cl[e][q_] += 1; iqa[e].append(float(x['iqa'])) if x.get('iqa') else None
    dias[e].add(t[:10])
res = {'atualizado_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'novos_registros': novos,
       'estacoes': {e: {'horas_com_dado': sum(cl[e].values()), 'dias': len(dias[e]), 'inicio': min(dias[e]), 'classes': dict(cl[e]),
                        'iqa_medio': round(sum(iqa[e]) / len(iqa[e]), 1) if iqa[e] else None, 'iqa_max': max(iqa[e]) if iqa[e] else None} for e in dias}}
json.dump(res, open('data/ar/resumo.json', 'w'), ensure_ascii=False, indent=1); print(res)
