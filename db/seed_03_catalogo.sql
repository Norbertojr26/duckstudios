-- Itens que o CATÁLOGO comercial oferece mas que NÃO existem no controle patrimonial.
-- Entram bloqueados e sem preço: item que ninguém cadastrou não pode ser alugado nem orçado.
-- Código provisório CAT-xx; renumerar para a sequência do AssetTiger ao cadastrar de verdade.

INSERT INTO asset (codigo, nome, categoria, marca, status, serializado, origem_import, observacoes)
VALUES
 ('CAT-01','GoPro 13','Câmera Principal','GoPro','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.11. Não existe no inventário. Confirmar: é seu, foi vendida, ou é sublocada?'),
 ('CAT-02','SmallRig Mini Matte Box Lite','Acessório Cinema','SmallRig','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.25. Inventário só tem a Tilta Mirage (0073).'),
 ('CAT-03','K&F 82mm Variable Star Filter','Acessório Cinema','K&F Concept','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-04','K&F 82mm Variable ND 2-400','Acessório Cinema','K&F Concept','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-05','K&F 67mm Variable ND 2-32 + CPL 1/4','Acessório Cinema','K&F Concept','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.26.'),
 ('CAT-06','Tripé Sirui SQ75A com cabeça S5','Tripé Premium','Sirui','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.39. Único tripé de vídeo bowl 75mm do catálogo e não está no inventário.'),
 ('CAT-07','Tilta Hydra Car Mount','Acessório Cinema','Tilta','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.42. Ventosas eletrônicas, carga 20 kg.'),
 ('CAT-08','Tilta Shoulder Rig LWS 15mm','Acessório Cinema','Tilta','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.43.'),
 ('CAT-09','Hollyland M2','Áudio','Hollyland','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.62. Inventário tem Lark Max 1 e 2, não tem M2.'),
 ('CAT-10','Deity TC-SL1 Timecode Smart Slate','Áudio','Deity','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.66. Inventário tem 3x TC-1, não tem a claquete.'),
 ('CAT-11','Blackmagic ATEM Mini Pro','Monitor/Wireless','Blackmagic','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.79. Switcher de 4 canais para live.'),
 ('CAT-12','Teleprompter para iPad','Produção','Genérico','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.80.'),
 ('CAT-13','Baofeng BF-777s (kit 6 rádios)','Comunicação','Baofeng','bloqueado',false,'catalogo:2026-02',
  'Catálogo p.83. Kit com 6 unidades — controlar por quantidade, não por série.'),
 ('CAT-14','ProAim Bag','Case/Proteção','ProAim','bloqueado',true,'catalogo:2026-02',
  'Catálogo p.70.')
ON CONFLICT (codigo) DO UPDATE SET nome = EXCLUDED.nome, observacoes = EXCLUDED.observacoes;

UPDATE asset SET quantidade = 6 WHERE codigo = 'CAT-13';

-- Divergência séria, não é item novo: o catálogo (p.41) descreve um ProAim Breeza Dolly Slider
-- com 16 rodas, trilhos, mala e cabeça SmallRig DH12. O inventário tem "Jingmei Dolly Slider
-- Rodas" a R$ 360 — que não paga um ProAim Breeza. Ou o cadastro está errado, ou são dois itens.
UPDATE asset SET status = 'bloqueado',
  observacoes = 'CONFERIR: catálogo p.41 anuncia ProAim Breeza (trilhos + mala + cabeça DH12). '
                'Cadastro diz Jingmei a R$ 360. Valor de reposição e preço de locação estão errados '
                'em um dos dois lados.'
 WHERE codigo = '0091';
