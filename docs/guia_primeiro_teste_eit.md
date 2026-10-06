# Primeiro Teste de EIT — Guia Completo
### LiverScan · montagem do tanque de salmoura com a EVAL-CN0565-ARDZ

Para quem nunca mexeu com essas placas. Tempo estimado: um fim de semana. Custo: menos de R$ 200.

## Antes de começar: o que este teste é e o que não é

**O que é:** provar que a cadeia inteira funciona. Eletrodo → cabo → placa → software → imagem. Você vai colocar eletrodos num balde com água salgada, medir, colocar uma batata dentro, medir de novo, e ver se a batata aparece na imagem.

**O que não é:** medir gordura no fígado. Nem chega perto. Isso vem muito depois.

**Por que vale a pena mesmo assim:** hoje o LiverScan existe só em simulação. Depois deste teste, existe em hardware.

> ⚠️ **Regra de segurança:** Não coloque eletrodo em nenhuma pessoa, nem em você. A placa tem limitação de corrente, mas medir em gente envolve protocolo, consentimento e aprovação de Comitê de Ética. Balde não tem nada disso. Fique no balde.

## Glossário rápido
- **Firmware:** o programa que roda dentro da placa.
- **Shield:** placa que encaixa em cima de outra, tipo Lego. A CN0565 é shield da ADICUP3029.
- **Pinout:** o mapa de qual pino do conector corresponde a qual eletrodo.
- **Linha de base:** a medição de referência, feita antes de mudar qualquer coisa.
- **Imagem de diferença:** o software compara a medição nova com a linha de base e mostra só o que mudou.
- **Salmoura:** água com sal. Conduz eletricidade; água pura quase não conduz.

## PARTE 1 — Software funcionando
1. Baixar documentação oficial ADI: user guide, firmware, software de PC.
2. Empilhar CN0565 em cima da ADICUP3029.
3. Ligar USB, gravar firmware, abrir software de PC.

## PARTE 2 — A verificação que salva dias
**Passo 4 — Teste com resistor conhecido.** Medir um resistor de 1kΩ com multímetro, depois ligar nos eletrodos e comparar com a leitura do software. Se não bater, não adianta montar o tanque.

## PARTE 3 — Montando o tanque
- Balde/pote redondo, paredes retas (~20cm de diâmetro).
- 16 eletrodos de parafuso inox M4-M6 com porca e arruela, igualmente espaçados.
- Numerar os eletrodos sempre no mesmo sentido (a reconstrução assume isso).

## PARTE 4 — Primeira medição
- Preparar salmoura (começar com 1 colher de chá de sal por litro).
- Medir linha de base 3x sem mexer em nada — devem ser praticamente iguais.

## PARTE 5 — O teste da batata
- Colocar a batata num ponto identificável, medir, salvar.
- Mover para o lado oposto, medir de novo.
- A mancha na imagem de diferença tem que se mover junto — isso confirma sinal real, não artefato.

## O que anotar em tudo
Data/hora, litros de água, quantidade de sal, numeração dos eletrodos, frequência usada, nomes dos arquivos salvos.

## Depois que funcionar (em ordem de dificuldade)
1. Objetos diferentes (plástico, metal, pepino).
2. Variar a frequência (1kHz–200kHz).
3. Fantoma com gordura controlada — o experimento que responde à pergunta central do PIPE.
4. Camada externa simulando gordura subcutânea.

---
*Nota: durante a execução real (setembro 2026), surgiu uma divergência ainda em aberto sobre a contagem de eletrodos — 16 conforme a fiação atual do CN0565 vs. até 24/32 mencionados como possibilidade. Resolver antes de fechar o layout final do tanque/cinto.*
