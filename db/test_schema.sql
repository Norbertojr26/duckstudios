\set ON_ERROR_STOP off
INSERT INTO asset (codigo,nome,categoria,valor_reposicao,valor_diaria)
  VALUES ('DS-CAM-001','Sony FX3','camera',45000,600);
INSERT INTO company (nome,tipo) VALUES ('Cliente A','cliente'),('Cliente B','cliente');

-- Reserva 1: confirmada 10/09 a 12/09
INSERT INTO rental (company_id,inicio,fim,status)
  SELECT id,'2026-09-10','2026-09-12','confirmado' FROM company WHERE nome='Cliente A';
INSERT INTO rental_line (rental_id,asset_id,during,status)
  SELECT r.id,a.id,tstzrange('2026-09-10','2026-09-12'),'confirmado'
  FROM rental r, asset a WHERE a.codigo='DS-CAM-001' LIMIT 1;

-- Reserva 2: sobreposta (11/09 a 13/09) -> DEVE FALHAR
INSERT INTO rental (company_id,inicio,fim,status)
  SELECT id,'2026-09-11','2026-09-13','confirmado' FROM company WHERE nome='Cliente B';
\echo '>>> tentando overbooking (deve falhar):'
INSERT INTO rental_line (rental_id,asset_id,during,status)
  SELECT r.id,a.id,tstzrange('2026-09-11','2026-09-13'),'confirmado'
  FROM rental r JOIN company c ON c.id=r.company_id, asset a
  WHERE c.nome='Cliente B' AND a.codigo='DS-CAM-001';

\echo '>>> reserva nao sobreposta (deve passar):'
INSERT INTO rental_line (rental_id,asset_id,during,status)
  SELECT r.id,a.id,tstzrange('2026-09-13','2026-09-15'),'confirmado'
  FROM rental r JOIN company c ON c.id=r.company_id, asset a
  WHERE c.nome='Cliente B' AND a.codigo='DS-CAM-001';

\echo '>>> asset_disponivel 10-12 (esperado f) / 20-22 (esperado t):'
SELECT asset_disponivel(id,'2026-09-10','2026-09-12') AS ocupado,
       asset_disponivel(id,'2026-09-20','2026-09-22') AS livre FROM asset;

\echo '>>> deal perdido sem motivo (deve falhar):'
INSERT INTO deal (titulo,estagio) VALUES ('Teste','perdido');
\echo '>>> deal perdido com motivo (deve passar):'
INSERT INTO deal (titulo,estagio,motivo_perda) VALUES ('Teste','perdido','preco');
