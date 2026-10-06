# LiverScan

Tomógrafo de impedância elétrica (EIT) de baixo custo, em desenvolvimento, para investigar se é possível enxergar gordura no fígado.

**Estado atual:** pesquisa em andamento, em bancada. O dispositivo **ainda não mede gordura**. O que existe hoje é uma cadeia de medição funcionando (hardware, firmware, coleta e reconstrução de imagem) e um tanque de teste com água salgada. Nada é testado em pessoas.

Projeto de Sophia Nickerson, com Fellipe Godoy na execução e no registro de parte das sessões de bancada. Os scripts deste repositório foram escritos por Sophia com assistência do Claude (Anthropic).

## O que já foi feito

| Data | Marco |
|---|---|
| 18/09/2026 | Primeira leitura de impedância pela placa de teste P2 (Fellipe Godoy): 43.282,3 Ω, fase 0,97°, par de eletrodos 0 e 1, 10 kHz, 100 mV. |
| 21/09/2026 | Mesma leitura reproduzida em outra estação de trabalho (Sophia Nickerson): 43.239,7 Ω, fase 0,96°. As leituras ficam dentro de 0,15% entre si. |
| 29/09/2026 | Tanque de 16 eletrodos montado, mapeamento do conector P1 deduzido do esquemático e confirmado com um resistor de 1 kΩ (992,1 Ω). Primeira imagem de diferença: objeto isolante localizado no eletrodo 11. |

**Limites da primeira imagem:** a linha de base foi estimada (o tanque vazio ainda não tinha sido medido), só uma posição real do objeto foi medida, e o modelo não conhece a impedância de contato dos eletrodos. A imagem é qualitativa. Repetir o resultado com linha de base real e objeto em outras posições é o foco atual.

## Hardware

- Analog Devices **EVAL-ADICUP3029** (processador) + **EVAL-CN0565-ARDZ** (bioimpedância: AD5940 e crosspoints ADG2128). Firmware `cn0565.hex` e documentação oficiais da Analog Devices.
- Tanque: pote de 23,8 cm de diâmetro interno, 16 parafusos de inox como eletrodos, centros a 3 cm do fundo, igualmente espaçados, vedados por fora.
- Computador: Mac, ligado à placa por USB.

### Mapeamento do conector P1 (índice do software e pino físico)

A documentação pública da Analog Devices não traz esse mapeamento. Ele foi deduzido do esquemático oficial (EVAL-CN0565-ARDZ rev. B) e confirmado com um resistor de 1 kΩ nos pinos 3 e 4 (índices 12 e 13). O restante segue o esquemático.

| Eletrodo (índice) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pino do P1 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 3 | 4 | 5 | 6 |

Os pinos 1, 2, 29 e 30 são terra, e os pinos 13 a 16 não são conectados.

## Instalação (macOS)

1. Instalar o libiio nativo (arquivo `.pkg` na página de releases do libiio, no GitHub da Analog Devices).
2. Criar e ativar um ambiente virtual Python e instalar as dependências:

```bash
python3 -m venv liverscan
source liverscan/bin/activate
pip install -r requirements.txt
```

3. Gravar o firmware `cn0565.hex` na placa, arrastando o arquivo para o volume `DAPLINK` pelo Finder.

## Scripts

Os scripts leem e gravam em `~/Documents/liverscan_dados/` (medições) e `~/Documents/liverscan_imagens/` (imagens).

### Coleta (`codigo/coleta`)

- **`varredura_eit.py`**: mede os 120 pares possíveis entre os 16 eletrodos, a 10 kHz e 100 mV, pela biblioteca `adi.cn0565` (porta serial `/dev/cu.usbmodem*`, achada automaticamente, 230400 baud). Cada par é gravado no CSV assim que é medido. Tenta cada par até 3 vezes e aborta depois de 5 falhas seguidas.
  `python varredura_eit.py NOME_DA_MEDICAO`

### Análise (`codigo/analise`)

- **`checar_varreduras.py`**: confere cada CSV da pasta de dados (120 linhas, nenhum par vazio, mediana de cada eletrodo a menos de 3% da mediana geral) e imprime PASSA ou REPROVA.
- **`media_v1_v5.py`**: gera a linha de base `baseline_media_v1_v5.csv`, a média de duas varreduras do tanque vazio, e lista os pares em que elas discordam mais de 5%.
- **`media_vazio.py`**: média de três varreduras do tanque vazio (`vazio_1`, `vazio_2` e `vazio_3`).

### Imagem (`codigo/imagem`)

- **`liverscan_imagem_diferenca.py`**: script principal. Lê CSVs de medição e desenha, com a biblioteca pyEIT (método Jacobiano), uma imagem de diferença de condutividade por arquivo (azul = menos condutivo). Sem `--base`, estima a linha de base pela mediana de cada distância entre eletrodos. Foi o que gerou a primeira imagem, de 29/09. Com `--base=VAZIO.csv`, usa uma linha de base real. Salva `imagem_liverscan.png`.
  `python liverscan_imagem_diferenca.py [--base=VAZIO.csv] [PASTA_OU_CSVs]`
- **`liverscan_imagem_sem_e3.py`**, **`liverscan_imagem_batata_contra_v1.py`** e **`liverscan_imagem_baseline_v1v5_todos_eletrodos.py`**: variantes usadas em sessões específicas (excluir um eletrodo, comparar a batata com o tanque vazio, descartar pares que discordam entre duas linhas de base). Os nomes de arquivo estão fixos no código, então servem como exemplos a adaptar.

## Formato dos dados

Cada medição é um CSV com as colunas `pair, e_pos, e_neg, real, imag, magnitude, phase_deg`, nomeado `NOME_10kHz_100mV_AAAAMMDD_HHMMSS.csv`. A ordem dos pares é fixa: para o eletrodo negativo de 1 a 15, o positivo de 0 até o anterior.

## Documentação

- `docs/guia_primeiro_teste_eit.md`: guia do primeiro teste (tanque de salmoura, validação com resistor e com batata, ordem dos experimentos seguintes).

## Licença

MIT. Veja `LICENSE`.
