"""LiverScan - metricas de ruido do tanque vazio (Eq. 14 e 15 do artigo arXiv 2505.19146).

Uso:
    python metricas_varreduras.py                      (usa ~/Documents/liverscan_dados, arquivos com "vazio")
    python metricas_varreduras.py PASTA_OU_CSVs ...    (pasta ou arquivos .csv)
    python metricas_varreduras.py --filtro=vazio300    (so arquivos cujo nome contem esse texto)

Le varreduras COMPLETAS (120 pares validos) do tanque vazio feitas na mesma
amplitude e calcula, para cada par, entre as varreduras repetidas:
  RSD (%) = desvio padrao / media * 100          (Eq. 15)
  SNR (dB) = 10 log10( soma Z^2 / soma (Z - media)^2 )   (Eq. 14)
Varreduras de amplitudes diferentes NAO sao misturadas (sao analisadas em grupos).
Nao usa a placa, so le os CSVs.
"""
import glob
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NPARES = 120

filtro = "vazio"
entradas = []
for a in sys.argv[1:]:
    if a.startswith("--filtro="):
        filtro = a.split("=", 1)[1]
    else:
        entradas.append(a)
if not entradas:
    entradas = [str(Path.home() / "Documents" / "liverscan_dados")]

arquivos = []
for e in entradas:
    e = os.path.expanduser(e)
    arquivos += sorted(glob.glob(os.path.join(e, "*.csv"))) if os.path.isdir(e) else [e]

grupos = {}  # amplitude -> lista de (nome, Series de magnitude indexada por par)
for f in arquivos:
    nome = os.path.basename(f)
    if filtro not in nome:
        continue
    m = re.search(r"_(\d+)mV_", nome)
    amp = int(m.group(1)) if m else 100  # arquivos antigos sem mV no nome eram 100 mV
    try:
        d = pd.read_csv(f)
    except Exception as ex:
        print("Ignorado (erro ao ler):", nome, ex)
        continue
    if not {"e_pos", "e_neg", "magnitude"} <= set(d.columns) or len(d) != NPARES:
        print("Ignorado (incompleto ou formato diferente):", nome, "[{} linhas]".format(len(d)))
        continue
    if d["magnitude"].isna().any():
        print("Ignorado (tem nan):", nome)
        continue
    serie = pd.Series(d["magnitude"].values,
                      index=list(zip(d["e_pos"].astype(int), d["e_neg"].astype(int))))
    grupos.setdefault(amp, []).append((nome, serie))

if not grupos:
    sys.exit("Nenhuma varredura completa encontrada (filtro '{}').".format(filtro))

for amp in sorted(grupos):
    lista = grupos[amp]
    print("=" * 60)
    print("Amplitude {} mV: {} varreduras completas".format(amp, len(lista)))
    for nome, _ in lista:
        print("  -", nome)
    if len(lista) < 2:
        print("  Preciso de pelo menos 2 varreduras na mesma amplitude para medir a variacao.")
        continue
    if len(lista) < 3:
        print("  Aviso: com so {} varreduras a estimativa e grosseira. Ideal: 3 ou mais.".format(len(lista)))
    tabela = pd.concat([s for _, s in lista], axis=1)
    Z = tabela.values.astype(float)           # linhas = pares, colunas = varreduras
    media = Z.mean(axis=1)
    desvio = np.sqrt(((Z - media[:, None]) ** 2).mean(axis=1))   # Eq. 15 (1/N)
    rsd = 100.0 * desvio / media
    soma_quad = (Z ** 2).sum(axis=1)
    soma_dev = ((Z - media[:, None]) ** 2).sum(axis=1)
    with np.errstate(divide="ignore"):
        snr = 10.0 * np.log10(soma_quad / soma_dev)              # Eq. 14
    snr_ok = snr[np.isfinite(snr)]
    print("  RSD por par: mediana {:.2f}% | media {:.2f}% | maximo {:.2f}%".format(
        np.median(rsd), rsd.mean(), rsd.max()))
    if len(snr_ok):
        print("  SNR por par: mediana {:.1f} dB | minimo {:.1f} dB".format(
            np.median(snr_ok), snr_ok.min()))
    if len(snr_ok) < len(snr):
        print("  ({} pares com variacao zero entre varreduras: SNR infinito)".format(len(snr) - len(snr_ok)))
    pares = list(tabela.index)
    pior = np.argsort(rsd)[::-1][:5]
    print("  5 pares com maior RSD:", ", ".join(
        "{}-{}: {:.2f}%".format(pares[i][0], pares[i][1], rsd[i]) for i in pior))
    # referencia do artigo, so para comparar
    print("  Referencia do artigo (AD5933): RSD < 0,3% e SNR de 50 a 70 dB")
    # variacao geral da varredura inteira (media dos pares)
    media_por_varredura = Z.mean(axis=0)
    print("  Media de todos os pares, por varredura:",
          ", ".join("{:.1f}".format(v) for v in media_por_varredura), "ohm")
    deriva = 100.0 * (media_por_varredura.max() - media_por_varredura.min()) / media_por_varredura.mean()
    print("  Diferenca entre varreduras (deriva geral): {:.2f}%".format(deriva))
