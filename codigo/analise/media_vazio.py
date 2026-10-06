import os, glob
import numpy as np
import pandas as pd

PASTA = os.path.expanduser("~/Documents/liverscan_dados/vazio")
arquivos = sorted(glob.glob(os.path.join(PASTA, "vazio_[123]_*.csv")))
if len(arquivos) != 3:
    raise SystemExit(f"Esperava 3 arquivos vazio_1/2/3, achei {len(arquivos)}")

dfs = [pd.read_csv(f) for f in arquivos]
for f, d in zip(arquivos, dfs):
    if len(d) != 120 or d[["real", "imag", "magnitude"]].isna().any().any():
        raise SystemExit("Arquivo incompleto ou com valores vazios: " + os.path.basename(f))

ref = dfs[0][["pair", "e_pos", "e_neg"]]
for f, d in zip(arquivos[1:], dfs[1:]):
    if not d[["pair", "e_pos", "e_neg"]].equals(ref):
        raise SystemExit("Pares em ordem diferente em: " + os.path.basename(f))

re = np.mean([d["real"].values for d in dfs], axis=0)
im = np.mean([d["imag"].values for d in dfs], axis=0)
z = re + 1j * im

saida = ref.copy()
saida["real"] = re
saida["imag"] = im
saida["magnitude"] = np.abs(z)
saida["phase_deg"] = np.degrees(np.angle(z))
destino = os.path.join(PASTA, "vazio_media.csv")
saida.to_csv(destino, index=False)
print("Salvo:", destino)

media_mag = saida["magnitude"].values
print("Diferenca de cada leitura em relacao a media (magnitude, em %):")
for f, d in zip(arquivos, dfs):
    dif = np.abs(d["magnitude"].values - media_mag) / media_mag * 100
    print(f"  {os.path.basename(f)[:8]}: tipica {np.median(dif):.2f}%   maxima {np.max(dif):.2f}%")
print(f"Magnitude media dos pares: de {media_mag.min():.0f} a {media_mag.max():.0f} ohms")
