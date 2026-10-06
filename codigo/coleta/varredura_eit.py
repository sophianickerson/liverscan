"""
LiverScan - Varredura completa dos 16 eletrodos (120 pares).

Uso:   python varredura_eit.py NOME_DA_MEDICAO
Ex.:   python varredura_eit.py baseline1

Cada par e gravado no CSV assim que e medido, entao uma falha no meio
nao perde o que ja foi medido. Os arquivos ficam em
~/Documents/liverscan_dados/
"""
import cmath
import csv
import glob
import os
import sys
import time
from datetime import datetime

import adi

AMPLITUDE = 100  # mV
FREQUENCY = 10000  # Hz
N_ELECTRODES = 16
MAX_RETRIES = 3  # tentativas por par
MAX_CONSECUTIVE_FAILS = 5  # aborta se falharem tantos pares seguidos
DATA_DIR = os.path.expanduser("~/Documents/liverscan_dados")


def find_port():
    ports = glob.glob("/dev/cu.usbmodem*")
    if len(ports) != 1:
        sys.exit(
            "Esperava exatamente 1 porta usbmodem, achei "
            + str(len(ports))
            + ": "
            + str(ports)
        )
    return ports[0]


def measure(cn0565, pos_e, neg_e):
    """Mede a impedancia entre dois eletrodos (mesma configuracao do exemplo da ADI)."""
    cn0565.open_all()
    cn0565[pos_e][0] = True
    cn0565[pos_e][1] = True
    cn0565[neg_e][2] = True
    cn0565[neg_e][3] = True
    return cn0565.channel["voltage0"].raw


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python varredura_eit.py NOME_DA_MEDICAO   (ex.: baseline1)")

    label = sys.argv[1]
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        DATA_DIR,
        f"{label}_{FREQUENCY // 1000}kHz_{AMPLITUDE}mV_{stamp}.csv",
    )

    port = find_port()
    print("Porta encontrada:", port)
    cn0565 = adi.cn0565(uri=f"serial:{port},230400,8n1n")

    cn0565.gpio1_toggle = True
    cn0565.excitation_amplitude = AMPLITUDE
    cn0565.excitation_frequency = FREQUENCY
    cn0565.magnitude_mode = False
    cn0565.impedance_mode = True
    cn0565.immediate = True
    cn0565.add(0x71)
    cn0565.add(0x70)

    total = N_ELECTRODES * (N_ELECTRODES - 1) // 2
    print(f"Medindo {total} pares a {FREQUENCY} Hz, {AMPLITUDE} mV")
    print("Arquivo:", filename)

    start = time.time()
    done = 0
    failed = 0
    consecutive_fails = 0
    aborted = False

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["pair", "e_pos", "e_neg", "real", "imag", "magnitude", "phase_deg"]
        )

        pair = 0
        for neg_e in range(1, N_ELECTRODES):
            for pos_e in range(0, neg_e):
                pair += 1
                res = None
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        res = measure(cn0565, pos_e, neg_e)
                        break
                    except Exception as e:
                        print(
                            f"  par {pos_e}-{neg_e}: tentativa {attempt} falhou ({e})"
                        )
                        time.sleep(1)

                if res is None:
                    failed += 1
                    consecutive_fails += 1
                    writer.writerow([pair, pos_e, neg_e, "", "", "", ""])
                    f.flush()
                    if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                        print("Muitas falhas seguidas, abortando.")
                        aborted = True
                        break
                    continue

                consecutive_fails = 0
                mag, radph = cmath.polar(res)
                writer.writerow(
                    [pair, pos_e, neg_e, res.real, res.imag, mag, radph * 180 / cmath.pi]
                )
                f.flush()
                done += 1

                if pair % 10 == 0:
                    print(f"  {pair}/{total} pares ({time.time() - start:.0f} s)")
            if aborted:
                break

    elapsed = time.time() - start
    print("--------------------------------------------------------------")
    print(f"Pares medidos: {done}/{total}   Falhas: {failed}   Tempo: {elapsed:.0f} s")
    print("Arquivo salvo em:", filename)
    if aborted or failed:
        print("ATENCAO: medicao incompleta. Nao use este arquivo como linha de base.")
    else:
        print("Medicao completa.")


main()
