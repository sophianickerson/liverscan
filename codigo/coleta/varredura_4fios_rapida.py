"""Varredura EIT 4 fios - versao RAPIDA (para caminhar rumo ao tempo real).

Uso:   python varredura_4fios_rapida.py NOME [mV]
Ex.:   python varredura_4fios_rapida.py vazio_teste 300

Diferencas da varredura normal:
- reset dos interruptores via gpio1_toggle (1 comando) em vez de open_all (192 comandos)
- sem pausa entre leituras
- reconecta a serial por software a cada 120 leituras (teste contra o
  travamento das ~177 leituras, sem precisar replugar o USB)
- cronometra e imprime o tempo total do quadro

Mesmo CSV da varredura normal. Control + C: para e salva o que ja foi medido.
"""
import cmath
import csv
import glob
import math
import os
import signal
import sys
import time

import gc

import adi

N_EL = 16
RECONECTA_A_CADA = 140  # a placa trava apos ~175 leituras por conexao; reconectar antes

if len(sys.argv) not in (2, 3):
    print("Uso: python varredura_4fios_rapida.py NOME [mV]")
    sys.exit(1)

nome = sys.argv[1]
amplitude = int(sys.argv[2]) if len(sys.argv) == 3 else 300
if not (1 <= amplitude <= 600):
    sys.exit(f"Amplitude fora do limite (1 a 600 mV): {amplitude}")

portas = sorted(glob.glob("/dev/cu.usbmodem*"))
if not portas:
    sys.exit("Nenhuma porta usbmodem encontrada. Confira o cabo USB.")
porta = portas[0]
print("Porta:", porta, flush=True)

plano = []
for i in range(N_EL):
    a, b = i, (i + 1) % N_EL
    for s in range(N_EL):
        sp, sm = s, (s + 1) % N_EL
        if sp in (a, b) or sm in (a, b):
            continue
        plano.append((a, b, sp, sm))
print(f"{len(plano)} leituras, {amplitude} mV, 10 kHz, modo rapido.", flush=True)


def abrir():
    c = adi.cn0565(uri="serial:" + porta + ",230400,8n1n")
    c.gpio1_toggle = True
    c.excitation_amplitude = amplitude
    c.excitation_frequency = 10000
    c.magnitude_mode = False
    c.impedance_mode = True
    c.add(0x71)
    c.add(0x70)
    c.immediate = True
    return c


def reconectar(c):
    try:
        c.close()         # metodo oficial do pyadi: destroi a conexao e solta a porta
    except Exception:
        pass
    try:
        del c
    except Exception:
        pass
    gc.collect()
    for tent in range(3):
        time.sleep(5)
        try:
            return abrir()
        except Exception as e:
            print(f"  [reconexao tentativa {tent + 1} falhou: {e}]", flush=True)
            gc.collect()
    raise RuntimeError("Nao consegui reconectar. Repluge o USB e rode de novo.")


cn0565 = abrir()

parar = False


def pedir_parada(signum, frame):
    global parar
    parar = True
    print("\n[Control + C recebido: salvando o que ja foi medido]", flush=True)


signal.signal(signal.SIGINT, pedir_parada)

linhas = []
erros = 0
desde_reconexao = 0
t0 = time.time()

try:
    for seq, (a, b, sp, sm) in enumerate(plano, start=1):
        if parar:
            break
        if RECONECTA_A_CADA and desde_reconexao >= RECONECTA_A_CADA:
            print(f"  [reconectando a serial por software apos {desde_reconexao} leituras...]", flush=True)
            cn0565 = reconectar(cn0565)
            desde_reconexao = 0
        try:
            cn0565.gpio1_toggle = True   # reseta os dois chips num comando so
            cn0565[a][0] = True   # injecao + -> Y0 (CE0)
            cn0565[a][1] = True   # injecao + -> Y1 (RE0)
            cn0565[b][2] = True   # injecao - -> Y2 (SE0)
            cn0565[b][3] = True   # injecao - -> Y3 (DE0)
            cn0565[sp][6] = True  # leitura + -> Y6 (AIN2)
            cn0565[sm][7] = True  # leitura - -> Y7 (AIN3)
            z = cn0565.channel["voltage0"].raw
            erros = 0
            desde_reconexao += 1
        except Exception as e:
            erros += 1
            print(f"seq {seq} inj {a}-{b} le {sp}-{sm}  ERRO: {e}", flush=True)
            if erros >= 3:
                print("3 erros seguidos. Parando e salvando.", flush=True)
                break
            print("  [tentando reconectar a serial por software...]", flush=True)
            try:
                cn0565 = reconectar(cn0565)
                desde_reconexao = 0
            except Exception as e2:
                print("  [", e2, "]", flush=True)
                break
            continue

        mag, fase = cmath.polar(z)
        linhas.append([seq, a, b, sp, sm, z.real, z.imag, mag, math.degrees(fase)])
        if sp == (b + 1) % N_EL or len(linhas) == 1:
            print(f"injecao {a}-{b}  ({seq}/{len(plano)}, {time.time() - t0:.0f} s)", flush=True)
finally:
    try:
        cn0565.open_all()
    except Exception:
        pass

dur = time.time() - t0
if not linhas:
    sys.exit("Nenhuma leitura valida; nada foi salvo.")

pasta = os.path.expanduser("~/Documents/liverscan_dados")
os.makedirs(pasta, exist_ok=True)
carimbo = time.strftime("%Y%m%d_%H%M%S")
arq = os.path.join(pasta, f"{nome}_4fios_10kHz_{amplitude}mV_{carimbo}.csv")
with open(arq, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag", "magnitude", "phase_deg"])
    w.writerows(linhas)

mags = sorted(l[7] for l in linhas)
print("-" * 50, flush=True)
print(f"Leituras validas: {len(linhas)} de {len(plano)} em {dur / 60:.1f} min "
      f"({dur / max(len(linhas), 1):.2f} s por leitura)", flush=True)
print(f"Magnitude min / mediana / max: {mags[0]:.1f} / {mags[len(mags) // 2]:.1f} / {mags[-1]:.1f} ohm", flush=True)
print("Salvo em:", arq, flush=True)
