// Camada de animações do vídeo de apresentação (injetada pela gravação; não faz parte do site).
(() => {
    const css = `
    body.v-cine .sidebar, body.v-cine .mapboxgl-ctrl, body.v-cine #panelToggle, body.v-cine .mapboxgl-popup { display:none !important; }
    body.v-cine.v-painel .sidebar { display:flex !important; }
    body.v-cine .topbar { display:none !important; } body.v-cine .layout { height:100% !important; }
    .v-ov { position:fixed; z-index:99990; pointer-events:none; font-family:'Segoe UI','Noto Sans',Arial,sans-serif; color:#fff; }
    #v-marca { right:18px; top:14px; display:flex; align-items:center; gap:10px; background:rgba(10,38,30,.72); padding:7px 14px 7px 8px; border-radius:999px;
        font-weight:700; font-size:15px; letter-spacing:.3px; opacity:0; transition:opacity .8s; backdrop-filter:blur(4px); }
    #v-marca img { height:28px; background:#fff; border-radius:50%; padding:2px; }
    #v-marca span { font-weight:400; opacity:.8; }
    #v-prog { right:22px; top:62px; display:flex; gap:6px; opacity:0; transition:opacity .8s; }
    #v-prog i { width:26px; height:5px; border-radius:3px; background:rgba(255,255,255,.35); transition:background .5s, width .5s; }
    #v-prog i.on { background:#ffca28; width:44px; } #v-prog i.ok { background:#8bc34a; }
    #v-cap { left:34px; bottom:40px; max-width:640px; }
    #v-cap .n { display:inline-block; font:800 15px/1 Arial; letter-spacing:2px; color:#133d30; background:#ffca28; padding:6px 10px; border-radius:4px;
        transform:translateX(-30px); opacity:0; transition:all .5s cubic-bezier(.2,.9,.3,1.2); }
    #v-cap h2 { margin:10px 0 0; font-size:46px; line-height:1.05; font-weight:800; text-shadow:0 3px 18px rgba(0,0,0,.55);
        clip-path:inset(0 100% 0 0); transition:clip-path .8s cubic-bezier(.6,0,.2,1) .15s; }
    #v-cap p { margin:10px 0 0; font-size:21px; line-height:1.3; background:rgba(10,38,30,.78); padding:9px 14px; border-left:5px solid #8bc34a; border-radius:0 8px 8px 0;
        opacity:0; transform:translateY(14px); transition:all .6s ease .55s; }
    #v-cap.on .n { transform:none; opacity:1; } #v-cap.on h2 { clip-path:inset(0 0 0 0); } #v-cap.on p { opacity:1; transform:none; }
    body.v-painel #v-cap { left:auto; right:30px; max-width:560px; text-align:right; }
    body.v-painel #v-cap p { border-left:0; border-right:5px solid #8bc34a; border-radius:8px 0 0 8px; }
    #v-stats { inset:0; display:flex; align-items:center; justify-content:center; gap:26px; background:radial-gradient(ellipse at center, rgba(8,30,24,.55), rgba(8,30,24,.82)); opacity:0; transition:opacity .6s; }
    #v-stats.on { opacity:1; }
    .v-st { width:330px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.25); border-radius:18px; padding:26px 22px; text-align:center;
        opacity:0; transform:translateY(40px) scale(.9); transition:all .7s cubic-bezier(.2,.9,.3,1.25); backdrop-filter:blur(6px); }
    .v-st.on { opacity:1; transform:none; }
    .v-st b { display:block; font-size:74px; font-weight:800; line-height:1; color:#ffca28; font-variant-numeric:tabular-nums; }
    .v-st b.quente { color:#ff7043; } .v-st b.verde { color:#9ccc65; } .v-st b.azul { color:#4fc3f7; }
    .v-st span { display:block; margin-top:12px; font-size:19px; line-height:1.3; opacity:.92; }
    #v-chips { right:26px; top:70px; display:flex; flex-direction:column; gap:10px; align-items:flex-end; }
    .v-chip { background:rgba(10,38,30,.85); border-radius:12px; padding:10px 16px; font-size:17px; display:flex; align-items:center; gap:12px;
        opacity:0; transform:translateX(60px); transition:all .6s cubic-bezier(.2,.9,.3,1.2); box-shadow:0 6px 20px rgba(0,0,0,.3); }
    .v-chip.on { opacity:1; transform:none; }
    .v-chip b { font-size:30px; font-weight:800; color:#ffca28; min-width:50px; text-align:right; }
    body.v-painel #v-chips { right:auto; left:470px; align-items:flex-start; }
    #v-lista { inset:0; background:linear-gradient(135deg, rgba(0,96,150,.92), rgba(33,92,76,.94) 60%, rgba(19,61,48,.97)); display:flex; flex-direction:column;
        align-items:center; justify-content:center; padding:40px 70px; opacity:0; transition:opacity .7s; }
    #v-lista.on { opacity:1; }
    #v-lista h2 { margin:0 0 6px; font-size:44px; font-weight:800; } #v-lista h3 { margin:0 0 26px; font-size:20px; font-weight:400; opacity:.85; }
    #v-lista .gr { display:grid; grid-template-columns:repeat(2, 1fr); gap:14px 22px; width:100%; max-width:1080px; }
    #v-lista .gr.g4 { grid-template-columns:repeat(4, 1fr); }
    .v-it { display:flex; align-items:center; gap:16px; background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.22); border-radius:14px; padding:14px 18px;
        font-size:21px; line-height:1.25; opacity:0; transform:translateY(26px); transition:all .6s cubic-bezier(.2,.9,.3,1.2); }
    .v-it.on { opacity:1; transform:none; } .v-it.on.ativo { background:rgba(255,202,40,.22); border-color:#ffca28; }
    .v-it .ic { flex:none; width:54px; height:54px; border-radius:50%; background:#fff; display:flex; align-items:center; justify-content:center; font-size:30px; }
    .v-it small { display:block; font-size:15px; opacity:.8; margin-top:3px; }
    .g4 .v-it { flex-direction:column; text-align:center; padding:22px 14px; font-size:20px; }
    .g4 .v-it .ic { width:70px; height:70px; font-size:38px; }
    #v-intro, #v-fim { inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center;
        background:linear-gradient(135deg,#0080c9,#215c4c 62%,#133d30); transition:opacity 1s; }
    #v-intro img, #v-fim img { height:120px; background:#fff; border-radius:22px; padding:12px; animation:v-pop 1s cubic-bezier(.2,.9,.3,1.4) both; }
    #v-intro h1, #v-fim h1 { font-size:76px; margin:22px 0 6px; font-weight:800; letter-spacing:-1px; }
    #v-intro h1 span, #v-fim h1 span { display:inline-block; animation:v-sobe .8s cubic-bezier(.2,.9,.3,1.2) both; }
    #v-intro p, #v-fim p { font-size:26px; margin:6px; opacity:0; animation:v-aparece .8s ease both; }
    #v-intro .faixa { position:absolute; bottom:0; left:0; height:8px; background:linear-gradient(90deg,#4fc3f7,#8bc34a,#ffca28,#ff7043); animation:v-faixa 6s linear both; }
    #v-fim .cta { margin-top:26px; font-size:22px; background:#ffca28; color:#133d30; font-weight:800; padding:12px 26px; border-radius:999px; animation-delay:1.6s; }
    @keyframes v-pop { from { transform:scale(.3) rotate(-12deg); opacity:0 } to { transform:none; opacity:1 } }
    @keyframes v-sobe { from { transform:translateY(50px); opacity:0 } to { transform:none; opacity:1 } }
    @keyframes v-aparece { from { opacity:0; transform:translateY(12px) } to { opacity:.92; transform:none } }
    @keyframes v-faixa { from { width:0 } to { width:100% } }
    .v-alvo { width:26px; height:26px; border-radius:50%; background:#ffca28; border:3px solid #fff; box-shadow:0 0 0 0 rgba(255,202,40,.7); animation:v-pulso 1.6s infinite; }
    .v-alvo.frio { background:#4fc3f7; box-shadow:0 0 0 0 rgba(79,195,247,.7); animation-name:v-pulso2; }
    @keyframes v-pulso { 0% { box-shadow:0 0 0 0 rgba(255,202,40,.75) } 100% { box-shadow:0 0 0 36px rgba(255,202,40,0) } }
    @keyframes v-pulso2 { 0% { box-shadow:0 0 0 0 rgba(79,195,247,.75) } 100% { box-shadow:0 0 0 36px rgba(79,195,247,0) } }
    .v-rot { position:absolute; left:34px; top:-20px; white-space:nowrap; background:rgba(10,38,30,.9); color:#fff; border-radius:10px; padding:8px 14px;
        font:600 18px 'Segoe UI',Arial; box-shadow:0 6px 18px rgba(0,0,0,.35); animation:v-entra .6s cubic-bezier(.2,.9,.3,1.2) both .3s; }
    .v-rot b { display:block; font-size:30px; color:#ff7043; } .v-alvo.frio + .v-rot b { color:#4fc3f7; }
    @keyframes v-entra { from { opacity:0; transform:translateX(-20px) } to { opacity:1; transform:none } }
    `;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const el = (id, html = '') => { const d = document.createElement('div'); d.id = id; d.className = 'v-ov'; d.innerHTML = html; document.body.appendChild(d); return d; };
    const marca = el('v-marca', '<img src="logo_biosimos.png"> Clima Londrina <span>· Instituto Biosimos</span>');
    const prog = el('v-prog'); const cap = el('v-cap'); const stats = el('v-stats'); const chips = el('v-chips'); const lista = el('v-lista');
    const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const contar = (b, alvo, casas, pre, suf, ms) => {
        const t0 = performance.now();
        const passo = t => { const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
            b.textContent = pre + (alvo * e).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }) + suf; if (k < 1) requestAnimationFrame(passo); };
        requestAnimationFrame(passo);
    };
    const marcadores = [];
    window.V = {
        intro() {
            el('v-intro', `<img src="logo_biosimos.png"><h1>${'Clima Londrina'.split(' ').map((w, i) => `<span style="animation-delay:${.5 + i * .25}s">${w}</span>`).join(' ')}</h1>
                <p style="animation-delay:1.3s">Os dados do clima da cidade e do campo, em um só mapa</p>
                <p style="animation-delay:1.9s;font-size:19px">aberto · gratuito · atualizado todos os meses</p><div class="faixa"></div>`);
        },
        sairIntro() { const i = document.getElementById('v-intro'); i.style.opacity = 0; setTimeout(() => i.remove(), 1100); marca.style.opacity = 1; prog.style.opacity = 1; },
        progresso(n, total) { prog.innerHTML = Array.from({ length: total }, (_, i) => `<i class="${i < n ? 'ok' : i === n ? 'on' : ''}"></i>`).join(''); },
        capitulo(n, titulo, texto) {
            cap.classList.remove('on');
            setTimeout(() => { cap.innerHTML = `${n ? `<span class="n">${esc(n)}</span>` : ''}<h2>${titulo}</h2>${texto ? `<p>${texto}</p>` : ''}`;
                void cap.offsetWidth; cap.classList.add('on'); }, 350);
        },
        semCapitulo() { cap.classList.remove('on'); },
        stats(lst) {
            stats.innerHTML = lst.map(s => `<div class="v-st"><b class="${s.cor || ''}">${s.pre || ''}0${s.suf || ''}</b><span>${s.rot}</span></div>`).join('');
            void stats.offsetWidth; stats.classList.add('on');
        },
        mostrarStat(i) { const s = stats.children[i]; if (!s) return; s.classList.add('on'); const d = window.V._st[i];
            if (d && d.de != null) { const b = s.querySelector('b'); b.textContent = `${d.de}`; setTimeout(() => contar(b, d.v, d.casas || 0, d.pre || '', d.suf || '', 1500), 700); }
            else if (d) contar(s.querySelector('b'), d.v, d.casas || 0, d.pre || '', d.suf || '', 1600); },
        _st: [],
        sairStats() { stats.classList.remove('on'); },
        chips(lst) { chips.innerHTML = lst.map(c => `<div class="v-chip"><b>${esc(c.v)}</b><span>${c.rot}</span></div>`).join(''); },
        mostrarChip(i) { chips.children[i] && chips.children[i].classList.add('on'); },
        sairChips() { [...chips.children].forEach(c => c.classList.remove('on')); },
        lista(titulo, sub, itens, g4) {
            lista.innerHTML = `<h2>${titulo}</h2><h3>${sub}</h3><div class="gr ${g4 ? 'g4' : ''}">${itens.map(it => `<div class="v-it"><div class="ic">${it.ic}</div><div>${it.t}${it.s ? `<small>${it.s}</small>` : ''}</div></div>`).join('')}</div>`;
            void lista.offsetWidth; lista.classList.add('on');
        },
        mostrarItem(i) { const its = lista.querySelectorAll('.v-it'); its.forEach(x => x.classList.remove('ativo')); if (its[i]) its[i].classList.add('on', 'ativo'); },
        sairLista() { lista.classList.remove('on'); },
        alvo(lnglat, titulo, valor, frio) {
            const d = document.createElement('div'); d.innerHTML = `<div class="v-alvo ${frio ? 'frio' : ''}"></div><div class="v-rot">${esc(titulo)}<b>${esc(valor)}</b></div>`;
            const m = new mapboxgl.Marker({ element: d, anchor: 'center' }).setLngLat(lnglat).addTo(map); marcadores.push(m);
        },
        limparAlvos() { marcadores.splice(0).forEach(m => m.remove()); },
        fim() {
            el('v-fim', `<img src="logo_biosimos.png"><h1>${'Clima Londrina'.split(' ').map((w, i) => `<span style="animation-delay:${.4 + i * .25}s">${w}</span>`).join(' ')}</h1>
                <p style="animation-delay:1s">Dados abertos para uma cidade preparada para o clima</p>
                <p style="animation-delay:1.3s;font-size:20px">Uma iniciativa do Instituto Biosimos</p><p class="cta">Acesse · explore · compartilhe</p>`);
            marca.style.opacity = 0; prog.style.opacity = 0; cap.classList.remove('on');
        }
    };
})();
