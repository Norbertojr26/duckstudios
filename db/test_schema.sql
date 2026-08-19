-- Teste de fumaça. Requer BANCO NOVO (as asserções contam registros).
--   createdb duck && psql -d duck -f db/schema.sql && psql -d duck -f db/test_schema.sql
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

-- --- MVP de conferência: saída, view "em campo" e idempotência de sincronização ---
UPDATE rental_line SET status='em_campo' WHERE during && tstzrange('2026-09-10','2026-09-12');
UPDATE rental SET status='em_campo', tipo='emprestimo', responsavel_nome='Videomaker da campanha',
       checkout_at=now(), previsao_devolucao=now()-interval '2 hours'
 WHERE inicio='2026-09-10';
\echo '>>> equipamento_em_campo (esperado 1 linha, atrasado=t):'
SELECT responsavel, codigo, atrasado FROM equipamento_em_campo;

\echo '>>> conferencia de saida (deve passar):'
INSERT INTO conference_check (rental_id,asset_id,momento,estado,operador,client_uuid)
  SELECT rl.rental_id, rl.asset_id,'saida','ok','operador',
         '11111111-1111-1111-1111-111111111111'
  FROM rental_line rl WHERE rl.status='em_campo';
\echo '>>> mesma bipada sincronizada de novo (deve falhar por client_uuid duplicado):'
INSERT INTO conference_check (rental_id,asset_id,momento,estado,operador,client_uuid)
  SELECT rl.rental_id, rl.asset_id,'saida','ok','operador',
         '11111111-1111-1111-1111-111111111111'
  FROM rental_line rl WHERE rl.status='em_campo';
