# LiverScan

Tomógrafo de impedância elétrica (EIT) de baixo custo, em desenvolvimento, para investigar se é possível enxergar gordura no fígado.

**Estado atual:** pesquisa em andamento, em bancada. O dispositivo **ainda não mede gordura**. O que existe é uma cadeia de medição funcionando (hardware, firmware corrigido, coleta, imagem em tempo real) e um tanque de teste com água salgada. Nada é testado em pessoas.

Projeto de Sophia Nickerson, com Fellipe Godoy na execução e no registro de parte das sessões de bancada. Os scripts deste repositório foram escritos por Sophia com assistência do Claude (Anthropic).

## O que já foi feito

| Data | Marco |
|---|---|
| 18/09/2026 | Primeira leitura de impedância pela placa de teste P2 (Fellipe Godoy): 43.282,3 Ω, fase 0,97°, par de eletrodos 0 e 1, 10 kHz, 100 mV. |
| 21/09/2026 | Mesma leitura reproduzida em outra estação de trabalho (Sophia Nickerson): 43.239,7 Ω, fase 0,96°. As leituras ficam dentro de 0,15% entre si. |
| 29/09/2026 | Tanque de 16 eletrodos montado, mapeamento do conector P1 deduzido do esquemático e confirmado com um resistor de 1 kΩ (992,1 Ω). Primeira imagem de diferença: objeto isolante localizado no eletrodo 11. |
| 30–31/10/2026 | Causa das travas da placa (~180 leituras) achada e corrigida no firmware (1 byte): 400 de 400 leituras OK. Medição passou para **4 fios**. |
| 31/10/2026 | **800 mV** (em vez de 300 mV) triplica a resolução das leituras; padrão de injeção **salto 4** melhora o sinal/ruído 3 a 4×; imagem em **tempo real** (~15–18 s por quadro); batata localizada no eletrodo certo em 3 posições. |
| 02/11/2026 | Gelatinas com 0 a 30% de óleo ficam ordenadas na imagem com escala de cor fixa (qualitativo; ainda não é % de gordura). |

**Limites:** as imagens são qualitativas. Só foram testados objetos de batata e gelatina no tanque; o modelo não conhece a impedância de contato dos eletrodos; a conversão de impedância para % de gordura ainda não existe (exige calibração com gelatinas de sal conhecido). Detalhes em [`docs/parametros_e_resultados_4fios.md`](docs/parametros_e_resultados_4fios.md).

## Hardware

- Analog Devices **EVAL-ADICUP3029** (processador) + **EVAL-CN0565-ARDZ** (bioimpedância: AD5940 e crosspoints ADG2128). Firmware `cn0565.hex` e documentação oficiais da Analog Devices; usamos uma versão com 1 byte corrigido (veja `firmware/`).
- Tanque: pote de 23,8 cm de diâmetro interno, 16 parafusos de inox como eletrodos, centros a 3 cm do fundo, igualmente espaçados, vedados por fora.
- Computador: Mac, ligado à placa por USB. (A gravação do firmware, quando o disco DAPLINK falha, foi feita no Windows.)

### Mapeamento do conector P1 (índice do software e pino físico)

A documentação pública da Analog Devices não traz esse mapeamento. Ele foi deduzido do esquemático oficial (EVAL-CN0565-ARDZ rev. B) e confirmado com um resistor de 1 kΩ nos pinos 3 e 4 (índices 12 e 13). O restante segue o esquemático.

| Eletrodo (índice) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pino do P1 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 3 | 4 | 5 | 6 |

Os pinos 1, 2, 29 e 30 são terra, e os pinos 13 a 16 não são conectados.

## Rodar em outro computador (macOS)

1. **libiio nativo:** instale o arquivo `.pkg` da página de releases do libiio (GitHub da Analog Devices).
2. **Python e bibliotecas:**
   ```bash
   python3 -m venv liverscan
   source liverscan/bin/activate
   pip install -r requirements.txt
   ```
3. **Firmware corrigido:** siga [`firmware/README.md`](firmware/README.md). Não grave pelo disco DAPLINK; isso já corrompeu a memória da nossa placa.
4. **Conferir a placa** (a placa precisa estar ligada por USB; os scripts acham a porta `/dev/cu.usbmodem*` sozinhos):
   ```bash
   python codigo/diagnostico/teste_serial_cru.py     # a placa responde?
   python codigo/diagnostico/teste_vazamento.py      # 400 leituras sem travar?
   ```
5. **Primeira imagem ao vivo** (tanque vazio no começo, ele tira o baseline sozinho):
   ```bash
   python codigo/ao_vivo/aovivo_rapido.py --salto=4 --escala=0.5 --nome=primeiro_teste
   ```
   Tecla `b` = novo baseline, tecla `s` = salvar o próximo quadro, Ctrl+C = sair.

Se a placa ficar muda, confira primeiro fios e encaixe do shield (veja `docs/firmware_vazamento_memoria.md`).

## Scripts

Os scripts leem e gravam em `~/Documents/liverscan_dados/` (medições, baselines e quadros salvos).

| Pasta | Script | Para quê |
|---|---|---|
| `codigo/ao_vivo/` | **`aovivo_rapido.py`** | Imagem em tempo real, 4 fios, 800 mV, uma conexão aberta. **O principal.** Opções: `--salto`, `--escala`, `--nbase`, `--base`, `--mv`, `--suave`, `--inj`, `--nome` (veja o topo do arquivo). |
| `codigo/coleta/` | `varredura_4fios_rapida.py` | Uma varredura de 4 fios gravada em CSV: `python varredura_4fios_rapida.py NOME [mV]`. |
| | `varredura_eit.py` | Varredura de 2 fios, 120 pares, 100 mV (fase de setembro). |
| `codigo/analise/` | `baseline_medio.py` | Baseline médio de N varreduras do tanque vazio, com desvio por leitura: `python baseline_medio.py 5 800`. |
| | `comparar_padroes.py` | Compara injeção adjacente com salto K na mesma sessão. |
| | `metricas_varreduras.py` | Métricas de ruído do tanque vazio. |
| | `checar_varreduras.py`, `media_v1_v5.py`, `media_vazio.py` | Conferência e médias das varreduras de 2 fios (setembro). |
| `codigo/imagem/` | `foto_4fios.py` (+ `varredura_4fios_chunk.py`) | Uma varredura = uma imagem (modo foto), sem loop. **Usa a convenção de cor antiga.** |
| | `liverscan_imagem_*.py` | Imagens de diferença da fase de 2 fios (setembro); nomes de arquivo fixos no código, servem como exemplo. |
| `codigo/diagnostico/` | `teste_serial_cru.py`, `teste_vazamento.py` | Checar se a placa responde e se o firmware não trava. |

**Convenção de cor atual (`aovivo_rapido.py` e `comparar_padroes.py`): vermelho = mais condutivo que a água, azul = menos condutivo.** Os scripts de `codigo/imagem/` usam a convenção invertida. Veja `docs/parametros_e_resultados_4fios.md`.

## Formato dos dados

Cada medição é um CSV com as colunas `pair, e_pos, e_neg, real, imag, magnitude, phase_deg`, nomeado `NOME_10kHz_100mV_AAAAMMDD_HHMMSS.csv`. A ordem dos pares é fixa: para o eletrodo negativo de 1 a 15, o positivo de 0 até o anterior.

## Documentação

- `docs/parametros_e_resultados_4fios.md`: parâmetros atuais (800 mV, salto 4), tempo real, convenção de cor, resultados e próximos passos.
- `docs/firmware_vazamento_memoria.md`: causa e correção do travamento da placa.
- `docs/guia_primeiro_teste_eit.md`: guia do primeiro teste (tanque de salmoura, validação com resistor e com batata).

## Licença

MIT. Veja `LICENSE`.
