"""LiverScan - COMPARA padroes de injecao: ADJACENTE (i, i+1) x SALTO (i, i+k).

Objetivo: ver se injetar corrente em eletrodos mais afastados da leituras com |Z| maior,
menos ruido relativo e imagem melhor, com a MESMA batata no MESMO lugar.

Uso:
  python comparar_padroes.py                     (salto de 4, 800 mV, 3 varreduras de baseline e 3 com a batata)
  python comparar_padroes.py --salto=5           (outro salto)
  python comparar_padroes.py --nome=batata_meio  (nome usado nos arquivos salvos)

Roteiro (o programa pede Enter nos momentos certos):
  1) tanque SEM objeto: mede o baseline de cada padrao
  2) voce coloca a batata no meio e aperta Enter: mede cada padrao de novo
Total: ~4 minutos. Nao mexa na batata nem nos fios durante as medidas.
Arquivos: ~/Documents/liverscan_dados/AAAA-MM-DD/ (CSV com todas as leituras, resumo e PNG).
"""
import cmath, datetime, glob, math, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyeit.mesh as mesh_mod
import pyeit.eit.jac as jac
from pyeit.eit.protocol import PyEITProtocol
from pyeit.eit.interp2d import sim2pts

N = 16
DADOS = Path.home() / "Documents" / "liverscan_dados"
amplitude = 800
salto = 4
nbase = 3
nobj = 3
nome = "batata_meio"
simulado = False
for a in sys.argv[1:]:
    if a.startswith("--salto="):
        salto = int(a.split("=", 1)[1])
    elif a.startswith("--nbase="):
        nbase = max(2, int(a.split("=", 1)[1]))
    elif a.startswith("--nobj="):
        nobj = max(2, int(a.split("=", 1)[1]))
    elif a.startswith("--mv="):
        amplitude = int(a.split("=", 1)[1])
    elif a.startswith("--nome="):
        nome = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in a.split("=", 1)[1]) or "teste"
    elif a == "--simulado":
        simulado = True   # so para testar o programa sem a placa

SESSAO = DADOS / datetime.date.today().isoformat()
SESSAO.mkdir(parents=True, exist_ok=True)
TS = datetime.datetime.now().strftime("%H%M%S")


def montar_plano(k):
    """Injecao em (a, a+k); leitura nos pares adjacentes que nao tocam os eletrodos de injecao."""
    plano = []
    for a in range(N):
        b = (a + k) % N
        for s in range(N):
            sp, sm = s, (s + 1) % N
            if sp in (a, b) or sm in (a, b):
                continue
            plano.append((a, b, sp, sm))
    return plano


malha = mesh_mod.create(N, h0=0.05)


def montar_eit(plano):
    ex = np.array([[p[0], p[1]] for p in plano])
    me = np.array([[p[2], p[3]] for p in plano]).reshape(-1, 1, 2)
    proto = PyEITProtocol(ex_mat=ex, meas_mat=me, keep_ba=np.ones((len(ex), 1), dtype=bool))
    e = jac.JAC(malha, proto)
    e.setup(p=0.5, lamb=0.4, method="kotre", perm=1, jac_normalized=True)
    return e


def conectar():
    import adi
    portas = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not portas:
        raise RuntimeError("sem porta usbmodem")
    ultimo = None
    for _ in range(5):
        try:
            c = adi.cn0565(uri="serial:" + portas[0] + ",230400,8n1n")
            c.gpio1_toggle = True
            c.excitation_amplitude = amplitude
            c.excitation_frequency = 10000
            c.magnitude_mode = False
            c.impedance_mode = True
            c.add(0x71)
            c.add(0x70)
            c.immediate = True
            return c
        except Exception as e:
            ultimo = e
            time.sleep(2)
    raise RuntimeError(f"nao conectou: {ultimo}")


_rng = np.random.default_rng(0)


def medir(c, plano, com_objeto=False):
    mags = np.zeros(len(plano))
    linhas = []
    for k, (a, b, sp, sm) in enumerate(plano):
        if c is None:   # simulado
            d = min((a - b) % N, (b - a) % N)
            z0 = 80 + 25 * ((a * 7 + sp * 3) % 11) + 20 * d
            mag = z0 * (1.06 if (com_objeto and sp in (6, 7, 8, 9)) else 1.0) + _rng.normal(0, 2.0)
            z = complex(mag, 0)
        else:
            c.gpio1_toggle = True
            c[a][0] = True
            c[a][1] = True
            c[b][2] = True
            c[b][3] = True
            c[sp][6] = True
            c[sm][7] = True
            z = c.channel["voltage0"].raw
            mag = abs(z)
        fase = cmath.phase(z)
        mags[k] = mag
        linhas.append([k + 1, a, b, sp, sm, z.real, z.imag, mag, math.degrees(fase)])
    if np.ptp(mags) < 1.0:
        raise RuntimeError("todas as leituras iguais: a placa travou")
    return mags, linhas


COLS = ["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag", "magnitude", "phase_deg"]
padroes = [("adjacente", 1), (f"salto{salto}", salto)]
planos = {nm: montar_plano(k) for nm, k in padroes}
for nm, _ in padroes:
    print(f"Padrao {nm}: {len(planos[nm])} leituras por varredura")
print(f"{amplitude} mV | {nbase} varreduras de baseline + {nobj} com a batata, por padrao | pasta {SESSAO}")

cn = None if simulado else conectar()
dados = {"base": {nm: [] for nm, _ in padroes}, "obj": {nm: [] for nm, _ in padroes}}


def rodar_fase(fase, n, com_objeto):
    for nm, _ in padroes:
        for i in range(n):
            t0 = time.time()
            m, l = medir(cn, planos[nm], com_objeto)
            dados[fase][nm].append((m, l))
            print(f"  {fase} {nm}: varredura {i + 1}/{n} ({time.time() - t0:.0f} s)", flush=True)
        linhas_tab = []
        for i, (_, l) in enumerate(dados[fase][nm]):
            linhas_tab += [[i + 1] + x for x in l]
        pd.DataFrame(linhas_tab, columns=["varredura"] + COLS).to_csv(
            SESSAO / f"{TS}_{nome}_{fase}_{nm}.csv", index=False)


try:
    input("\nTANQUE SEM OBJETO, nao mexa em nada. Aperte Enter para medir o baseline... ")
    rodar_fase("base", nbase, False)
    input("\nBaseline pronto. COLOQUE A BATATA NO MEIO e aperte Enter... ")
    rodar_fase("obj", nobj, True)
except Exception as e:
    print(f"\nFALHA durante a medicao: {e}")
    print("Faca o ciclo de energia da placa (USB fora 30 s) e rode de novo.")
    sys.exit(1)

# ---------- analise ----------
resumo = []
imagens = {}
for nm, _ in padroes:
    pl = planos[nm]
    b = np.array([m for m, _ in dados["base"][nm]])
    o = np.array([m for m, _ in dados["obj"][nm]])
    v0 = b.mean(0)
    vo = o.mean(0)
    delta = (vo - v0) / v0 * 100                       # mudanca por leitura (%)
    sd_b = b.std(0, ddof=1) / v0 * 100
    sd_o = o.std(0, ddof=1) / v0 * 100
    sd_pool = np.sqrt((sd_b ** 2 + sd_o ** 2) / 2)
    sig = sd_pool * math.sqrt(1 / len(b) + 1 / len(o))  # ruido esperado da diferenca das medias (%)
    razao = math.sqrt(np.mean(delta ** 2)) / max(math.sqrt(np.mean(sig ** 2)), 1e-12)
    # imagem
    eit = montar_eit(pl)
    sg = np.sign(eit.v0.real)   # sinal que o modelo espera em cada leitura (o |Z| perde o sinal)
    picos = []
    for m in b:
        zz = sim2pts(malha.node, malha.element, np.real(eit.solve(m * sg, v0 * sg, normalize=True)))
        picos.append(float(np.max(np.abs(zz))))
    nb = len(b)
    ruido = float(np.mean(picos)) * math.sqrt(nb / (nb - 1)) * math.sqrt(1 + 1 / nb)
    z = sim2pts(malha.node, malha.element, np.real(eit.solve(vo * sg, v0 * sg, normalize=True)))
    pico = float(np.max(np.abs(z)))
    i = int(np.argmax(np.abs(z)))
    x, y = malha.node[i][:2]
    imagens[nm] = (z, pico, ruido)
    resumo.append(dict(
        padrao=nm, leituras=len(pl), z_mediana_ohm=round(float(np.median(v0))),
        ruido_mediano_pct=round(float(np.median(sd_b)), 2),
        mudanca_mediana_pct=round(float(np.median(np.abs(delta))), 2),
        razao_sinal_ruido_leituras=round(razao, 1),
        sinal_ruido_imagem=round(pico / ruido, 1),
        pico_dist_centro_raios=round(math.hypot(x, y), 2),
        pico_x=round(float(x), 2), pico_y=round(float(y), 2)))

res = pd.DataFrame(resumo)
print("\n================ RESULTADO ================")
print(res.T.to_string(header=False))
res.insert(0, "hora", TS)
res.insert(1, "nome", nome)
res.insert(2, "mV", amplitude)
arq = SESSAO / "comparacao_padroes.csv"
res.to_csv(arq, mode="a", header=not arq.exists(), index=False)

fig, axs = plt.subplots(1, 2, figsize=(11, 5.5))
for ax, (nm, _) in zip(axs, padroes):
    z, pico, ruido = imagens[nm]
    lim = max(pico, 2 * ruido, 1e-9)
    ax.tripcolor(malha.node[:, 0], malha.node[:, 1], malha.element, z, shading="flat",
                 cmap="RdBu_r", vmin=-lim, vmax=lim)
    for e in range(N):
        ex_, ey_ = malha.node[malha.el_pos[e]][:2]
        ax.plot(ex_, ey_, "ko", ms=4)
        ax.annotate(str(e), (ex_ * 1.12, ey_ * 1.12), ha="center", va="center", fontsize=8)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{nm}: sinal/ruido da imagem {pico / ruido:.1f}\nvermelho = mais condutivo | azul = menos condutivo", fontsize=10)
fig.tight_layout()
png = SESSAO / f"{TS}_{nome}_comparacao_padroes.png"
fig.savefig(png, dpi=150)
print(f"\nSalvo: {png.name}, {arq.name} e os CSVs de cada padrao em {SESSAO}")
plt.show()
