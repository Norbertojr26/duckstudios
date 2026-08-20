-- Itens que o catálogo oferece e que NÃO são seus: são SUBLOCADOS de terceiros (confirmado).
--
-- Consequências de serem sublocados, e por isso este arquivo existe separado:
--   * não entram no patrimônio (R$ 519.110 continua sendo só o que é seu)
--   * não recebem etiqueta QR nem número de série — o dono é outro
--   * não têm valor de reposição seu; quem responde pelo dano é o contrato com o fornecedor
--   * o preço depende de cotação: por isso requer_cotacao = true e valor_diaria fica NULL
--
-- Ficam DISPONÍVEIS (você realmente aluga isso hoje), mas marcados para cotar antes de fechar
-- preço. O agente comercial lê essa flag e responde "preciso cotar com o fornecedor" em vez de
-- inventar um valor.
--
-- Código CAT-xx porque a numeração do AssetTiger é do parque próprio.

INSERT INTO asset (codigo, nome, categoria, marca, status, serializado, origem_import, observacoes)
VALUES
 ('CAT-01','GoPro 13','Câmera Principal','GoPro','disponivel',false,'catalogo:2026-02',
  'Catálogo p.11. Não existe no inventário. Confirmar: é seu, foi vendida, ou é sublocada?'),
 ('CAT-02','SmallRig Mini Matte Box Lite','Acessório Cinema','SmallRig','disponivel',false,'catalogo:2026-02',
  'Catálogo p.25. Inventário só tem a Tilta Mirage (0073).'),
 ('CAT-03','K&F 82mm Variable Star Filter','Acessório Cinema','K&F Concept','disponivel',false,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-04','K&F 82mm Variable ND 2-400','Acessório Cinema','K&F Concept','disponivel',false,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-05','K&F 67mm Variable ND 2-32 + CPL 1/4','Acessório Cinema','K&F Concept','disponivel',false,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-06','Tripé Sirui SQ75A com cabeça S5','Tripé Premium','Sirui','disponivel',false,'catalogo:2026-02',
  'Catálogo p.39. Único tripé de vídeo bowl 75mm do catálogo e não está no inventário.'),
 ('CAT-07','Tilta Hydra Car Mount','Acessório Cinema','Tilta','disponivel',false,'catalogo:2026-02',
  'Catálogo p.42. Ventosas eletrônicas, carga 20 kg.'),
 ('CAT-08','Tilta Shoulder Rig LWS 15mm','Acessório Cinema','Tilta','disponivel',false,'catalogo:2026-02',
  'Catálogo p.43.'),
 ('CAT-09','Hollyland M2','Áudio','Hollyland','disponivel',false,'catalogo:2026-02',
  'Catálogo p.62. Inventário tem Lark Max 1 e 2, não tem M2.'),
 ('CAT-10','Deity TC-SL1 Timecode Smart Slate','Áudio','Deity','disponivel',false,'catalogo:2026-02',
  'Catálogo p.66. Inventário tem 3x TC-1, não tem a claquete.'),
 ('CAT-11','Blackmagic ATEM Mini Pro','Monitor/Wireless','Blackmagic','disponivel',false,'catalogo:2026-02',
  'Catálogo p.79. Switcher de 4 canais para live.'),
 ('CAT-12','Teleprompter para iPad','Produção','Genérico','disponivel',false,'catalogo:2026-02',
  'Catálogo p.80.'),
 ('CAT-13','Baofeng BF-777s (kit 6 rádios)','Comunicação','Baofeng','disponivel',false,'catalogo:2026-02',
  'Catálogo p.83. Kit com 6 unidades — controlar por quantidade, não por série.'),
 ('CAT-14','ProAim Bag','Case/Proteção','ProAim','disponivel',false,'catalogo:2026-02',
  'Catálogo p.70.')
ON CONFLICT (codigo) DO UPDATE SET nome = EXCLUDED.nome, observacoes = EXCLUDED.observacoes;

UPDATE asset SET quantidade = 6 WHERE codigo = 'CAT-13';

-- Marca todos como sublocados e pendentes de cotação.
UPDATE asset SET proprietario = 'sublocado', requer_cotacao = true,
                 valor_aquisicao = NULL, valor_reposicao = NULL,
                 valor_diaria = NULL, valor_semanal = NULL, valor_mensal = NULL
 WHERE origem_import = 'catalogo:2026-02';

-- FALTA PREENCHER, e trava o comercial: de quem você subloca cada um, e por quanto.
-- Sem custo_diaria não existe margem, e sem fornecedor_id não existe a quem ligar.
-- Cadastrar os fornecedores em `company` (tipo = 'fornecedor') e ligar aqui.

-- 0091: confirmado que é o ProAim Breeza do catálogo (p.41) — o cadastro estava errado.
-- O valor de compra de R$ 360 era de outro item; fica NULL para você preencher, porque chutar
-- o preço de um slider com trilhos, mala e cabeça DH12 sairia errado nos dois sentidos.
-- Enquanto o valor não vier, a diária também não pode ser calculada (é % do valor).
UPDATE asset SET
  nome = 'ProAim Breeza Dolly Slider',
  marca = 'ProAim',
  categoria = 'Acessório Cinema',
  valor_aquisicao = NULL, valor_reposicao = NULL,
  valor_diaria = NULL, valor_semanal = NULL, valor_mensal = NULL,
  observacoes = 'Corrigido pelo catálogo p.41: 16 rodas Metalon, trilhos, carga 100 kg, mala e '
                'cabeça SmallRig DH12 inclusa. Valor de compra a preencher (o R$ 360 do cadastro '
                'antigo era de outro item). Sem valor não há diária: a diária é 3% do valor.'
 WHERE codigo = '0091';
