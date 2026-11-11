"""Gera uma trilha instrumental original (sintetizada, sem direitos de terceiros) para o vídeo.
Uso: trilha.py SEGUNDOS saida.wav"""
import sys, wave, numpy as np
DUR, OUT = float(sys.argv[1]), sys.argv[2]
SR, BPM = 44100, 104
beat = 60 / BPM; n = int(DUR * SR); t = np.arange(n) / SR
mix = np.zeros((n, 2))
f = lambda m: 440 * 2 ** ((m - 69) / 12)
# progressão Am – F – C – G (2 compassos cada), clima de "descoberta"
acordes = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
baixos = [45, 41, 48, 43]
comp = 4 * beat; ciclo = 2 * comp


def env(L, a, r):
    e = np.ones(L); a = min(int(a * SR), L); r = min(int(r * SR), L - a)
    e[:a] = np.linspace(0, 1, a); e[L - r:] = np.linspace(1, 0, r); return e


def soma(ini, sinal, pan=0.0, g=1.0):
    i = int(ini * SR)
    if i >= n: return
    s = sinal[:n - i] * g
    mix[i:i + len(s), 0] += s * (1 - pan) ; mix[i:i + len(s), 1] += s * (1 + pan)


k = 0; tempo = 0.0
while tempo < DUR:
    ac, bx = acordes[k % 4], baixos[k % 4]
    L = int(ciclo * SR); tt = np.arange(L) / SR
    # pad: notas com leve desafinação e vibrato lento
    pad = sum(np.sin(2 * np.pi * f(m) * (1 + d) * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt)) for m in ac for d in (-0.002, 0.002))
    pad += 0.35 * sum(np.sin(2 * np.pi * f(m + 12) * tt) for m in ac)
    soma(tempo, pad * env(L, 1.2, 1.4), 0, 0.022)
    # baixo pulsante em colcheias
    for j in range(16):
        Lb = int(beat / 2 * SR); tb = np.arange(Lb) / SR
        nota = np.sin(2 * np.pi * f(bx - 12) * tb) + 0.3 * np.sin(2 * np.pi * f(bx) * tb)
        soma(tempo + j * beat / 2, nota * np.exp(-tb * 7) * env(Lb, .005, .03), 0, 0.10 if j % 2 == 0 else 0.06)
    # arpejo dedilhado (semicolcheias leves) a partir do 2º ciclo
    if k >= 1:
        seq = [ac[0] + 12, ac[1] + 12, ac[2] + 12, ac[1] + 24, ac[2] + 12, ac[1] + 12]
        for j in range(32):
            La = int(beat / 4 * 3 * SR); ta = np.arange(La) / SR; m = seq[j % len(seq)]
            nota = np.sin(2 * np.pi * f(m) * ta) + 0.25 * np.sin(2 * np.pi * f(m) * 2 * ta)
            soma(tempo + j * beat / 4, nota * np.exp(-ta * 9) * env(La, .003, .05), 0.35 if j % 2 else -0.35, 0.035)
    # batida suave (bumbo + chimbal) a partir do 3º ciclo
    if k >= 2:
        for j in range(8):
            Lk = int(0.25 * SR); tk = np.arange(Lk) / SR
            bumbo = np.sin(2 * np.pi * (55 + 90 * np.exp(-tk * 35)) * tk) * np.exp(-tk * 14)
            soma(tempo + j * beat, bumbo, 0, 0.16)
            Lh = int(0.06 * SR); ruido = np.random.default_rng(j).standard_normal(Lh) * np.exp(-np.arange(Lh) / SR * 70)
            ruido = np.diff(ruido, prepend=0)
            soma(tempo + j * beat + beat / 2, ruido, 0.2, 0.025)
    tempo += ciclo; k += 1
# eco simples para dar espaço
d = int(beat * 0.75 * SR); eco = np.zeros_like(mix); eco[d:] = mix[:-d] * 0.28; mix += eco
mix *= env(n, 2.5, 4.0)[:, None]
mix /= np.max(np.abs(mix)) + 1e-9; mix *= 0.85
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('trilha', OUT, round(DUR, 1), 's')
