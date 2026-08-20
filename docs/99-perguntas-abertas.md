# Perguntas abertas

Nada aqui dá para eu inferir — depende da sua operação. Isto é o insumo da Fase 0.
Responder direto neste arquivo (editar e commitar).

## ✅ Já respondido nos áudios de 18/08 (não precisa repetir)

| Pergunta | Resposta |
|---|---|
| Ferramenta de inventário hoje | AssetTiger (gratuito) — tem check-in, não tem check-out |
| Como o controle funciona | memória; nada sumiu porque ele era o único operador |
| Canais de lead | 90% indicação/rede · casamentos.com.br (pago) |
| Resultado da plataforma paga | ⚠️ 70+ leads respondidos → 1 fechamento desde março |
| Ticket atual vs. desejado | ⚠️ R$ 3,8k (casamento) vs. R$ 10k–80k (marca/retainer) |
| Prospecção já tentada | e-mail, mensagem, ligação, visita — sem retorno |
| Contexto urgente | campanha em curso, vários videomakers com o equipamento |

**Prioridade de resposta agora:** perguntas 9, 10, 11, 13 e 17 (bloqueiam o P0 e o P2).

## Operação de mídia (bloqueia SOP-001)

1. **Qual estrutura de pastas você usa hoje?** Cole a árvore real de um projeto recente.
2. **Quais câmeras e formatos?** (modelos, codecs, se há RAW, drone, GoPro, áudio externo)
3. **Quantas diárias por mês** e quantos TB por diária, em média?
4. **Qual NLE?** Premiere, Resolve, Final Cut? Muda formato de proxy e estrutura esperada.
5. **Como você faz backup hoje?** Quantas cópias, em quê, quem confere?
6. **Usa alguma ferramenta de offload** (Hedge, ShotPut, Silverstack) ou copia no Finder?
7. **Quando o cartão é formatado**, por quem, e com base em qual verificação?
8. **Política de retenção:** por quanto tempo guarda o bruto? Quem autoriza apagar?

## Locação (bloqueia SOP-002)

9. ~~Quantos itens no inventário?~~ ✅ **156 itens, R$ 519.110** — importado e validado.
    Ver [`13-analise-inventario.md`](13-analise-inventario.md). Restam destas:
    - 9a. O AssetTiger tem **número de série** preenchido? (156/156 vieram vazios) 🔴
    - 9b. `0103` Aputure LS 600d: R$ 10.779,61 ou R$ 15.000? E `0104`: R$ 8.000 ou R$ 6.000? 🔴
    - 9c. Data de aquisição do `0145` Laowa 12mm 🟡
    - 9d. **Valor de reposição** dos ~30 itens de maior valor (é o que vai no termo) 🔴
      — o seed usa o valor de compra como piso, marcado como NÃO confirmado
    - 9e. O que mora dentro dos cases? 7 resolvidos pelo nome; faltam Pelican, DeWalt, SKB e
      Worldview 🟡
    - 9f. **Os 14 itens do catálogo sem cadastro** são seus, foram vendidos, ou você subloca?
      Ver [`15-catalogo-vs-inventario.md`](15-catalogo-vs-inventario.md) 🔴
    - 9g. `0091` Dolly Slider: é ProAim Breeza (catálogo) ou Jingmei a R$ 360 (cadastro)? 🔴
10. **O que é controlado por número de série** vs. por quantidade? (cabo e bateria por serial é o
    jeito mais rápido de abandonar o sistema) 🔴 bloqueia P0
11. **Trabalha com kits fechados** ou monta item a item? 🔴 bloqueia P0
12. **Política de caução:** valor, quando exige, como devolve.
13. **Buffer entre locações:** quantas horas para vistoria/limpeza/recarga? 🔴 bloqueia P0
13b. **Quem mais vai usar o app** na campanha, e esses videomakers devolvem sozinhos? 🔴 bloqueia P0
14. **Como registra dano hoje?** Tem termo de responsabilidade padrão? (anexar)
15. **Aluga para pessoa física?** Muda exigência de documento e risco.

## Comercial e financeiro (bloqueia SOP-003)

16. **Por onde chegam os leads**, em ordem de volume?
17. ~~Tabela de preços de equipamento~~ ✅ recebida e decodificada (3,5% / 3% / 2,5% / 2% da diária,
    semanal = 4× diária, acessório herda o % do item-mãe). Restam:
    - 17a. Confirmar as 4 exceções fora da regra — principalmente `0023` DJI RC PRO 2 🔴
    - 17b. ~~Tarifa mensal~~ ✅ criada: **mês = 2,5× semana = 10 diárias**. Confirmar 🟡
    - 17c. ~~Case como linha separada~~ ✅ embutido no preço dos 10 kits (desconto de 10%). Confirmar 🟡
    - 17d. ~~Tabela de serviço~~ ✅ criada em `seed_04_precos_servico.sql` — **21 linhas, todas
      proposta**. Calibrar os valores 🔴
    - 17e. **Licenciamento de uso** entrou como linha própria (digital 12m +30%, TV/OOH +80%,
      perpétuo +150%). Você cobra isso hoje? Em publicidade é onde está a margem 🔴
    - 17f. **Retainer mensal** entrou a partir de R$ 25.000 (4 peças/mês). É o formato do cliente
      que você disse querer, e não existia na tabela 🔴
18. **Acima de que valor** você quer aprovar pessoalmente?
19. **Prazo mínimo operacional** para aceitar um job?
20. **Quantos orçamentos por mês** e qual a taxa de fechamento aproximada?
21. **Quem emite NF** e como? Tem integração possível?
22. **Onde estão os dados hoje?** (planilha, Notion, agenda, WhatsApp — o que migrar)

## Equipe e acesso

23. **Quantas pessoas** vão usar o sistema? Precisa de permissão por usuário na Fase 1?
24. **Tem freelancers recorrentes** cujas diárias precisam entrar no custo do projeto?
25. **Quem é o dono humano** de cada SOP (quem responde quando o agente erra)?

## Infra

26. **Qual Mac Mini** (chip, RAM, SSD)? Define qual modelo local roda.
27. **Já tem DAS/RAID?** Qual capacidade?
28. **Qual estação de bateria** e capacidade em Wh?
29. **Starlink padrão ou Mini?**
30. **Tem servidor/NAS no studio** para onde a mídia migra depois da locação?

## Escopo

31. Das automações possíveis, **qual você mais quer ver funcionando primeiro?**
    (a resposta define a ordem da Fase 2 — a primeira vitória precisa ser visível)

## Estratégia (bloqueiam o P3)

32. **Qual é o cliente-alvo, em uma frase específica?** Setor, porte, cidade, quem decide.
    "Marca que precisa de conteúdo" é largo demais para virar lista.
33. Dos últimos 20 leads de casamento: **quanto tempo até sua primeira resposta** e **quantos
    receberam um segundo contato?** (decide se o problema é segmento ou processo)
34. **Quem já te indicou** nos últimos 2 anos? Lista nominal — é o seu canal principal e hoje é passivo.
35. **Quais produtoras e agências** da sua região já subcontratam? (foi assim que veio seu cliente atual)
36. A campanha atual **pode virar case público** — ou tem restrição de divulgação?
