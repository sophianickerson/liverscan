"""LiverScan - imagem de diferenca (tudo em um).
Uso:
  python liverscan_imagem_diferenca.py                 (usa ~/Documents/liverscan_dados)
  python liverscan_imagem_diferenca.py PASTA_OU_CSVs   (pasta ou arquivos .csv)
  python liverscan_imagem_diferenca.py --base=VAZIO.csv PASTA_OU_CSVs  (baseline real)
Cada CSV completo (120 linhas) vira um painel. Sem --base, a baseline e estimada
(mediana por distancia entre eletrodos). Salva imagem_liverscan.png e abre no Mac.
"""
import sys, glob, os, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyeit.mesh as mesh_mod
import pyeit.eit.jac as jac
from pyeit.eit.protocol import PyEITProtocol
from pyeit.eit.interp2d import sim2pts

N = 16
NPARES = N * (N - 1) // 2
base_path, entradas = None, []
for a in sys.argv[1:]:
    if a.startswith("--base="):
        base_path = a.split("=", 1)[1]
    else:
        entradas.append(a)
if not entradas:
    entradas = [str(Path.home() / "Documents" / "liverscan_dados")]

arquivos = []
for e in entradas:
    e = os.path.expanduser(e)
    arquivos += sorted(glob.glob(os.path.join(e, "*.csv"))) if os.path.isdir(e) else [e]
validos = []
for f in arquivos:
    try:
        d = pd.read_csv(f)
        if len(d) == NPARES and {"e_pos", "e_neg", "magnitude"} <= set(d.columns):
            validos.append((f, d))
        else:
            print("Ignorado (incompleto ou formato diferente):", os.path.basename(f), f"[{len(d)} linhas]")
    except Exception as ex:
        print("Ignorado:", f, ex)
if not validos:
    sys.exit("Nenhum CSV completo (120 linhas) encontrado.")
validos.sort(key=lambda t: os.path.getmtime(t[0]))
d_base = pd.read_csv(base_path) if base_path else None

pares = validos[0][1][["e_pos", "e_neg"]].values.astype(int)
proto = PyEITProtocol(ex_mat=pares, meas_mat=pares.reshape(-1, 1, 2),
                      keep_ba=np.ones((len(pares), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.08)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.01, method="kotre", perm=1, jac_normalized=True)
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1], malha.node[malha.el_pos[e]][0])) for e in range(N)]

resultados = []
for f, d1 in validos:
    if list(zip(d1.e_pos, d1.e_neg)) != [tuple(p) for p in pares]:
        print("Ignorado (pares em ordem diferente):", os.path.basename(f)); continue
    if d_base is not None:
        v0 = d_base.magnitude.values.astype(float)
    else:
        sep = (d1.e_neg - d1.e_pos).abs().apply(lambda x: min(x, N - x))
        v0 = d1.groupby(sep)["magnitude"].transform("median").values.astype(float)
    ds = eit.solve(d1.magnitude.values.astype(float), v0, normalize=True)
    z = sim2pts(malha.node, malha.element, np.real(ds))
    i = int(np.argmax(np.abs(z)))
    a = np.degrees(np.arctan2(malha.node[i][1], malha.node[i][0]))
    prox = int(np.argmin([abs((a - g + 180) % 360 - 180) for g in angs]))
    print(f"{os.path.basename(f)}: maior variacao perto do eletrodo {prox}")
    resultados.append((os.path.basename(f), z, prox))

rotulo = "baseline REAL" if d_base is not None else "baseline ESTIMADA"
lim = max(np.max(np.abs(z)) for _, z, _ in resultados)
fig, axs = plt.subplots(1, len(resultados), figsize=(5.2 * len(resultados), 5.4), squeeze=False)
for ax, (nome, z, prox) in zip(axs[0], resultados):
    im = ax.tripcolor(malha.node[:, 0], malha.node[:, 1], malha.element, z,
                      shading="gouraud", cmap="RdBu_r", vmin=-lim, vmax=lim)
    for e in range(N):
        x, y = malha.node[malha.el_pos[e]][:2]
        ax.text(1.12 * x, 1.12 * y, str(e), ha="center", va="center", fontsize=9)
    ax.set_title(f"{nome[:38]}\nmaior variacao: eletrodo {prox}", fontsize=9)
    ax.set_aspect("equal"); ax.axis("off")
fig.suptitle(f"Variacao de condutividade ({rotulo}) - azul = menos condutivo", fontsize=11)
fig.colorbar(im, ax=axs[0].tolist(), shrink=0.7, label="variacao relativa")
fig.savefig("imagem_liverscan.png", dpi=150, bbox_inches="tight")
print("Salvo:", os.path.abspath("imagem_liverscan.png"))
if sys.platform == "darwin":
    subprocess.run(["open", "imagem_liverscan.png"])
