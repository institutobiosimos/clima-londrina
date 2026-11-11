"""Gera a narração (Piper TTS, voz pt-BR) para cada trecho de narracao.json. Saída: PASTA/<chave>.wav e PASTA/duracoes.json"""
import json, subprocess, sys, os, wave
txt, modelo, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
dur = {}
for k, t in json.load(open(txt)).items():
    w = os.path.join(out, k + '.wav')
    subprocess.run(['piper', '--model', modelo, '--output_file', w, '--length_scale', os.environ.get('VELOCIDADE', '1.05'), '--sentence_silence', '0.25'], input=t.encode(), check=True, capture_output=True)
    with wave.open(w) as f: dur[k] = round(f.getnframes() / f.getframerate(), 2)
json.dump(dur, open(os.path.join(out, 'duracoes.json'), 'w'), indent=1)
print(dur)
