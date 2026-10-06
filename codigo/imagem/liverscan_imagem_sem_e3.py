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
EXCLUIR = 3
DADOS = os.path.expanduser("~/Documents/liverscan_dados")
SAIDA = os.path.expanduser("~/Documents/liverscan_imagens")


def achar(padrao):
    f = glob.glob(os.path.join(DADOS, padrao))
    if len(f) != 1:
        sys.exit(f"Esperava 1 arquivo para {padrao}, achei {len(f)}")
    return f[0]


def ler(caminho):
    d = pd.read_csv(caminho)
    if len(d) != 120:
        sys.exit("Arquivo incompleto: " + os.path.basename(caminho))
    d = d[(d.e_pos != EXCLUIR) & (d.e_neg != EXCLUIR)].reset_index(drop=True)
    return d


base = ler(achar("vazio/vazio_1_*.csv"))
casos = [
    ("controle_vazio3_contra_vazio1", "CONTROLE: vazio_3 contra vazio_1 (sem objeto)",
     ler(achar("vazio/vazio_3_*.csv"))),
    ("A_objeto_eletrodo11_contra_vazio1", "POSICAO A: objeto no eletrodo 11 contra vazio_1",
     ler(achar("objeto_eletrodo11_*.csv"))),
    ("B_objeto_eletrodo3_contra_vazio1", "POSICAO B: objeto no eletrodo 3 contra vazio_1",
     ler(achar("objeto_eletrodo3_*.csv"))),
]

pares = base[["e_pos", "e_neg"]].values.astype(int)
for _, _, d in casos:
    if not np.array_equal(d[["e_pos", "e_neg"]].values.astype(int), pares):
        sys.exit("Pares em ordem diferente entre arquivos")
print(f"Pares usados: {len(pares)} de 120 (eletrodo {EXCLUIR} excluido)")

proto = PyEITProtocol(ex_mat=pares, meas_mat=pares.reshape(-1, 1, 2),
                      keep_ba=np.ones((len(pares), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.08)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.01, method="kotre", perm=1, jac_normalized=True)
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1],
                              malha.node[malha.el_pos[e]][0])) for e in range(N)]

v0 = base.magnitude.values.astype(float)
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
        txt = f"{e}*" if e == EXCLUIR else str(e)
        ax.text(1.12 * x, 1.12 * y, txt, ha="center", va="center", fontsize=9)
    ax.set_title(f"{titulo}\npico perto do eletrodo {prox}  (* = eletrodo excluido)", fontsize=9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.colorbar(im, ax=ax, shrink=0.7, label="variacao relativa (azul = menos condutivo)")
    destino = os.path.join(SAIDA, f"imagem_{nome}_sem_e3.png")
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Salvo:", destino)
