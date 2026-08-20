-- Duck Studios CRM — schema base (PostgreSQL 16)
-- Rascunho de referência: cobre CRM + produção + locação + auditoria de agentes.
-- Aplicar: psql -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- necessário para EXCLUDE com igualdade + range

-- =============================================================================
-- 1. CRM — pessoas e empresas
-- =============================================================================

CREATE TABLE company (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            text NOT NULL,
    cnpj            text UNIQUE,
    tipo            text CHECK (tipo IN ('cliente','fornecedor','parceiro','ambos')),
    endereco        jsonb,
    observacoes     text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE contact (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid REFERENCES company(id),
    nome            text NOT NULL,
    cargo           text,
    email           text,
    telefone_e164   text,                       -- normalizado: dedupe do agente depende disso
    cpf             text,
    origem          text,                       -- whatsapp | instagram | indicacao | site | ...
    criado_em       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (telefone_e164),
    UNIQUE (email)
);

-- =============================================================================
-- 2. Comercial — funil e propostas
-- =============================================================================

CREATE TABLE deal (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      uuid REFERENCES contact(id),
    company_id      uuid REFERENCES company(id),
    titulo          text NOT NULL,
    tipo_servico    text CHECK (tipo_servico IN ('filmagem','edicao','locacao','pacote','outro')),
    estagio         text NOT NULL DEFAULT 'novo'
                    CHECK (estagio IN ('novo','qualificado','proposta_enviada','negociacao','ganho','perdido')),
    valor_estimado  numeric(12,2),
    data_evento     date,
    local_evento    text,
    prazo_entrega   date,
    motivo_perda    text,                       -- obrigatório quando estagio='perdido' (ver trigger)
    responsavel     text,
    criado_em       timestamptz NOT NULL DEFAULT now(),
    atualizado_em   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE price_list (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo          text UNIQUE NOT NULL,
    descricao       text NOT NULL,
    unidade         text NOT NULL,              -- diaria | hora | km | mes | unidade | pacote | percentual
    valor           numeric(12,2) NOT NULL,
    categoria       text,                       -- servico | pos | locacao | deslocamento
                                                -- | licenciamento | extra | retainer
    ativo           boolean NOT NULL DEFAULT true
);

CREATE TABLE quote (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id         uuid NOT NULL REFERENCES deal(id),
    numero          text UNIQUE,
    versao          int NOT NULL DEFAULT 1,
    status          text NOT NULL DEFAULT 'rascunho'
                    CHECK (status IN ('rascunho','aguardando_aprovacao_interna','enviada','aceita','recusada','expirada')),
    validade        date,
    subtotal        numeric(12,2),
    desconto        numeric(12,2) DEFAULT 0,
    total           numeric(12,2),
    pdf_path        text,
    criado_por      text,                       -- 'humano:nome' | 'agente:comercial'
    aprovado_por    text,                       -- NULL enquanto não houve aprovação humana
    criado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE quote_item (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id        uuid NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
    price_list_id   uuid REFERENCES price_list(id),  -- NULL = item fora de tabela: exige aprovação
    descricao       text NOT NULL,
    quantidade      numeric(10,2) NOT NULL,
    valor_unitario  numeric(12,2) NOT NULL,
    total           numeric(12,2) GENERATED ALWAYS AS (quantidade * valor_unitario) STORED
);

-- =============================================================================
-- 3. Produção — projetos, diárias, entregas
-- =============================================================================

CREATE TABLE project (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id         uuid REFERENCES deal(id),
    company_id      uuid REFERENCES company(id),
    slug            text UNIQUE NOT NULL,       -- usado no caminho de pastas da mídia
    nome            text NOT NULL,
    status          text NOT NULL DEFAULT 'ativo'
                    CHECK (status IN ('ativo','pausado','concluido','arquivado','cancelado')),
    data_inicio     date,
    data_entrega    date,
    valor_contrato  numeric(12,2),
    pasta_raiz      text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE shoot_day (                        -- diária de filmagem
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES project(id),
    data            date NOT NULL,
    numero          int NOT NULL,               -- DIARIA_NN
    local           text,
    observacoes     text,
    UNIQUE (project_id, data, numero)
);

CREATE TABLE deliverable (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES project(id),
    nome            text NOT NULL,
    formato         text,                       -- 16:9 | 9:16 | 1:1
    duracao_seg     int,
    versao_atual    int NOT NULL DEFAULT 0,
    status          text NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','em_edicao','em_revisao','aprovado','entregue')),
    prazo           date
);

CREATE TABLE deliverable_version (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id  uuid NOT NULL REFERENCES deliverable(id) ON DELETE CASCADE,
    versao          int NOT NULL,
    arquivo_path    text,
    link_review     text,
    enviado_em      timestamptz,
    feedback        text,
    aprovado        boolean,
    UNIQUE (deliverable_id, versao)
);

-- =============================================================================
-- 4. Mídia — ligação entre o mundo DIT e o CRM (SOP-001)
-- =============================================================================

CREATE TABLE media_offload (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid NOT NULL REFERENCES project(id),
    shoot_day_id        uuid REFERENCES shoot_day(id),
    card_uuid           text NOT NULL,          -- identificador do volume/cartão
    camera              text NOT NULL,
    card_numero         int NOT NULL DEFAULT 1,
    status              text NOT NULL DEFAULT 'em_progresso'
                        CHECK (status IN ('em_progresso','verificado','parcial','falha','interrompido')),
    arquivos_total      int,
    bytes_total         bigint,
    destinos            jsonb NOT NULL DEFAULT '[]',   -- [{path, verificado_em, mhl_path}]
    divergencias        jsonb NOT NULL DEFAULT '[]',
    liberado_para_format boolean NOT NULL DEFAULT false, -- só humano formata, mesmo com true
    iniciado_em         timestamptz NOT NULL DEFAULT now(),
    concluido_em        timestamptz,
    trace_id            uuid,
    UNIQUE (card_uuid, project_id, shoot_day_id)
);

CREATE TABLE media_file (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    offload_id      uuid NOT NULL REFERENCES media_offload(id) ON DELETE CASCADE,
    caminho_relativo text NOT NULL,
    nome_original   text NOT NULL,
    bytes           bigint NOT NULL,
    hash_xxh64      text NOT NULL,
    codec           text,
    resolucao       text,
    fps             numeric(6,3),
    duracao_seg     numeric(10,3),
    timecode_inicio text,
    metadados       jsonb,
    proxy_path      text,
    verificado_em   jsonb NOT NULL DEFAULT '{}',   -- {destino: timestamp}
    UNIQUE (offload_id, caminho_relativo)
);

-- =============================================================================
-- 5. Locação — inventário e reservas (o coração do rental)
-- =============================================================================

CREATE TABLE asset (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo              text UNIQUE NOT NULL,   -- etiqueta física: DS-CAM-001
    nome                text NOT NULL,
    categoria           text NOT NULL,          -- categorias reais do studio; ver db/seed_inventario.sql
    marca               text,
    modelo              text,
    numero_serie        text,
    valor_aquisicao     numeric(12,2),          -- o que custou (vem do AssetTiger)
    valor_reposicao     numeric(12,2),          -- quanto custa repor HOJE — é este que vai no termo
    valor_diaria        numeric(12,2),
    valor_semanal       numeric(12,2),
    valor_mensal        numeric(12,2),
    -- false enquanto valor_reposicao for estimativa. O termo de responsabilidade
    -- avisa quando o valor ainda não foi confirmado por um humano.
    valor_reposicao_confirmado boolean NOT NULL DEFAULT false,
    data_aquisicao      date,
    -- Case/maleta que contém este item. Permite conferir "o case 0074" e expandir no conteúdo.
    container_id        uuid REFERENCES asset(id),
    e_container         boolean NOT NULL DEFAULT false,
    status              text NOT NULL DEFAULT 'disponivel'
                        CHECK (status IN ('disponivel','em_campo','manutencao','bloqueado','baixado')),
    serializado         boolean NOT NULL DEFAULT true,   -- false = consumível controlado por qtd
    quantidade          int NOT NULL DEFAULT 1,
    observacoes         text,
    origem_import       text                    -- ex: 'assettiger:2026-08' para rastrear a carga
);
CREATE INDEX ON asset (container_id) WHERE container_id IS NOT NULL;

CREATE TABLE kit (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            text UNIQUE NOT NULL,
    descricao       text,
    valor_diaria    numeric(12,2)
);

CREATE TABLE kit_item (
    kit_id          uuid NOT NULL REFERENCES kit(id) ON DELETE CASCADE,
    asset_id        uuid NOT NULL REFERENCES asset(id),
    quantidade      int NOT NULL DEFAULT 1,
    PRIMARY KEY (kit_id, asset_id)
);

CREATE TABLE rental (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id         uuid REFERENCES deal(id),
    company_id      uuid REFERENCES company(id),
    contact_id      uuid REFERENCES contact(id),
    project_id      uuid REFERENCES project(id),      -- locação para job interno
    numero          text UNIQUE,
    -- Distinguir isto é o que impede relatório de faturamento e ocupação virarem ficção.
    tipo            text NOT NULL DEFAULT 'locacao_paga'
                    CHECK (tipo IN ('locacao_paga','emprestimo','uso_interno','subcontratacao')),
    responsavel_nome text,                            -- quem fisicamente levou (pode não ser o contato)
    previsao_devolucao timestamptz,
    status          text NOT NULL DEFAULT 'hold'
                    CHECK (status IN ('hold','confirmado','em_campo','devolvido','cancelado')),
    inicio          timestamptz NOT NULL,
    fim             timestamptz NOT NULL,
    valor_total     numeric(12,2),
    caucao          numeric(12,2),
    termo_path      text,
    termo_assinado_em timestamptz,
    assinatura_path text,                             -- assinatura coletada na tela do celular
    checkout_at     timestamptz,
    checkin_at      timestamptz,
    criado_em       timestamptz NOT NULL DEFAULT now(),
    CHECK (fim > inicio)
);

-- Uma linha por item reservado. `during` inclui o buffer de vistoria pós-devolução.
CREATE TABLE rental_line (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id       uuid NOT NULL REFERENCES rental(id) ON DELETE CASCADE,
    asset_id        uuid NOT NULL REFERENCES asset(id),
    kit_id          uuid REFERENCES kit(id),          -- se veio via kit, rastreia a origem
    during          tstzrange NOT NULL,
    status          text NOT NULL DEFAULT 'hold'
                    CHECK (status IN ('hold','confirmado','em_campo','devolvido','cancelado')),
    valor_diaria    numeric(12,2),
    -- >>> Impede overbooking no nível do banco. Nem um bug do agente atravessa isto. <<<
    EXCLUDE USING gist (
        asset_id WITH =,
        during   WITH &&
    ) WHERE (status IN ('confirmado','em_campo'))
);

-- Cada bipada de QR na conferência de saída ou de retorno (MVP de conferência).
-- client_uuid vem do celular e garante sincronização idempotente depois de operar offline.
CREATE TABLE conference_check (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id       uuid NOT NULL REFERENCES rental(id) ON DELETE CASCADE,
    asset_id        uuid NOT NULL REFERENCES asset(id),
    momento         text NOT NULL CHECK (momento IN ('saida','retorno')),
    quantidade      int NOT NULL DEFAULT 1,           -- itens não serializados
    estado          text CHECK (estado IN ('ok','danificado','faltando')),
    observacao      text,
    fotos           jsonb NOT NULL DEFAULT '[]',
    operador        text NOT NULL,                    -- quem conferiu (pode não ser o dono)
    client_uuid     uuid NOT NULL UNIQUE,             -- idempotência na sincronização offline
    registrado_em   timestamptz NOT NULL DEFAULT now(),
    sincronizado_em timestamptz NOT NULL DEFAULT now(),
    UNIQUE (rental_id, asset_id, momento)
);
CREATE INDEX ON conference_check (rental_id, momento);

CREATE TABLE damage_report (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rental_id       uuid REFERENCES rental(id),
    asset_id        uuid NOT NULL REFERENCES asset(id),
    descricao       text NOT NULL,
    gravidade       text CHECK (gravidade IN ('cosmetico','funcional','inutilizavel','perda')),
    fotos           jsonb NOT NULL DEFAULT '[]',
    custo_estimado  numeric(12,2),
    cobrado_do_cliente boolean NOT NULL DEFAULT false,  -- decisão humana, nunca do agente
    registrado_em   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE maintenance_log (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id        uuid NOT NULL REFERENCES asset(id),
    tipo            text CHECK (tipo IN ('preventiva','corretiva','limpeza','calibracao','firmware')),
    descricao       text,
    custo           numeric(12,2),
    executado_em    date,
    proxima_em      date
);

-- =============================================================================
-- 6. Financeiro
-- =============================================================================

CREATE TABLE invoice (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid REFERENCES project(id),
    rental_id       uuid REFERENCES rental(id),
    company_id      uuid REFERENCES company(id),
    numero          text,
    valor           numeric(12,2) NOT NULL,
    emitida_em      date,
    vencimento      date,
    status          text NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','emitida','paga','vencida','cancelada')),
    nf_path         text
);

CREATE TABLE expense (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid REFERENCES project(id),
    shoot_day_id    uuid REFERENCES shoot_day(id),
    categoria       text NOT NULL,              -- freela | alimentacao | transporte | locacao_terceiro | equipamento
    descricao       text,
    valor           numeric(12,2) NOT NULL,
    data            date NOT NULL,
    fornecedor_id   uuid REFERENCES company(id),
    comprovante_path text,
    classificado_por text                       -- 'agente:financeiro' quando automático
);

-- =============================================================================
-- 7. Agentes — auditoria, aprovações, fila e outbox
-- =============================================================================

CREATE TABLE agent_run (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id            uuid NOT NULL,
    agente              text NOT NULL,
    sop_id              text,                   -- SOP-001, ...
    gatilho             text NOT NULL,
    entrada             jsonb,
    saida               jsonb,
    status              text NOT NULL DEFAULT 'em_progresso'
                        CHECK (status IN ('em_progresso','sucesso','parcial','falha','escalado','cancelado')),
    modelo              text,
    tokens_entrada      int,
    tokens_saida        int,
    custo_usd           numeric(10,4),
    iniciado_em         timestamptz NOT NULL DEFAULT now(),
    concluido_em        timestamptz
);

CREATE TABLE agent_action (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL REFERENCES agent_run(id) ON DELETE CASCADE,
    sequencia       int NOT NULL,
    tool            text NOT NULL,
    argumentos      jsonb,
    resultado       jsonb,
    nivel_autonomia text CHECK (nivel_autonomia IN ('A0','A1','A2','A3','A4')),
    aprovado_por    text,
    erro            text,
    executado_em    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequencia)
);

CREATE TABLE approval_request (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid REFERENCES agent_run(id),
    titulo          text NOT NULL,
    descricao       text NOT NULL,
    payload         jsonb NOT NULL,             -- a ação exata que será executada se aprovada
    status          text NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','aprovado','rejeitado','expirado')),
    decidido_por    text,
    decidido_em     timestamptz,
    expira_em       timestamptz,
    criado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE job_queue (
    id              bigserial PRIMARY KEY,
    tipo            text NOT NULL,
    payload         jsonb NOT NULL,
    status          text NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','processando','concluido','falha')),
    tentativas      int NOT NULL DEFAULT 0,
    max_tentativas  int NOT NULL DEFAULT 3,
    disponivel_em   timestamptz NOT NULL DEFAULT now(),
    erro            text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON job_queue (status, disponivel_em) WHERE status = 'pendente';

-- Nada sai da máquina de forma síncrona: tudo passa por aqui e é entregue quando houver rede.
CREATE TABLE outbox (
    id              bigserial PRIMARY KEY,
    canal           text NOT NULL,              -- email | whatsapp | telegram | webhook
    destino         text NOT NULL,
    assunto         text,
    corpo           text NOT NULL,
    anexos          jsonb NOT NULL DEFAULT '[]',
    status          text NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','enviado','falha','cancelado')),
    aprovado_por    text,                       -- mensagem a cliente exige aprovação humana
    tentativas      int NOT NULL DEFAULT 0,
    criado_em       timestamptz NOT NULL DEFAULT now(),
    enviado_em      timestamptz
);

-- Timeline unificada: notas, ligações, mensagens, eventos automáticos
CREATE TABLE activity (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entidade_tipo   text NOT NULL,              -- deal | project | rental | contact | asset
    entidade_id     uuid NOT NULL,
    tipo            text NOT NULL,              -- nota | email | ligacao | mensagem | evento_sistema
    conteudo        text,
    autor           text,                       -- 'humano:nome' | 'agente:comercial'
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON activity (entidade_tipo, entidade_id, criado_em DESC);

-- =============================================================================
-- 8. Regras auxiliares
-- =============================================================================

CREATE OR REPLACE FUNCTION exigir_motivo_perda() RETURNS trigger AS $$
BEGIN
    IF NEW.estagio = 'perdido' AND (NEW.motivo_perda IS NULL OR NEW.motivo_perda = '') THEN
        RAISE EXCEPTION 'deal perdido exige motivo_perda';
    END IF;
    NEW.atualizado_em := now();
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_deal_motivo_perda
    BEFORE INSERT OR UPDATE ON deal
    FOR EACH ROW EXECUTE FUNCTION exigir_motivo_perda();

-- Disponibilidade de um item num período (usada pelo rental-mcp)
CREATE OR REPLACE FUNCTION asset_disponivel(p_asset_id uuid, p_inicio timestamptz, p_fim timestamptz)
RETURNS boolean AS $$
    SELECT NOT EXISTS (
        SELECT 1 FROM rental_line rl
        WHERE rl.asset_id = p_asset_id
          AND rl.status IN ('confirmado','em_campo')
          AND rl.during && tstzrange(p_inicio, p_fim)
    ) AND (SELECT status IN ('disponivel','em_campo') FROM asset WHERE id = p_asset_id);
$$ LANGUAGE sql STABLE;

-- Responde "quem está com o quê, agora" — a tela inicial do app de conferência.
CREATE OR REPLACE VIEW equipamento_em_campo AS
SELECT r.id                AS rental_id,
       r.tipo,
       COALESCE(r.responsavel_nome, c.nome, co.nome) AS responsavel,
       a.codigo,
       a.nome              AS equipamento,
       r.checkout_at,
       r.previsao_devolucao,
       (now() > r.previsao_devolucao) AS atrasado
FROM rental r
JOIN rental_line rl ON rl.rental_id = r.id AND rl.status = 'em_campo'
JOIN asset a        ON a.id = rl.asset_id
LEFT JOIN contact c ON c.id = r.contact_id
LEFT JOIN company co ON co.id = r.company_id
WHERE r.status = 'em_campo';
