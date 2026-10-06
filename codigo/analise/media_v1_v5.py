import glob, os
import numpy as np
import pandas as pd

PASTA = os.path.expanduser("~/Documents/liverscan_dados/vazio")


def ler(prefixo):
    f = glob.glob(os.path.join(PASTA, prefixo + "_*.csv"))
    if len(f) != 1:
        raise SystemExit(f"Esperava 1 arquivo {prefixo}, achei {len(f)}")
    d = pd.read_csv(f[0])
    if len(d) != 120 or d[["real", "imag", "magnitude"]].isna().any().any():
        raise SystemExit("Arquivo incompleto ou com pares vazios: " + os.path.basename(f[0]))
    return d, os.path.basename(f[0])


v1, n1 = ler("vazio_1")
v5, n5 = ler("vazio_5")
if not v1[["e_pos", "e_neg"]].equals(v5[["e_pos", "e_neg"]]):
    raise SystemExit("Pares em ordem diferente entre v1 e v5")

z = ((v1.real + v5.real) / 2) + 1j * ((v1.imag + v5.imag) / 2)
saida = v1[["pair", "e_pos", "e_neg"]].copy()
saida["real"] = z.values.real
saida["imag"] = z.values.imag
saida["magnitude"] = np.abs(z.values)
saida["phase_deg"] = np.degrees(np.angle(z.values))
destino = os.path.join(PASTA, "baseline_media_v1_v5.csv")
saida.to_csv(destino, index=False)
print("Usando:", n1, "+", n5)
print("Salvo:", destino)

dif = (v5.magnitude - v1.magnitude) / v1.magnitude * 100
ruins = dif[dif.abs() > 5]
print(f"Pares em que v1 e v5 discordam mais de 5%: {len(ruins)} de 120")
for i in ruins.index:
    print(f"  par {int(v1.e_pos[i])}-{int(v1.e_neg[i])}: v1 {v1.magnitude[i]:.0f} / v5 {v5.magnitude[i]:.0f} ohms ({dif[i]:+.1f}%)")
