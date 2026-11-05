"""Junta vídeo gravado + falas nos instantes marcados. Uso: montar.py video.webm marcas.json pasta_falas saida.mp4"""
import json, subprocess, sys, os
vid, marcas, falas, saida = sys.argv[1:5]
m = json.load(open(marcas))
corte = max(0, m['intro'] - 0.8)                     # começa logo antes da abertura
ins = ['-ss', f'{corte:.2f}', '-i', vid]; filt = []; n = 0
for k, t in sorted(m.items(), key=lambda x: x[1]):
    w = os.path.join(falas, k + '.wav')
    if not os.path.exists(w): continue
    n += 1; ins += ['-i', w]
    filt.append(f'[{n}:a]aresample=48000,adelay={int((t - corte + 0.25) * 1000)}:all=1[a{n}]')
filt.append(''.join(f'[a{i}]' for i in range(1, n + 1)) + f'amix=inputs={n}:normalize=0,loudnorm=I=-16:TP=-1.5,apad[aout]')
cmd = ['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(filt), '-map', '0:v', '-map', '[aout]', '-shortest',
       '-r', '30', '-c:v', 'libx264', '-crf', '21', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', saida + '.tmp.mp4']
subprocess.run(cmd, check=True); os.replace(saida + '.tmp.mp4', saida); print('ok', saida)
