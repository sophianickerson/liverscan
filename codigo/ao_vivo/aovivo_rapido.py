"""LiverScan AO VIVO RAPIDO - 4 fios, uma conexao so, 800 mV, reconstrucao JAC.

Uso:
  python aovivo_rapido.py                         (tira o PROPRIO baseline na partida: tanque VAZIO!)
  python aovivo_rapido.py --nbase=5               (baseline = media de 5 varreduras; padrao 3)
  python aovivo_rapido.py --base=ARQUIVO.csv      (usa um baseline salvo, em ~/Documents/liverscan_dados)
  python aovivo_rapido.py --inj=13                (so as injecoes 0 a 12; padrao 16 injecoes = 208 leituras)
  python aovivo_rapido.py --salto=4               (injecao em i e i+4; padrao 1 = adjacente. Salto 4 foi bem melhor nos testes de 31/10)
  python aovivo_rapido.py --nome=saquinho_sal      (nome do teste, usado nos arquivos salvos com a tecla s)
  python aovivo_rapido.py --mv=800 --suave=0.5    (suave: 0 = so o quadro atual; 0.5 = mistura 50% do anterior)

Cada quadro: 208 leituras (16 injecoes) numa conexao que fica aberta, ~18 s por quadro.
No grafico: tecla b = re-tira o baseline (tanque como esta agora).
tecla s = SALVA o proximo quadro (PNG + CSV + o baseline vigente NOME_base.csv + linha no registro.csv) na pasta da sessao.
Control + C no Terminal = sair. Ultimo quadro: ~/Documents/liverscan_dados/aovivo_rapido_ultimo.csv
Requer o firmware CORRIGIDO (sem o vazamento de memoria) - com o original trava na leitura ~181.
"""
import cmath, datetime, glob, math, os, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyeit.mesh as mesh_mod
import pyeit.eit.jac as jac
from pyeit.eit.protocol import PyEITProtocol
from pyeit.eit.interp2d import sim2pts
import adi

N = 16
DADOS = Path.home() / "Documents" / "liverscan_dados"
amplitude = 800
suave = 0.0
nome = "teste"
salto = 1
base_path = None
escala = None  # se definida (--escala=X), todas as imagens usam a mesma escala de cor fixa
nbase = 3
n_inj = 16
for a in sys.argv[1:]:
    if a.startswith("--nbase="):
        nbase = max(1, int(a.split("=", 1)[1]))
    elif a.startswith("--inj="):
        n_inj = int(a.split("=", 1)[1])
    elif a.startswith("--base="):
        p = Path(os.path.expanduser(a.split("=", 1)[1]))
        base_path = p if p.is_absolute() else DADOS / p
    elif a.startswith("--mv="):
        amplitude = int(a.split("=", 1)[1])
    elif a.startswith("--suave="):
        suave = float(a.split("=", 1)[1])
    elif a.startswith("--salto="):
        salto = int(a.split("=", 1)[1])
    elif a.startswith("--escala="):
        escala = float(a.split("=", 1)[1])
    elif a.startswith("--nome="):
        nome = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in a.split("=", 1)[1]) or "teste"

if base_path is not None:
    d_base = pd.read_csv(base_path).sort_values(["inj_pos", "s_pos"]).reset_index(drop=True)
    plano = list(zip(d_base.inj_pos, d_base.inj_neg, d_base.s_pos, d_base.s_neg))
    v0 = d_base.magnitude.values.astype(float)
    print(f"Baseline do arquivo: {base_path.name} ({len(d_base)} leituras) | {amplitude} mV | suave={suave}")
else:
    plano = []
    for a in range(n_inj):
        b = (a + salto) % N
        for s_ in range(N):
            sp, sm = s_, (s_ + 1) % N
            if sp in (a, b) or sm in (a, b):
                continue
            plano.append((a, b, sp, sm))
    v0 = None
    d_base = pd.DataFrame(plano, columns=["inj_pos", "inj_neg", "s_pos", "s_neg"])
    print(f"Baseline proprio na partida (media de {nbase} varreduras) | injecao i e i+{salto} | {len(plano)} leituras | {amplitude} mV | suave={suave}")

ex_mat = d_base[["inj_pos", "inj_neg"]].values.astype(int)
meas_mat = d_base[["s_pos", "s_neg"]].values.astype(int).reshape(-1, 1, 2)
proto = PyEITProtocol(ex_mat=ex_mat, meas_mat=meas_mat, keep_ba=np.ones((len(ex_mat), 1), dtype=bool))
malha = mesh_mod.create(N, h0=0.05)
eit = jac.JAC(malha, proto)
eit.setup(p=0.5, lamb=0.4, method="kotre", perm=1, jac_normalized=True)
sinal = np.sign(eit.v0.real)   # sinal que o modelo espera em cada leitura (|Z| perde o sinal); cores: vermelho = mais condutivo, azul = menos
angs = [np.degrees(np.arctan2(malha.node[malha.el_pos[e]][1], malha.node[malha.el_pos[e]][0])) for e in range(N)]


def conectar():
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


def medir(c):
    mags = np.zeros(len(plano))
    linhas = []
    for k, (a, b, sp, sm) in enumerate(plano):
        c.gpio1_toggle = True
        c[a][0] = True
        c[a][1] = True
        c[b][2] = True
        c[b][3] = True
        c[sp][6] = True
        c[sm][7] = True
        z = c.channel["voltage0"].raw
        mag, fase = cmath.polar(z)
        mags[k] = mag
        linhas.append([k + 1, a, b, sp, sm, z.real, z.imag, mag, math.degrees(fase)])
    return mags, linhas


if salto != 1 and base_path is None:
    nome = f"{nome}_s{salto}"
SESSAO = DADOS / datetime.date.today().isoformat()
SESSAO.mkdir(parents=True, exist_ok=True)
plt.rcParams["keymap.save"] = []   # libera a tecla s (antes abria a janela de salvar)
plt.ion()
fig, ax = plt.subplots(figsize=(6.5, 6.5))
fig.canvas.manager.set_window_title("LiverScan ao vivo (rapido)")
rebase = {"pedido": False}
salvar = {"pedido": False}
ultimo = {"linhas": None, "snr": None, "prox": None, "var": None, "lamb": 0.4}


def on_key(ev):
    if ev.key == "b":
        rebase["pedido"] = True
        print("  [tecla b: o proximo quadro vira o novo baseline]")
    elif ev.key == "s":
        salvar["pedido"] = True
        print("  [tecla s: vou salvar o quadro atual]")


fig.canvas.mpl_connect("key_press_event", on_key)

print("Conectando...")
cn = conectar()
def tirar_baseline():
    """Mede nbase varreduras. Devolve (baseline medio, nivel de ruido da imagem).
    O nivel de ruido = pico tipico da imagem que o proprio ruido produz (varredura vs media)."""
    acc = []
    for k in range(nbase):
        m, _ = medir(cn)
        acc.append(m)
        print(f"    baseline: varredura {k + 1}/{nbase}", flush=True)
    media = np.mean(acc, axis=0)
    if nbase < 2:
        return media, None
    picos = []
    for m in acc:
        zz = sim2pts(malha.node, malha.element, np.real(eit.solve(m * sinal, media * sinal, normalize=True)))
        picos.append(float(np.max(np.abs(zz))))
    # corrige o vies de comparar cada varredura com a media que a inclui
    ruido = float(np.mean(picos)) * math.sqrt(nbase / (nbase - 1)) * math.sqrt(1 + 1 / nbase)
    print(f"    nivel de ruido da imagem: {ruido:.3g}")
    return media, ruido


ruido = None
if v0 is None:
    print("TANQUE VAZIO? Tirando o baseline agora (nao mexa em nada)...")
    v0, ruido = tirar_baseline()
    print("Baseline pronto. Agora coloque o objeto e observe.")
    _bn = SESSAO / f"{datetime.datetime.now().strftime('%H%M%S')}_baseline_{nome}_{amplitude}mV.csv"
    pd.DataFrame({"inj_pos": d_base.inj_pos, "inj_neg": d_base.inj_neg, "s_pos": d_base.s_pos,
                  "s_neg": d_base.s_neg, "magnitude": v0}).to_csv(_bn, index=False)
    print(f"    baseline salvo em {SESSAO.name}/{_bn.name}")
print(f"Quadros de ~18 s. Tecla s = salvar o quadro | tecla b = novo baseline | Control + C = sair. Pasta: {SESSAO}")
quadro = 0
anterior = None
falhas = 0
try:
    while True:
        t0 = time.time()
        try:
            mags, linhas = medir(cn)
            falhas = 0
        except Exception as e:
            falhas += 1
            print(f"  [falha na medicao ({e.__class__.__name__}); tentativa {falhas}/3 de reconectar]")
            if falhas >= 3:
                print("  Placa nao responde. Faca o ciclo de energia (USB fora 30 s) e rode de novo.")
                break
            time.sleep(5)
            try:
                cn = conectar()
            except Exception as e2:
                print("  nao reconectou:", e2)
            continue

        if np.ptp(mags) < 1.0:
            print("  ATENCAO: todas as leituras iguais; a placa travou. Ciclo de energia e rode de novo.")
            break
        pd.DataFrame(linhas, columns=["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag",
                                      "magnitude", "phase_deg"]).to_csv(DADOS / "aovivo_rapido_ultimo.csv", index=False)

        if rebase["pedido"]:
            print("  [re-tirando o baseline: tanque vazio, nao mexa em nada]")
            ax.clear()
            ax.set_title("tirando novo baseline...\nnao mexa em nada")
            fig.canvas.draw_idle(); plt.pause(0.1)
            v0, ruido = tirar_baseline()
            anterior = None
            rebase["pedido"] = False
            print("  [novo baseline capturado]")
            ax.set_title("novo baseline capturado\ncoloque o objeto e observe")
            fig.canvas.draw_idle(); plt.pause(0.1)
            continue

        v = mags if (suave <= 0 or anterior is None) else suave * anterior + (1 - suave) * mags
        anterior = v
        ds = eit.solve(v * sinal, v0 * sinal, normalize=True)
        z = sim2pts(malha.node, malha.element, np.real(ds))
        i = int(np.argmax(np.abs(z)))
        ang = np.degrees(np.arctan2(malha.node[i][1], malha.node[i][0]))
        prox = int(np.argmin([abs((ang - g + 180) % 360 - 180) for g in angs]))
        pico = float(np.max(np.abs(z)))
        lim = max(pico, 2.0 * ruido, 1e-9) if ruido else max(pico, 1e-9)
        snr = pico / ruido if ruido else None
        if escala is not None:
            lim = escala

        quadro += 1
        ax.clear()
        ax.tripcolor(malha.node[:, 0], malha.node[:, 1], malha.element, z,
                     shading="flat", cmap="RdBu_r", vmin=-lim, vmax=lim)
        for e in range(N):
            x, y = malha.node[malha.el_pos[e]][:2]
            ax.plot(x, y, "ko", ms=4)
            ax.annotate(str(e), (x * 1.12, y * 1.12), ha="center", va="center", fontsize=9)
        ax.set_aspect("equal"); ax.set_axis_off()
        var = 100 * np.median(np.abs(v - v0) / v0)
        if snr is None:
            info = f"quadro {quadro} | maior variacao: eletrodo {prox}"
        elif snr < 1.5:
            info = f"quadro {quadro} | sem objeto detectavel (sinal/ruido {snr:.1f})"
        else:
            info = f"quadro {quadro} | objeto perto do eletrodo {prox} (sinal/ruido {snr:.1f})"
        ax.set_title(info + f"\nmudanca mediana: {var:.1f}% | pico: {pico:.3g}" + (f" | escala fixa +-{escala:g}" if escala is not None else "") + " | b = novo baseline")
        ax.text(0.5, 0.0, "vermelho = mais condutivo | azul = menos condutivo", transform=ax.transAxes, ha="center", fontsize=9)
        fig.canvas.draw_idle(); plt.pause(0.1)
        ultimo.update(linhas=linhas, snr=snr, prox=prox, var=var)
        if salvar["pedido"]:
            salvar["pedido"] = False
            ts = datetime.datetime.now().strftime("%H%M%S")
            base_nome = f"{ts}_{nome}_q{quadro}"
            fig.savefig(SESSAO / (base_nome + ".png"), dpi=150)
            pd.DataFrame(linhas, columns=["seq", "inj_pos", "inj_neg", "s_pos", "s_neg", "real", "imag",
                                          "magnitude", "phase_deg"]).to_csv(SESSAO / (base_nome + ".csv"), index=False)
            pd.DataFrame({"inj_pos": [x[0] for x in plano], "inj_neg": [x[1] for x in plano],
                          "s_pos": [x[2] for x in plano], "s_neg": [x[3] for x in plano],
                          "magnitude": v0}).to_csv(SESSAO / (base_nome + "_base.csv"), index=False)   # baseline vigente neste quadro
            reg = SESSAO / "registro.csv"
            nova = not reg.exists()
            with open(reg, "a", encoding="utf-8") as f:
                if nova:
                    f.write("hora,nome,quadro,mV,lambda,nbase,sinal_ruido,eletrodo_proximo,mudanca_mediana_pct,arquivo\n")
                f.write(f"{ts},{nome},{quadro},{amplitude},0.4,{nbase},"
                        f"{'' if snr is None else round(snr, 1)},{prox},{var:.1f},{base_nome}\n")
            print(f"  [SALVO em {SESSAO.name}/{base_nome}.png e .csv + registro.csv]")
        print(f"  quadro {quadro}: eletrodo {prox} | sinal/ruido {snr if snr is None else round(snr, 1)} | "
              f"mudanca mediana {var:.1f}% | {time.time()-t0:.0f} s")
except KeyboardInterrupt:
    pass
print("Encerrado.")
