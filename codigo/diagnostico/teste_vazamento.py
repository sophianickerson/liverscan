"""Teste do vazamento de memoria: leituras seguidas SEM mexer nas chaves.

Uso:   python teste_vazamento.py [N]        (padrao: 400 leituras)

Liga a placa, monta UMA vez a receita de 4 fios (injeta 0 -> 1, le 3 - 4)
e le o AD5940 N vezes seguidas em modo impedancia. Antes da correcao do
firmware a placa travava por volta da leitura ~175. Com o firmware
corrigido, deve chegar ate o fim sem erro.
"""
import cmath
import glob
import math
import sys
import time

import adi

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400

portas = sorted(glob.glob("/dev/cu.usbmodem*"))
if not portas:
    sys.exit("Nenhuma porta usbmodem encontrada. Confira o cabo USB.")
print("Porta:", portas[0], "| leituras:", N)

cn = adi.cn0565(uri="serial:" + portas[0] + ",230400,8n1n")
cn.gpio1_toggle = True
cn.excitation_amplitude = 300
cn.excitation_frequency = 10000
cn.magnitude_mode = False
cn.impedance_mode = True
cn.add(0x71)
cn.add(0x70)
cn.immediate = True

# receita de 4 fios validada: F+ nas linhas Y0/Y1, F- em Y2/Y3, S+ em Y6, S- em Y7
cn[0][0] = True
cn[0][1] = True
cn[1][2] = True
cn[1][3] = True
cn[3][6] = True
cn[4][7] = True

mags, tempos = [], []
ok = 0
inicio = time.time()
for i in range(1, N + 1):
    t0 = time.time()
    try:
        z = cn.channel["voltage0"].raw
    except Exception as e:
        print("\n>>> FALHOU na leitura", i, "->", type(e).__name__, ":", e)
        break
    tempos.append(time.time() - t0)
    mags.append(abs(z))
    ok += 1
    if i % 25 == 0:
        m = sum(mags[-25:]) / 25
        t = sum(tempos[-25:]) / 25
        tmax = max(tempos[-25:])
        fase = math.degrees(cmath.phase(z))
        print("leitura %4d | |Z| medio %9.1f ohm | fase %7.2f | tempo medio %.3f s (max %.3f s)"
              % (i, m, fase, t, tmax))

print("\nResumo: %d de %d leituras OK em %.0f s." % (ok, N, time.time() - inicio))
if ok == N:
    print("PASSOU: nenhuma trava ate o fim.")
else:
    print("NAO passou: a placa parou na leitura", ok + 1, "- anote esse numero e me mande.")
