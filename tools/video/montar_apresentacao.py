"""Junta vídeo gravado + narração (nos instantes marcados) + trilha (abaixando sob a voz). Saída em 1920x1080.
Uso: montar_apresentacao.py video.webm marcas.json pasta_falas trilha.wav saida.mp4"""
import json, subprocess, sys, os
vid, marcas, falas, trilha, saida = sys.argv[1:6]
m = json.load(open(marcas))
corte = max(0, m['intro'] - 0.5)
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', vid], capture_output=True, text=True).stdout) - corte
ins = ['-ss', f'{corte:.2f}', '-i', vid, '-i', trilha]; filt = []; n = 1; vozes = []
for k, t in sorted(m.items(), key=lambda x: x[1]):
    w = os.path.join(falas, k + '.wav')
    if not os.path.exists(w): continue
    n += 1; ins += ['-i', w]
    filt.append(f'[{n}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={int((t - corte + 0.25) * 1000)}:all=1[a{n}]'); vozes.append(f'[a{n}]')
filt.append(''.join(vozes) + f'amix=inputs={len(vozes)}:normalize=0,apad,asplit=2[voz][chave]')
filt.append(f'[1:a]aresample=48000,volume=0.55,afade=t=out:st={max(0, dur - 4):.2f}:d=4[mus]')
filt.append('[mus][chave]sidechaincompress=threshold=0.03:ratio=7:attack=25:release=450[musd]')
filt.append('[voz][musd]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5[aout]')
filt.append(f'[0:v]scale=1920:1080:flags=lanczos,fade=t=in:st=0:d=0.6,fade=t=out:st={max(0, dur - 1.2):.2f}:d=1.2,format=yuv420p[vout]')
cmd = ['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(filt), '-map', '[vout]', '-map', '[aout]', '-t', f'{dur:.2f}',
       '-r', '30', '-c:v', 'libx264', '-crf', '24', '-preset', 'slow', '-maxrate', '2500k', '-bufsize', '5000k', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', saida + '.tmp.mp4']
subprocess.run(cmd, check=True); os.replace(saida + '.tmp.mp4', saida); print('ok', saida, round(dur, 1), 's')
