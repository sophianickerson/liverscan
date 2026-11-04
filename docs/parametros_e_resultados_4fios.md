# Medição de 4 fios: parâmetros, tempo real e o que aprendemos (31/out a 02/nov/2026)

## Parâmetros que usamos hoje
| Parâmetro | Valor | Por quê |
|---|---|---|
| Amplitude | **800 mV** | Com 300 mV as leituras saem em degraus de ~15 Ω (resolução ruim). Com 800 mV, ~3 Ω. |
| Frequência | 10 kHz | |
| Injeções | 16 (208 leituras por quadro) | |
| Padrão de injeção | **salto 4** (`--salto=4`, injeta em i e i+4) | Impedância mediana ~505 Ω contra ~126 Ω no adjacente; sinal/ruído das leituras 3 a 4× melhor. |
| Baseline | do **mesmo** mV e do **mesmo** padrão de injeção da medição | Misturar dá imagem errada. |
| Tanque | vazio (água salgada) para o baseline | |

Receita de 4 fios nas chaves ADG2128 (ver `codigo/diagnostico/teste_vazamento.py`): F+ nas linhas Y0/Y1, F− em Y2/Y3, S+ em Y6, S− em Y7.

## Por que 800 mV
Teste com duas varreduras idênticas do tanque (169 leituras cada):

| | 300 mV | 800 mV |
|---|---|---|
| leituras que mudam >5% entre as 2 varreduras | 36 | 16 |
| 90% das leituras abaixo de | 12,8% | 5,0% |
| pior caso | 22% | 10,1% |
| resolução aparente | ~15 Ω | ~3,2 Ω |

## Tempo real: `codigo/ao_vivo/aovivo_rapido.py`
Uma conexão aberta, 800 mV, reconstrução Jacobiana (pyEIT), quadro de ~15–18 s.

```bash
python aovivo_rapido.py --salto=4 --escala=0.5 --nome=meu_teste
```
- `--salto=K` padrão de injeção (recomendado 4) · `--nbase=N` varreduras do baseline (padrão 3) · `--base=ARQ.csv` usa baseline salvo · `--mv=` · `--suave=0..1` · `--inj=` · `--nome=`.
- `--escala=X` trava a escala de cor em −X a +X. **Sem isso, cada quadro é colorido pelo próprio pico e tudo parece igualmente saturado.** Use para comparar objetos.
- Tecla `b`: novo baseline (tanque vazio). Tecla `s`: salva o próximo quadro completo (PNG, CSV, o baseline em uso e uma linha em `registro.csv`).
- Dados salvos em `~/Documents/liverscan_dados/AAAA-MM-DD/`.
- A métrica mais confiável no título é a **mudança mediana** das leituras. O sinal/ruído da imagem varia muito entre execuções.

## Sinal e cor (corrigido em 31/out)
O pyEIT calcula a mudança sobre valores com sinal. O modelo espera `np.sign(eit.v0.real)` em cada leitura, então a chamada correta é `eit.solve(v * sinal, v0 * sinal, normalize=True)`.
**Convenção atual: vermelho = mais condutivo que a água; azul = menos condutivo.** Os scripts antigos (`foto_4fios.py`, `codigo/imagem/liverscan_imagem_*`) e imagens anteriores a 31/out ~15:30 usam a convenção invertida.

## Resultados de bancada (qualitativos)
- **Posição (31/out):** com salto 4, batata a ~2 cm da parede junto dos eletrodos 3, 11 e 7: o programa apontou o eletrodo certo nas três vezes (erros de direção de ~1° a ~7°, medidos a olho). A mancha aparece mais para dentro que o objeto, um viés conhecido da EIT. A distância ao centro não foi medida com régua.
- **Gelatinas com óleo (02/nov):** fantomas de 0, 10, 20 e 30% de óleo nominal no centro, `--escala=0.5`. Pico 0,47 / 0,49 / 0,42 / 0,38 (e 0,48 na repetição de 0%). O sistema ordena os extremos, mas **isso ainda não é medida de gordura**: o teor real de óleo é desconhecido (parte vazou) e foi uma gelatina por teor. Converter pico em % de gordura exige calibração com gelatinas de sal conhecido e sem óleo. Não existe uma fórmula única de impedância para % de gordura na literatura.

## Lições
- Resolução do instrumento (800 mV) importou mais que o tipo de injeção; depois dela, o salto 4 foi o maior ganho.
- Para comparar objetos, use escala de cor fixa. Se o baseline for refeito entre medidas, salve-o junto de cada quadro.
- A água da gelatina precisa ter a mesma condutividade do tanque, para que só o óleo crie contraste.

## Próximos passos
1. Gelatinas de calibração com sal conhecido (0, 0,5, 1 e 2 g/L), sem óleo.
2. Refazer as gelatinas com óleo em água a 5 g/L, com pesagem antes e depois e mais de uma gelatina por teor.
3. Colher de inox e posição intermediária da batata com régua.
4. Salto 8 só com as 8 injeções distintas; outros saltos; erro de reciprocidade.
5. DFT de 2048 pontos no firmware (quadro ~4× mais rápido), só com plano B de gravação.
