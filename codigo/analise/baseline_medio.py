"""Baseline MEDIO com as 16 injecoes (208 leituras) - tanque vazio.

Uso:  python baseline_medio.py [varreduras] [mV]       ex.: python baseline_medio.py 5 800

Faz N varreduras completas numa conexao so (cada ~18 s), tira a media de cada leitura e guarda tambem
o desvio entre varreduras (quais pares sao instaveis). Salva:
  ~/Documents/liverscan_dados/baseline_16inj_<mV>mV.csv      (media; mesmo formato dos outros baselines)
  ~/Documents/liverscan_dados/baseline_16inj_<mV>mV_desvio.csv (media, desvio, desvio % por leitura)
"""
import cmath, glob, math, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import adi

N_EL = 16
DADOS = Path.home() / "Documents" / "liverscan_dados"
n_var = int(sys.argv[1]) if len(sys.argv) > 1 else 5
amplitude = int(sys.argv[2]) if len(sys.argv) > 2 else 800

plano = []
for a in range(N_EL):
    b = (a + 1) % N_EL
    for s in range(N_EL):
        sp, sm = s, (s + 1) % N_EL
        if sp in (a, b) or sm in (a, b):
            continue
        plano.append((a, b, sp, sm))
print(f"{len(plano)} leituras por varredura | {n_var} varreduras | {amplitude} mV")

portas = sorted(glob.glob("/dev/cu.usbmodem*"))
if not portas:
    sys.exit("sem porta usbmodem")
c = None
for _ in range(5):
    try:
        c = adi.cn0565(uri="serial:" + portas[0] + ",230400,8n1n")
        break
    except Exception:
        time.sleep(2)
if c is None:
    sys.exit("nao conectou")
c.gpio1_toggle = True
c.excitation_amplitude = amplitude
c.excitation_frequency = 10000
c.magnitude_mode = False
c.impedance_mode = True
c.add(0x71)
c.add(0x70)
c.immediate = True

todas = []
for v in range(n_var):
    t0 = time.time()
    zs = []
    for (a, b, sp, sm) in plano:
        c.gpio1_toggle = True
        c[a][0] = True
        c[a][1] = True
        c[b][2] = True
        c[b][3] = True
        c[sp][6] = True
        c[sm][7] = True
        zs.append(c.channel["voltage0"].raw)
    todas.append(np.array(zs))
    print(f"  varredura {v + 1}/{n_var} pronta em {time.time() - t0:.0f} s", flush=True)

Z = np.array(todas)                      # (n_var, n_leituras) complexo
zm = Z.mean(axis=0)
mag_m = np.abs(Z).mean(axis=0)
sd = np.abs(Z).std(axis=0, ddof=1) if n_var > 1 else np.zeros(len(plano))

linhas = []
for k, (a, b, sp, sm) in enumerate(plano):
    mag, fase = cmath.polar(zm[k])
    linhas.append([k + 1, a, b, sp, sm, zm[k].real, zm[k].imag, mag_m[k], math.degrees(fase)])
cols = ["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag", "magnitude", "phase_deg"]
pd.DataFrame(linhas, columns=cols).to_csv(DADOS / f"baseline_16inj_{amplitude}mV.csv", index=False)
dd = pd.DataFrame(linhas, columns=cols)[["seq", "inj_pos", "s_pos"]]
dd["magnitude_media"] = mag_m
dd["desvio"] = sd
dd["desvio_pct"] = 100 * sd / mag_m
dd.to_csv(DADOS / f"baseline_16inj_{amplitude}mV_desvio.csv", index=False)

print("-" * 55)
print(f"BASELINE MEDIO salvo ({len(plano)} leituras, media de {n_var} varreduras)")
print(f"min/mediana/max |Z|: {mag_m.min():.0f} / {np.median(mag_m):.0f} / {mag_m.max():.0f} ohm")
if n_var > 1:
    p = dd.desvio_pct
    print(f"desvio entre varreduras: mediana {p.median():.2f}% | 90% abaixo de {p.quantile(.9):.1f}% | "
          f"max {p.max():.1f}% | leituras com desvio >3%: {(p > 3).sum()}")
