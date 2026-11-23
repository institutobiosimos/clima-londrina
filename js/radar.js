// ---------- Radar de chuva ao vivo (RainViewer, uso não comercial) ----------
// Últimas ~2 horas em quadros de 10 min; visão regional (o serviço gratuito vai até o zoom 7).
const RADAR_API = 'https://api.rainviewer.com/public/weather-maps.json';
const RADAR = { quadros: [], i: 0, timer: null, recarga: null, o: null, tocando: true };
function radarAdicionar(d) {
    d.camadas_opcionais = d.camadas_opcionais || [];
    if (d.camadas_opcionais.some(o => o.id === 'radar-chuva')) return;
    d.camadas_opcionais.unshift({ id: 'radar-chuva', tipo: 'radar', secao: 'Tempo agora', nome: 'Chuva agora – radar (últimas 2 h)', icone: 'fill', cor: '#1e88e5', opacidade: 0.75,
        legenda_itens: [{ rotulo: 'chuva fraca', cor: '#8fd3fe' }, { rotulo: 'moderada', cor: '#1e88e5' }, { rotulo: 'forte', cor: '#f6c344' }, { rotulo: 'muito forte / granizo', cor: '#e53935' }],
        fonte: 'Radar meteorológico: RainViewer (rainviewer.com), atualizado a cada 10 minutos.' });
}
async function radarDesenhar(o, antes) {
    RADAR.o = o; RADAR.antes = antes;
    const j = await (await fetch(RADAR_API, { cache: 'no-cache' })).json();
    const host = j.host || 'https://tilecache.rainviewer.com';
    radarLimparCamadas();
    RADAR.quadros = (j.radar && j.radar.past || []).map((f, k) => ({ t: f.time, id: `op-${o.id}-${k}`, url: `${host}${f.path}/256/{z}/{x}/{y}/2/1_0.png` }));
    for (const q of RADAR.quadros) {
        map.addSource(q.id, { type: 'raster', tiles: [q.url], tileSize: 256, maxzoom: 7, attribution: 'Radar © <a href="https://www.rainviewer.com" target="_blank" rel="noopener">RainViewer</a>' });
        map.addLayer({ id: q.id, type: 'raster', source: q.id, paint: { 'raster-opacity': 0, 'raster-opacity-transition': { duration: 0 }, 'raster-resampling': 'linear' } }, antes);
    }
    RADAR.i = RADAR.quadros.length - 1; radarMostrar(); radarPainel(true);
    if (map.getZoom() > 9.2) map.easeTo({ zoom: 8.2, duration: 1200 });   // abre a visão regional para ver a chuva chegando
    radarTocar(RADAR.tocando);
    clearInterval(RADAR.recarga); RADAR.recarga = setInterval(() => { if (opcionaisAtivas.has(o.id)) radarDesenhar(o, antes).catch(console.error); }, 10 * 60 * 1000);
}
function radarMostrar() {
    RADAR.quadros.forEach((q, k) => { if (map.getLayer(q.id)) map.setPaintProperty(q.id, 'raster-opacity', k === RADAR.i ? (RADAR.o.opacidade ?? 0.75) : 0); });
    const q = RADAR.quadros[RADAR.i], el = document.getElementById('radarHora');
    if (q && el) {
        const d = new Date(q.t * 1000), ult = RADAR.i === RADAR.quadros.length - 1;
        el.textContent = `${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' })}${ult ? ' · mais recente' : ''}`;
        const b = document.getElementById('radarBarra'); if (b) b.style.width = `${(RADAR.i + 1) / RADAR.quadros.length * 100}%`;
    }
}
function radarTocar(on) {
    RADAR.tocando = on; clearInterval(RADAR.timer);
    const bt = document.getElementById('radarPlay'); if (bt) { bt.textContent = on ? '❚❚' : '▶'; bt.setAttribute('aria-label', on ? 'Pausar animação' : 'Animar'); }
    if (!on) return;
    RADAR.timer = setInterval(() => {
        RADAR.i = (RADAR.i + 1) % RADAR.quadros.length; radarMostrar();
        if (RADAR.i === RADAR.quadros.length - 1) { clearInterval(RADAR.timer); setTimeout(() => RADAR.tocando && radarTocar(true), 1600); }   // pausa no quadro mais recente
    }, 650);
}
function radarPainel(on) {
    let el = document.getElementById('radarPainel');
    if (!on) { if (el) el.remove(); return; }
    if (!el) {
        el = document.createElement('div'); el.id = 'radarPainel';
        el.innerHTML = `<button type="button" id="radarPlay" aria-label="Pausar animação">❚❚</button><div><b>Radar de chuva</b> <span id="radarHora">–</span><i><em id="radarBarra"></em></i></div>`;
        document.getElementById('map').appendChild(el);
        el.querySelector('#radarPlay').addEventListener('click', () => radarTocar(!RADAR.tocando));
    }
    radarMostrar();
}
function radarLimparCamadas() {
    for (const q of RADAR.quadros) { if (map.getLayer(q.id)) map.removeLayer(q.id); if (map.getSource(q.id)) map.removeSource(q.id); }
}
function radarRemover() {
    clearInterval(RADAR.timer); clearInterval(RADAR.recarga); radarLimparCamadas(); RADAR.quadros = []; radarPainel(false);
}
