# Firmware: vazamento de memória que travava a placa (29–31/out/2026)

## Causa
Na função `AD5940_FIFORd_Fast` (`drivers/afe/ad5940/ad5940.c`, repositório `analogdevicesinc/no-OS`), toda leitura de 4 ou mais valores faz um `malloc` de ~32 bytes e nunca libera, porque a variável `iobuf_alloc_sz` nunca recebe valor (fica sempre 0, então o ramo do `malloc` sempre roda).

O modo impedância lê exatamente 4 valores por medição, então vaza a cada leitura. O modo tensão lê 2 valores (caminho lento, sem alocação) e não vaza. Quando a memória do ADuCM3029 acaba, a placa para de responder e o Python dá timeout ("sp_blocking_read_next has timedout", depois "No device found").

## Evidência
- Firmware original, receita de 4 fios fixa, 400 leituras: 181 OK e travou na 182, com tempo por leitura constante (0,057 s). Reconectar não ajuda (a memória é da placa); só religar a alimentação.
- Confirmado no código de máquina do `cn0565.hex` oficial (MD5 `74e327dc...`): a função está em `0xFBC` e o desvio `bne 0xFFC` em `0xFDE` nunca pula o `malloc`.
- Firmware corrigido (31/out): `codigo/diagnostico/teste_vazamento.py` → **400 de 400 leituras OK em 23 s**, tempo por leitura constante em 0,057 s.

## Correção (1 byte)
Endereço `0xFDE`, `0D D1` (bne) → `0D E0` (b incondicional). O `realloc(NULL, n)` seguinte faz a alocação uma única vez e reusa o bloco. Use `firmware/gerar_firmware_corrigido.py`.

## Outras observações (não corrigidas)
- `iio_ad5940.c` espera só 100 ms pelo dado do AD5940, apertado no modo impedância (~90 ms); estourar devolve `-ETIMEDOUT` sem limpar flags/FIFO.
- O retorno de `AppBiaISR` é ignorado: se falhar, o firmware devolve o dado antigo em silêncio.
- Há laços `while` sem limite de tempo esperando o AD5940.
- Medidas: leitura isolada ≈ 0,057 s; ≈ 0,09 s com os comandos das chaves; quadro de 208 leituras ≈ 12–20 s.
- Melhoria possível, uma mudança por vez: reduzir o DFT de 8192 para 2048 pontos (~4× mais rápido, com mais ruído).
- Em 31/out, a 1ª leitura de uma conexão veio 6% abaixo das seguintes (478,7 Ω contra 510,1 Ω). Possível transiente; se repetir, descartar a 1ª leitura.

## Gravação e placa muda
Veja `firmware/README.md`. Resumo: não gravar pelo disco DAPLINK; usar o ccsfp (Windows). Placa muda depois de gravar: conferir fios e encaixe antes de suspeitar do firmware.
