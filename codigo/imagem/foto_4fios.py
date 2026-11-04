"""LiverScan - MODO FOTO: uma varredura 4 fios = uma imagem (confiavel, sem loop).

Primeiro tire o baseline (tanque vazio):
    python foto_4fios.py baseline
Depois, cada posicao da batata:
    python foto_4fios.py meio
    python foto_4fios.py perto_e11
    (o nome e so um rotulo seu para a imagem)

Mede em dois pedacos (injecoes 0-7 e 8-15), cada um com conexao propria -
abaixo do limite de ~175 leituras, e sem o loop que trava a placa.
Compara com o baseline e salva/mostra a imagem. Usa JAC (mesma reconstrucao
que deu a boa imagem de hoje).

Se a placa travar (todas as leituras iguais), o script avisa para voce fazer
o ciclo de energia de 20 s.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

N = 16
DADOS = Path.home() / "Documents" / "liverscan_dados"
AQUI = Path(__file__).resolve().parent
BASELINE = DADOS / "baseline_foto_4fios.csv"
CHUNK = str(AQUI / "varredura_4fios_chunk.py")

if len(sys.argv) < 2:
    print("Uso: python foto_4fios.py baseline        (tanque vazio, tire primeiro)")
    print("     python foto_4fios.py NOME [mV]        (foto da batata numa posicao)")
    sys.exit(1)

nome = sys.argv[1]
eh_baseline = nome.lower() in ("baseline", "vazio", "base")
amplitude = int(sys.argv[2]) if len(sys.argv) >= 3 else 300


def medir_metade(injecoes):
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    tmp.close()
    r = subprocess.run([sys.executable, CHUNK, tmp.name, str(amplitude), injecoes],
                       capture_output=True, text=True)
    if r.returncode != 0:
        os.unlink(tmp.name)
        raise RuntimeError((r.stderr or r.stdout).strip()[-200:])
    d = pd.read_csv(tmp.name)
    os.unlink(tmp.name)
    return d


print(f"Medindo ({amplitude} mV)... (conexao unica, ~25 s)", flush=True)
d1 = medir_metade("0,1,2,3,4,5,6,7,8,9,10,11,12").sort_values(["inj_pos", "s_pos"]).reset_index(drop=True)

# checagem de placa travada (todas as leituras iguais)
if d1.magnitude.nunique() <= 2 or (d1.magnitude.max() - d1.magnitude.min()) < 1.0:
    print("=" * 55)
    print("ATENCAO: todas as leituras sairam IGUAIS (~%.0f ohm)." % d1.magnitude.median())
    print("A placa travou de novo. Faca o ciclo de energia:")
    print("  1) tire o cabo USB   2) espere 20 s   3) religue   4) espere 15 s")
    print("Depois rode este comando de novo.")
    print("=" * 55)
    sys.exit(1)

if eh_baseline:
    d1.to_csv(BASELINE, index=False)
    mags = d1.magnitude
    print("-" * 50)
    print(f"BASELINE salvo ({len(d1)} leituras). min/mediana/max: "
          f"{mags.min():.0f} / {mags.median():.0f} / {mags.max():.0f} ohm")
    print("Agora coloque a batata e rode: python foto_4fios.py NOME")
    sys.exit(0)

# modo foto: precisa do baseline
if not BASELINE.exists():
    sys.exit("Sem baseline. Rode primeiro: python foto_4fios.py baseline")
d_base = pd.read_csv(BASELINE).sort_values(["inj_pos", "s_pos"]).reset_index(drop=True)
chave = list(zip(d_base.inj_pos, d_base.inj_neg, d_base.s_pos, d_base.s_neg))
if list(zip(d1.inj_pos, d1.inj_neg, d1.s_pos, d1.s_neg)) != chave:
    sys.exit("As combinacoes nao batem com o baseline (algo saiu diferente).")

# salva o csv da foto
carimbo = time.strftime("%Y%m%d_%H%M%S")
csv_out = DADOS / f"foto_{nome}_4fios_{amplitude}mV_{carimbo}.csv"
d1.to_csv(csv_out, index=False)

# reconstrucao JAC
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyeit.mesh as mesh_mod
import pyeit.eit.jac as jac
from pyeit.eit.protocol import PyEITProtocol
from pyeit.eit.interp2d import sim2pts

ex_mat = d_base[["inj_pos", "inj_neg"]].values.astype(int)
meas_mat = d_base[["s_pos", "s_neg"]].values.astype(int).reshape(-1, 1, 2)
proto = PyEITProtocol(ex_mat=ex_mat, meas_mat=meas_mat,
                      keep_ba=np.ones((len(ex_mat), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.05)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.4, method="kotre", perm=1, jac_normalized=True)
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1],
                              malha.node[malha.el_pos[e]][0])) for e in range(N)]

ds = eit.solve(d1.magnitude.values.astype(float), d_base.magnitude.values.astype(float),
               normalize=True)
z = sim2pts(malha.node, malha.element, np.real(ds))
i = int(np.argmax(np.abs(z)))
a = np.degrees(np.arctan2(malha.node[i][1], malha.node[i][0]))
prox = int(np.argmin([abs((a - g + 180) % 360 - 180) for g in angs]))

lim = np.max(np.abs(z)) or 1
fig, ax = plt.subplots(figsize=(6.5, 6.5))
im = ax.tripcolor(malha.node[:, 0], malha.node[:, 1], malha.element, z,
                  shading="flat", cmap="RdBu_r", vmin=-lim, vmax=lim)
for e in range(N):
    x, y = malha.node[malha.el_pos[e]][:2]
    ax.plot(x, y, "ko", ms=4)
    ax.annotate(str(e), (x * 1.12, y * 1.12), ha="center", va="center", fontsize=9)
ax.set_aspect("equal"); ax.set_axis_off()
ax.set_title(f"LiverScan 4 fios - '{nome}'\nmaior variacao: eletrodo {prox}")
fig.colorbar(im, shrink=0.8, label="variacao de condutividade")
png = DADOS / f"foto_{nome}_4fios.png"
fig.savefig(png, dpi=150, bbox_inches="tight")
print("-" * 50)
print(f"Imagem salva: {png}")
print(f"Maior variacao perto do eletrodo {prox}")
subprocess.run(["open", str(png)], check=False)
