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
LIMITE = 5.0  # % de discordancia entre v1 e v5 para descartar um PAR (use 1000.0 para manter todos)
DADOS = os.path.expanduser("~/Documents/liverscan_dados")
SAIDA = os.path.expanduser("~/Documents/liverscan_imagens")


def ler_completo(prefixo):
    achados = []
    for f in sorted(glob.glob(os.path.join(DADOS, "**", prefixo + "_*.csv"), recursive=True)):
        if "antigos_29set" in f:
            continue
        d = pd.read_csv(f)
        if len(d) == 120:
            achados.append((f, d))
    if not achados:
        sys.exit("Nao achei arquivo completo de " + prefixo)
    f, d = achados[-1]
    print("usando:", os.path.relpath(f, DADOS))
    return d


base = pd.read_csv(os.path.join(DADOS, "vazio", "baseline_media_v1_v5.csv"))
v1 = ler_completo("vazio_1")
v5 = ler_completo("vazio_5")
casos = [
    ("controle_v6", "CONTROLE: vazio_6 contra baseline (sem objeto)", ler_completo("vazio_6")),
    ("A_tampa_eletrodo11", "POSICAO A: tampa no eletrodo 11 contra baseline", ler_completo("objeto_eletrodo11")),
    ("B_tampa_eletrodo3", "POSICAO B: tampa no eletrodo 3 contra baseline", ler_completo("objeto_eletrodo3")),
]

ref = base[["e_pos", "e_neg"]].values
for _, _, d in casos:
    if not np.array_equal(d[["e_pos", "e_neg"]].values, ref):
        sys.exit("Pares em ordem diferente entre arquivos")

dif = np.abs(v5.magnitude.values - v1.magnitude.values) / v1.magnitude.values * 100
usar = dif <= LIMITE
for nome, _, d in casos:
    vazios = d[d.magnitude.isna()]
    if len(vazios):
        print(nome, "- pares vazios fora:", ", ".join(f"{int(r.e_pos)}-{int(r.e_neg)}" for r in vazios.itertuples()))
    usar &= d.magnitude.notna().values
print(f"Pares usados: {int(usar.sum())} de 120 (nenhum eletrodo excluido)")

pares = base[["e_pos", "e_neg"]].values[usar].astype(int)
proto = PyEITProtocol(ex_mat=pares, meas_mat=pares.reshape(-1, 1, 2),
                      keep_ba=np.ones((len(pares), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.08)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.01, method="kotre", perm=1, jac_normalized=True)
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1],
                              malha.node[malha.el_pos[e]][0])) for e in range(N)]

v0 = base.magnitude.values[usar].astype(float)
res = []
for nome, titulo, d in casos:
    ds = eit.solve(d.magnitude.values[usar].astype(float), v0, normalize=True)
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
    ax.set_title(f"{titulo}\npico perto do eletrodo {prox}  ({int(usar.sum())} pares, todos os eletrodos)", fontsize=9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.colorbar(im, ax=ax, shrink=0.7, label="variacao relativa (azul = menos condutivo)")
    destino = os.path.join(SAIDA, f"imagem_{nome}_baseline_v1v5_todos_eletrodos.png")
    fig.savefig(destino, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Salvo:", destino)
