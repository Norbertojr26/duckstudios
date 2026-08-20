-- [PROPOSTA] Tabela de preços de SERVIÇO — a lacuna que faltava para orçar job, não só locação.
-- Todos os valores são ponto de partida para calibrar, não preço fechado. O que importa aqui é a
-- ESTRUTURA: com a tabela cadastrada, o agente comercial monta orçamento sem inventar número.
--
-- Duas linhas merecem atenção especial:
--   * LIC-*  licenciamento de uso. Em publicidade, a cessão de uso é linha própria e é onde está
--            a margem do trabalho de marca. Cobrar produção sem cobrar uso é deixar dinheiro na mesa.
--   * RET-*  retainer mensal. É o formato do cliente que você disse querer — e não existe hoje.

INSERT INTO price_list (codigo, descricao, unidade, valor, categoria) VALUES
 -- Equipe
 ('SRV-DIR',  'Direção / Direção de fotografia',                    'diaria',  2500.00, 'servico'),
 ('SRV-CAM',  'Operador de câmera',                                 'diaria',   800.00, 'servico'),
 ('SRV-AC',   'Assistente de câmera / AC',                          'diaria',   500.00, 'servico'),
 ('SRV-SOM',  'Técnico de som direto',                              'diaria',   900.00, 'servico'),
 ('SRV-GAF',  'Gaffer / elétrico',                                  'diaria',   700.00, 'servico'),
 ('SRV-PROD', 'Produção de set / assistente de produção',           'diaria',   700.00, 'servico'),
 ('SRV-DRONE','Operador de drone (piloto)',                         'diaria',  1000.00, 'servico'),
 -- Pós
 ('POS-EDIT', 'Edição',                                             'hora',     150.00, 'pos'),
 ('POS-COLOR','Color grading / finalização por peça',               'unidade',  600.00, 'pos'),
 ('POS-MOTION','Motion graphics / GC por peça',                     'unidade',  800.00, 'pos'),
 ('POS-TRILHA','Trilha licenciada / sound design por peça',         'unidade',  400.00, 'pos'),
 -- Deslocamento e diárias fora
 ('DES-KM',   'Deslocamento rodoviário',                            'km',         3.00, 'deslocamento'),
 ('DES-FORA', 'Diária fora de sede (hospedagem + alimentação)',     'diaria',   350.00, 'deslocamento'),
 -- Licenciamento de uso (percentual sobre o valor de produção)
 ('LIC-DIG12','Uso digital (redes/site), 12 meses — % s/ produção', 'percentual',  30.00, 'licenciamento'),
 ('LIC-TV12', 'Uso TV aberta / OOH, 12 meses — % s/ produção',      'percentual',  80.00, 'licenciamento'),
 ('LIC-PERP', 'Uso perpétuo / irrestrito — % s/ produção',          'percentual', 150.00, 'licenciamento'),
 -- Condições comerciais
 ('TAX-URG',  'Urgência: prazo abaixo do mínimo — % s/ total',      'percentual',  40.00, 'extra'),
 ('TAX-FDS',  'Filmagem em fim de semana / feriado — % s/ equipe',  'percentual',  50.00, 'extra'),
 ('TAX-HE',   'Hora extra além da 10ª hora de diária',              'hora',     250.00, 'extra'),
 -- Retainer: o formato do cliente-alvo
 ('RET-4PEC', 'Retainer mensal — 4 peças/mês, equipe e equipamento','mes',    25000.00, 'retainer'),
 ('RET-8PEC', 'Retainer mensal — 8 peças/mês, equipe e equipamento','mes',    45000.00, 'retainer')
ON CONFLICT (codigo) DO UPDATE SET
  descricao = EXCLUDED.descricao, unidade = EXCLUDED.unidade,
  valor = EXCLUDED.valor, categoria = EXCLUDED.categoria;
