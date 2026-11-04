# Firmware da placa (EVAL-ADICUP3029 + CN0565)

A placa roda o firmware `cn0565.hex` da Analog Devices. **Ele tem um defeito**: um vazamento de memória que faz a placa travar depois de ~180 leituras de impedância (detalhes em [`../docs/firmware_vazamento_memoria.md`](../docs/firmware_vazamento_memoria.md)). Nós usamos uma versão com **1 byte corrigido**.

Este repositório **não inclui o `.hex`** (ele é da Analog Devices). Em vez disso, o script `gerar_firmware_corrigido.py` fabrica o corrigido a partir do original.

## Passo a passo

1. Baixe o `cn0565.hex` original no site da Analog Devices (página do EVAL-CN0565-ARDZ, arquivos de firmware). O MD5 esperado é `74e327dc28081cc6525275f4943c74ac`.
2. Gere o corrigido:
   ```bash
   python gerar_firmware_corrigido.py cn0565.hex cn0565_CORRIGIDO.hex
   ```
   O script confere o MD5 do original e do resultado (`00985d8c620d7a397e690844612fe616`). Se algo não bater, ele para e não escreve nada.
3. Grave `cn0565_CORRIGIDO.hex` na placa (veja o aviso abaixo).
4. Confira que a placa responde e não trava: `codigo/diagnostico/teste_serial_cru.py` e depois `codigo/diagnostico/teste_vazamento.py` (deve fazer 400 de 400 leituras).

## O que o script muda

Endereço `0xFDE`, bytes `0D D1` (desvio condicional `bne`) → `0D E0` (desvio incondicional `b`). Só esse byte (`0xFDF`) difere do original.

## Aviso sobre a gravação

No nosso caso, **gravar pelo disco DAPLINK** (arrastar o arquivo no Finder) **falhou e deixou a memória corrompida** ("transfer timed out"). O que funcionou foi o **CrossCore Serial Flash Programmer (ccsfp)**, no Windows: alvo ADuCM302x, 9600 baud, *Erase* (segurando BOOT/S3 e apertando/soltando RESET/S1) e depois *Program*. Ele não existe para Mac. Tenha sempre esse plano B antes de gravar firmware modificado.

Se a placa ficar muda depois de gravar, confira **primeiro** fios e encaixe do shield. No nosso caso (31/10) a causa foi um fio solto, não o firmware.
