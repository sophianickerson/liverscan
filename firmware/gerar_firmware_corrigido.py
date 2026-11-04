"""Gera o firmware CORRIGIDO a partir do cn0565.hex ORIGINAL da Analog Devices.

Por que existe: o firmware original tem um vazamento de memoria (malloc sem free)
que trava a placa depois de ~180 leituras de impedancia. A correcao muda 1 byte.
Este script faz essa mudanca para voce, sem precisar baixar o arquivo de ninguem.

Uso:
    python gerar_firmware_corrigido.py cn0565.hex cn0565_CORRIGIDO.hex

Ele confere se o arquivo de entrada e mesmo o original (MD5) antes de mexer,
e confere o MD5 do resultado. Nao altera o arquivo de entrada.
"""
import hashlib
import sys

MD5_ORIGINAL = "74e327dc28081cc6525275f4943c74ac"
MD5_CORRIGIDO = "00985d8c620d7a397e690844612fe616"
ENDERECO = 0xFDE            # onde esta o desvio condicional (bne)
ANTES, DEPOIS = "0DD1", "0DE0"   # bne 0xFFC  ->  b 0xFFC (incondicional)


def md5(texto):
    return hashlib.md5(texto.encode("latin-1")).hexdigest()


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    entrada, saida = sys.argv[1], sys.argv[2]
    with open(entrada, "r", newline="", encoding="latin-1") as f:
        texto = f.read()
    if md5(texto) != MD5_ORIGINAL:
        sys.exit("ERRO: este nao e o cn0565.hex original (MD5 diferente). Nada foi feito.")

    linhas = texto.split("\n")
    achou = False
    for i, linha in enumerate(linhas):
        l = linha.rstrip("\r")
        if len(l) < 11 or l[0] != ":" or l[7:9] != "00":
            continue
        n = int(l[1:3], 16)
        base = int(l[3:7], 16)
        if base <= ENDERECO < base + n:  # primeiro segmento (endereco linear alto = 0)
            off = ENDERECO - base
            dados = l[9:9 + 2 * n]
            if dados[2 * off:2 * off + 4] != ANTES:
                continue
            novos = dados[:2 * off] + DEPOIS + dados[2 * off + 4:]
            corpo = l[1:9] + novos
            soma = sum(int(corpo[k:k + 2], 16) for k in range(0, len(corpo), 2))
            cks = (-soma) & 0xFF
            fim = linha[len(l):]  # preserva o fim de linha original
            linhas[i] = ":" + corpo + "%02X" % cks + fim
            achou = True
            break
    if not achou:
        sys.exit("ERRO: nao achei o trecho a corrigir. Nada foi feito.")

    novo = "\n".join(linhas)
    if md5(novo) != MD5_CORRIGIDO:
        sys.exit("ERRO: o resultado nao bate com o firmware corrigido validado. Nada foi gravado.")
    with open(saida, "w", newline="", encoding="latin-1") as f:
        f.write(novo)
    print("OK. Gerado:", saida, "(MD5", MD5_CORRIGIDO + ")")


main()
