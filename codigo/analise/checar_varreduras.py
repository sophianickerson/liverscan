import glob, os, re
import numpy as np, pandas as pd

BASE = os.path.expanduser("~/Documents/liverscan_dados")
TOLERANCIA = 3.0  # % de desvio de cada eletrodo em relacao a mediana geral

itens = []
for f in glob.glob(BASE + "/**/*.csv", recursive=True):
    nome = os.path.basename(f)
    if "antigos_29set" in f or "media" in nome:
        continue
    m = re.search(r"_(\d{8}_\d{6})\.csv$", nome)
    itens.append((m.group(1) if m else "", f))
itens.sort()

for _, f in itens:
    nome = os.path.basename(f)
    d = pd.read_csv(f)
    if len(d) != 120:
        print(f"{nome[:38]:38} INCOMPLETO ({len(d)} linhas)")
        continue
    nans = int(d.magnitude.isna().sum())
    med = np.array([d[(d.e_pos == e) | (d.e_neg == e)].magnitude.median() for e in range(16)])
    ref = np.median(med)
    ruins = [e for e in range(16) if abs(med[e] - ref) / ref * 100 > TOLERANCIA]
    if nans == 0 and not ruins:
        print(f"{nome[:38]:38} PASSA")
    else:
        motivo = []
        if nans:
            motivo.append(f"{nans} par(es) vazio(s)")
        if ruins:
            motivo.append("eletrodo(s) fora: " + ", ".join(f"{e} ({med[e]:.0f} ohms)" for e in ruins))
        print(f"{nome[:38]:38} REPROVA  " + "; ".join(motivo))
