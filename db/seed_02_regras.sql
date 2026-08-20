-- Camada de DECISÕES sobre a carga mecânica de seed_inventario.sql.
-- Separada de propósito: o import é reprodutível a partir das planilhas; isto aqui é julgamento,
-- e precisa ficar visível e discutível. Rodar sempre DEPOIS de seed_inventario.sql.
--
-- Tudo marcado [PROPOSTA] é sugestão minha e deve ser confirmado pelo dono do processo.

-- =============================================================================
-- 1. Correções de percentual fora da regra
--    A regra real (decodificada dos dados): 3,5% câmera principal · 3% premium ·
--    2,5% médio · 2% case — e acessório HERDA o percentual do item-mãe.
-- =============================================================================

-- 0023 RC PRO 2 sai com o Mavic; as baterias do mesmo drone já estão a 3,5%.
UPDATE asset SET valor_diaria = round(valor_aquisicao * 0.035, 2),
                 valor_semanal = round(valor_aquisicao * 0.14, 2)
 WHERE codigo = '0023';

-- Cases seguem 2% como todos os outros.
UPDATE asset SET valor_diaria = round(valor_aquisicao * 0.02, 2),
                 valor_semanal = round(valor_aquisicao * 0.08, 2)
 WHERE codigo IN ('0146', '0105');

-- 0086 Sony 28-70mm f/3.5-5.6 é lente de kit, não lente premium.
UPDATE asset SET categoria = 'Lente/Acessório Câmera' WHERE codigo = '0086';

-- =============================================================================
-- 2. [PROPOSTA] Tarifa mensal — a lacuna que trava proposta de longa e de retainer
--    Mercado usa mês ≈ 3× semana. Adotei 2,5× (= 10 diárias) porque o alvo é
--    justamente contrato longo, e 3× deixa o mês caro demais para competir.
--    Efeito: FX3 = R$ 875/dia · R$ 3.500/semana · R$ 8.750/mês.
-- =============================================================================

UPDATE asset SET valor_mensal = round(valor_semanal * 2.5, 2) WHERE valor_semanal IS NOT NULL;

-- =============================================================================
-- 3. Valor de reposição
--    valor_aquisicao é o que custou; o termo de responsabilidade precisa do que custa REPOR hoje.
--
--    Tentei um fator por idade (câmbio + inflação de importado) e descartei: ele infla itens
--    antigos para números que não se sustentam. Uma Pelican 1560 de 2010 viraria R$ 9.000 e uma
--    a7 III de 2018 viraria R$ 18.000 — nenhum dos dois repõe por esse preço, e um valor inflado
--    num documento assinado é pior que nenhum valor.
--
--    Regra adotada: reposição = valor de compra, marcado como NÃO CONFIRMADO. Serve de piso para
--    o termo sair, e o app avisa enquanto não houver confirmação humana.
--    Confirmar à mão os ~30 itens de maior valor consultando o preço atual do mesmo modelo
--    (ou do equivalente atual, quando o modelo saiu de linha).
-- =============================================================================

UPDATE asset SET valor_reposicao = valor_aquisicao, valor_reposicao_confirmado = false
 WHERE valor_aquisicao IS NOT NULL;

-- 4. Conteúdo dos cases
--    Só os que o próprio nome resolve sem ambiguidade. Atribuir conteúdo errado é
--    pior que deixar vazio: o app passaria a acusar "faltando" um item que nunca
--    esteve ali. Os demais cases ficam abertos até a passada física pelo parque.
-- =============================================================================

UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0139' AND a.codigo IN ('0140','0141','0142','0143','0144');   -- Blazar
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0146' AND a.codigo = '0145';                                   -- Laowa 12mm
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0105' AND a.codigo IN ('0103','0104');                         -- LS 600d Pro
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0126' AND a.codigo IN ('0121','0123');                         -- Storm 1200X
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0127' AND a.codigo = '0124';                                   -- Fresnel CF12
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0131' AND a.codigo IN ('0122','0125','0129','0130');           -- refletores
UPDATE asset a SET container_id = c.id FROM asset c
 WHERE c.codigo = '0072' AND a.codigo IN ('0066','0067','0068','0069','0070','0071'); -- Nucleus-M

-- =============================================================================
-- 5. Kits — 61 itens, 46% do patrimônio
--    Kit não tem disponibilidade própria: alugar um kit reserva cada item.
--    valor_diaria do kit = 90% da soma dos itens (desconto de pacote) e já embute
--    o case, que hoje é cobrado como linha separada na proposta. [PROPOSTA]
-- =============================================================================

INSERT INTO kit (nome, descricao) VALUES
 ('Blazar Remus 1.5x Anamorphic',  'Set anamórfico 33/50/65/85/125mm PL + case'),
 ('NiSi Athena Prime',             'Set 18/35/85mm PL + adaptadores PL→E'),
 ('Aputure Storm 1200X',           'Fixture + DMX + Fresnel CF12 + refletor + cases'),
 ('Aputure LS 600d Pro',           'Fixture + charger V-Mount + case'),
 ('Tilta Nucleus-M',               'FIZ + 2 motores + 2 empunhaduras + charger + hard case'),
 ('Hollyland Solidcom SE',         'Master + 7 headsets + base de carga'),
 ('DJI Avata 2 FPV',               'Drone + goggles + 2 controles + 3 baterias + hub + filtros'),
 ('DJI Mavic 4 Pro',               'Drone + RC Pro 2 + 3 baterias + hub + fonte'),
 ('Sony UWP-D27 (6 canais)',       '2 receptores + 4 transmissores'),
 ('Sony UWP-D26',                  'Receptor + 2 transmissores')
ON CONFLICT (nome) DO NOTHING;

INSERT INTO kit_item (kit_id, asset_id, quantidade)
SELECT k.id, a.id, 1 FROM (VALUES
 ('Blazar Remus 1.5x Anamorphic', ARRAY['0140','0141','0142','0143','0144','0139']),
 ('NiSi Athena Prime',            ARRAY['0008','0009','0010','0006','0007']),
 ('Aputure Storm 1200X',          ARRAY['0121','0123','0124','0122','0126','0127']),
 ('Aputure LS 600d Pro',          ARRAY['0103','0104','0105']),
 ('Tilta Nucleus-M',              ARRAY['0066','0067','0068','0069','0070','0071','0072']),
 ('Hollyland Solidcom SE',        ARRAY['0043','0044','0045','0046','0047','0048','0049','0050','0051']),
 ('DJI Avata 2 FPV',              ARRAY['0013','0014','0015','0016','0017','0018','0019','0020','0021']),
 ('DJI Mavic 4 Pro',              ARRAY['0022','0023','0024','0025','0026','0027','0028']),
 ('Sony UWP-D27 (6 canais)',      ARRAY['0147','0148','0149','0150','0151','0152']),
 ('Sony UWP-D26',                 ARRAY['0060','0061','0062'])
) AS m(nome, tags)
JOIN kit k ON k.nome = m.nome
JOIN asset a ON a.codigo = ANY(m.tags)
ON CONFLICT (kit_id, asset_id) DO NOTHING;

UPDATE kit k SET valor_diaria = round(s.soma * 0.90, 2)
  FROM (SELECT ki.kit_id, sum(a.valor_diaria) soma
          FROM kit_item ki JOIN asset a ON a.id = ki.asset_id GROUP BY ki.kit_id) s
 WHERE s.kit_id = k.id;

-- =============================================================================
-- 6. Nomes do catálogo — o cadastro estava genérico onde o catálogo é específico
-- =============================================================================

UPDATE asset SET nome = 'Sony UWP-D27 Receptor'     WHERE codigo IN ('0147','0150');
UPDATE asset SET nome = 'Sony UWP-D27 Transmissor'  WHERE codigo IN ('0148','0149','0151','0152');
UPDATE asset SET nome = 'NiceFoto 880A Painel LED BiColor', marca = 'NiceFoto'
 WHERE codigo IN ('0106','0107');
UPDATE asset SET nome = 'Hollyland Lark Max 1'      WHERE codigo = '0058';
UPDATE asset SET nome = 'Softbox Amaran Mini 60x60' WHERE codigo = '0090';
UPDATE asset SET nome = 'Softbox Fototudo FT-8120 120x120' WHERE codigo = '0089';
UPDATE asset SET nome = 'Tripé Manfrotto 755XB + cabeça 502AH' WHERE codigo = '0093';
UPDATE asset SET nome = 'Luva-Pino JB300 (combo triplo)' WHERE codigo = '0128';
UPDATE asset SET nome = 'C-Stand Century Pino'      WHERE codigo = '0108';
UPDATE asset SET nome = 'Tripé Greika WT808'        WHERE codigo IN ('0111','0112');
UPDATE asset SET nome = 'Tripé Iconoflash Mini'     WHERE codigo IN ('0099','0100');
