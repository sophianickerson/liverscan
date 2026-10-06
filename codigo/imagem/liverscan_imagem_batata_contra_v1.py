import os, glob, sys
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
DADOS = os.path.expanduser("~/Documents/liverscan_dados")
SAIDA = os.path.expanduser("~/Documents/liverscan_imagens")


def ler(padrao):
    achados = []
    for f in sorted(glob.glob(os.path.join(DADOS, "**", padrao), recursive=True)):
        if "antigos_29set" in f:
            continue
        d = pd.read_csv(f)
        if len(d) == 120 and d.magnitude.notna().all():
            achados.append((f, d))
    if not achados:
        sys.exit("Nao achei arquivo completo e sem pares vazios: " + padrao)
    f, d = achados[-1]
    print("usando:", os.path.relpath(f, DADOS))
    return d


v1 = ler("vazio_1_*.csv")
casos = [
    ("controle_v5_contra_v1", "CONTROLE: vazio_5 contra vazio_1 (sem objeto)", ler("vazio_5_*.csv")),
    ("batata_eletrodo11_contra_v1", "BATATA perto do eletrodo 11 contra vazio_1", ler("batata_eletrodo11_*_155329.csv")),
]

ref = v1[["e_pos", "e_neg"]].values
for _, _, d in casos:
    if not np.array_equal(d[["e_pos", "e_neg"]].values, ref):
        sys.exit("Pares em ordem diferente entre arquivos")

pares = ref.astype(int)
proto = PyEITProtocol(ex_mat=pares, meas_mat=pares.reshape(-1, 1, 2),
                      keep_ba=np.ones((len(pares), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.08)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.01, method="kotre", perm=1, jac_normalized=True)
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1],
                              malha.node[malha.el_pos[e]][0])) for e in range(N)]

v0 = v1.magnitude.values.astype(float)
res = []
for nome, titulo, d in casos:
    ds = eit.solve(d.magnitude.values.astype(float), v0, normalize=True)
    z = sim2pts(malha.node, malha.element, np.real(ds))
    i = int(np.argmax(np.abs(z)))
    a = np.degrees(np.arctan2(malha.node[i][1], malha.node[i][0]))
    prox = int(np.argmin([abs((a - g + 180) % 360 - 180) for g in angs]))
    print(f"{nome}: pico {np.max(np.abs(z)):.3f}, perto do eletrodo {prox}")
    res.append((nome, titulo, z, prox))

lim = max(np.max(np.abs(z)) for _, _, z, _ in res)
print(f"Escala comum das imagens: +-{lim:.3f}")
for nome, titulo, z, prox in res:
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.tripcolor(malha.node[:, 0], malha.node[:, 1], malha.element, z,
                      shading="gouraud", cmap="RdBu_r", vmin=-lim, vmax=lim)
    for e in range(N):
        x, y = malha.node[malha.el_pos[e]][:2]
        ax.text(1.12 * x, 1.12 * y, str(e), ha="center", va="center", fontsize=9)
    ax.set_title(f"{titulo}\npico perto do eletrodo {prox}  (120 pares, 16 eletrodos)", fontsize=9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.colorbar(im, ax=ax, shrink=0.7, label="variacao relativa (azul = menos condutivo)")
    destino = os.path.join(SAIDA, f"imagem_{nome}.png")
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Salvo:", destino)
