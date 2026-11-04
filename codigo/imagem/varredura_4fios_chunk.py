"""Pedaco de varredura 4 fios (uso interno do aovivo_4fios.py).

Uso: python varredura_4fios_chunk.py SAIDA.csv mV INJ1,INJ2,...
Roda em processo proprio: conexao nova, le os pares das injecoes pedidas
(13 por injecao), salva o CSV e sai. Sem prints, sem reconexao.
"""
import cmath
import csv
import glob
import math
import sys

import adi

N_EL = 16
saida = sys.argv[1]
amplitude = int(sys.argv[2])
injecoes = [int(x) % N_EL for x in sys.argv[3].split(",")]

portas = sorted(glob.glob("/dev/cu.usbmodem*"))
if not portas:
    sys.exit("sem porta usbmodem")

plano = []
for i in injecoes:
    a, b = i, (i + 1) % N_EL
    for s in range(N_EL):
        sp, sm = s, (s + 1) % N_EL
        if sp in (a, b) or sm in (a, b):
            continue
        plano.append((a, b, sp, sm))

import time
cn0565 = None
for tentativa in range(5):
    try:
        cn0565 = adi.cn0565(uri="serial:" + portas[0] + ",230400,8n1n")
        break
    except Exception:
        time.sleep(2)
if cn0565 is None:
    sys.exit("nao conectou apos 5 tentativas")
cn0565.gpio1_toggle = True
cn0565.excitation_amplitude = amplitude
cn0565.excitation_frequency = 10000
cn0565.magnitude_mode = False
cn0565.impedance_mode = True
cn0565.add(0x71)
cn0565.add(0x70)
cn0565.immediate = True

linhas = []
for seq, (a, b, sp, sm) in enumerate(plano, start=1):
    cn0565.gpio1_toggle = True
    cn0565[a][0] = True
    cn0565[a][1] = True
    cn0565[b][2] = True
    cn0565[b][3] = True
    cn0565[sp][6] = True
    cn0565[sm][7] = True
    z = cn0565.channel["voltage0"].raw
    mag, fase = cmath.polar(z)
    linhas.append([seq, a, b, sp, sm, z.real, z.imag, mag, math.degrees(fase)])

with open(saida, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag", "magnitude", "phase_deg"])
    w.writerows(linhas)
