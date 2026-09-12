"""Minutas de contrato do audiovisual — templates determinísticos.

Por que sem LLM: cláusula de contrato não pode variar por criatividade de modelo. O texto
sai de templates revisáveis neste arquivo, preenchidos com os dados da proposta (itens,
valores ditados pelo humano, etapas, condições) e das partes. Referências legais usadas:
Código Civil (arts. 593+ prestação de serviços, 565+ locação de coisas, 393 força maior,
20 direito de imagem), Lei 9.610/98 (direitos autorais) e Lei 13.709/2018 (LGPD).

É MINUTA: o rodapé de toda impressão avisa que deve ser revisada por advogado antes de
assinar — o sistema prepara, o humano responde pelo que assina.
"""


def _brl(v):
    if v is None:
        return "[PREENCHER]"
    return f"R$ {float(v):,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")


def _campo(d, chave):
    v = (d.get(chave) or "").strip()
    return v or "[PREENCHER]"


def _parte(rotulo, d):
    return (f"{rotulo}: {_campo(d, 'razao')}, inscrita no CNPJ/CPF sob o nº "
            f"{_campo(d, 'documento')}, com sede/endereço em {_campo(d, 'endereco')}, "
            f"neste ato representada por {_campo(d, 'representante')}, "
            f"CPF nº {_campo(d, 'rep_documento')}, e-mail {_campo(d, 'email')}, "
            f"doravante \"{rotulo}\".")


def _itens_texto(itens):
    if not itens:
        return "    (itens conforme proposta comercial anexa)"
    return "\n".join(f"    {chr(97 + n)}) {i['descricao']} — "
                     f"{float(i['quantidade']):g} × {_brl(i['valor_unitario'])};"
                     for n, i in enumerate(itens))


def _etapas_texto(etapas):
    if not etapas:
        return ("§1º Os prazos de execução e entrega serão os acordados por escrito entre "
                "as partes.")
    linhas = [f"    {n + 1}. {e['titulo']}"
              + (f" — {e['detalhe']}" if e.get("detalhe") else "")
              + (f" (prazo: {e['prazo']})" if e.get("prazo") else "")
              for n, e in enumerate(etapas)]
    return ("§1º A execução seguirá as etapas e prazos abaixo, contados na forma do §2º:\n"
            + "\n".join(linhas))


# --------------------------------------------------------------- cláusulas comuns

def _clausulas_comuns(q, itens, inicio=2):
    """Do valor em diante, o esqueleto é o mesmo para todo serviço; muda o objeto."""
    n = inicio
    condicoes = q.get("condicoes_pagamento") or "[PREENCHER condições de pagamento]"
    etapas = q.get("etapas") or []
    partes = []

    partes.append(f"""CLÁUSULA {n}ª — VALOR E FORMA DE PAGAMENTO
Pelo objeto deste contrato, a CONTRATANTE pagará à CONTRATADA o valor total de
{_brl(q.get('total'))}, conforme a proposta comercial nº {q.get('numero') or '[PREENCHER]'},
que integra este instrumento como anexo.
§1º Condições de pagamento: {condicoes}.
§2º O atraso no pagamento sujeita a CONTRATANTE a multa de 2% (dois por cento) sobre o valor
em aberto, juros de mora de 1% (um por cento) ao mês e correção monetária pelo IPCA.
§3º Valores de itens marcados como estimativa na proposta serão confirmados por escrito antes
da execução do item correspondente.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — PRAZOS E ETAPAS DE EXECUÇÃO
{_etapas_texto(etapas)}
§2º Os prazos que dependem de aprovação, retorno ou fornecimento de material pela CONTRATANTE
contam-se a partir do respectivo cumprimento; o atraso da CONTRATANTE prorroga automaticamente
os prazos subsequentes em igual período.
§3º Rodadas de ajuste excedentes às previstas nas etapas serão orçadas à parte, mediante
aprovação prévia da CONTRATANTE.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — OBRIGAÇÕES DA CONTRATADA
a) executar os serviços com equipe e equipamento profissionais adequados ao escopo;
b) manter o material captado em, no mínimo, duas cópias de segurança independentes até a
entrega final aprovada;
c) guardar sigilo sobre informações não públicas da CONTRATANTE a que tiver acesso;
d) comunicar de imediato qualquer fato que possa comprometer prazo ou qualidade;
e) emitir os documentos fiscais correspondentes aos valores recebidos.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — OBRIGAÇÕES DA CONTRATANTE
a) fornecer, nos prazos combinados, as informações, aprovações, acessos e materiais
necessários à execução;
b) garantir, quando o serviço ocorrer em local por ela indicado, acesso da equipe, ponto de
energia e condições seguras de trabalho;
c) responder pela titularidade e pela autorização de uso de todo material por ela fornecido
(marcas, imagens, textos, áudios), isentando a CONTRATADA de reclamações de terceiros quanto
a esse material;
d) realizar os pagamentos na forma da cláusula de valor.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — DIREITOS AUTORAIS (LEI 9.610/98)
§1º Com a quitação integral, a CONTRATANTE recebe licença de uso do material FINAL entregue,
em caráter definitivo, para as finalidades previstas no objeto deste contrato.
§2º O material bruto (arquivos de captação) permanece sob guarda e titularidade da
CONTRATADA, salvo cessão expressa e por escrito.
§3º A CONTRATADA poderá exibir o material final em seu portfólio e redes, mediante
autorização da CONTRATANTE, que pode ser revogada por escrito a qualquer tempo.
§4º Trilhas sonoras serão utilizadas conforme as licenças das plataformas contratadas pela
CONTRATADA; uso de fonograma comercial de terceiros depende de licenciamento próprio, por
conta da CONTRATANTE.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — IMAGEM, VOZ E PROTEÇÃO DE DADOS (ART. 20 CC E LGPD)
§1º A CONTRATANTE é responsável por obter as autorizações de uso de imagem e voz das pessoas
que indicar ou fizer participar da produção; a CONTRATADA fornecerá modelo de termo quando
solicitado.
§2º Os dados pessoais tratados em razão deste contrato serão utilizados exclusivamente para
sua execução, nos termos da Lei nº 13.709/2018 (LGPD), e eliminados ou anonimizados quando
deixarem de ser necessários, ressalvadas obrigações legais de guarda.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — RESCISÃO
§1º Qualquer parte pode rescindir este contrato por descumprimento da outra, mediante
notificação escrita e prazo de 5 (cinco) dias úteis para regularização.
§2º Em caso de desistência da CONTRATANTE após o início da execução, serão devidos os
serviços já executados e os custos incorridos, além de multa compensatória de 20% (vinte por
cento) sobre o saldo remanescente do contrato.
§3º Sinal e parcelas pagas relativas a serviços já executados não são reembolsáveis.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — CASO FORTUITO E FORÇA MAIOR (ART. 393 CC)
Nenhuma das partes responde por descumprimento decorrente de caso fortuito ou força maior.
Sendo possível, o serviço será reagendado sem penalidade; sendo impossível a execução, os
valores pagos por serviços não executados serão restituídos, deduzidos custos já incorridos
e comprovados.""")
    n += 1

    partes.append(f"""CLÁUSULA {n}ª — DISPOSIÇÕES GERAIS E FORO
§1º Este contrato obriga as partes e seus sucessores; alterações somente por escrito.
§2º A tolerância quanto a qualquer descumprimento não implica renúncia de direito.
§3º Fica eleito o foro da Circunscrição Judiciária de Brasília/DF para dirimir quaisquer
controvérsias oriundas deste contrato, com renúncia a qualquer outro.""")

    return "\n\n".join(partes)


# ------------------------------------------------------------------ templates

def _obj_edicao(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de EDIÇÃO E PÓS-PRODUÇÃO DE VÍDEO, compreendendo montagem, tratamento
de cor, mixagem básica de áudio e finalização, a partir de material bruto fornecido pela
CONTRATANTE, conforme os itens da proposta:
{_itens_texto(itens)}
§1º A CONTRATANTE entregará o material bruto organizado e em mídia/link acordado; a
integridade e a titularidade do material fornecido são de sua responsabilidade.
§2º Entregas em formatos e versões (resolução, cortes para redes) conforme a proposta."""


def _obj_casamento(q, itens):
    data = q.get("data_evento")
    data_txt = data.strftime("%d/%m/%Y") if data else "[PREENCHER data do evento]"
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de COBERTURA AUDIOVISUAL DE CASAMENTO a realizar-se em {data_txt},
compreendendo captação de imagens e áudio do evento e pós-produção, conforme os itens da
proposta:
{_itens_texto(itens)}
§1º O evento é único e irrepetível: a obrigação da CONTRATADA quanto à captação de momentos
específicos é de meio, executada com diligência profissional, dupla captação de segurança do
material e equipe de prontidão para substituição em emergência.
§2º A CONTRATANTE garantirá à equipe acesso aos locais do evento, e refeição quando a
cobertura exceder 6 (seis) horas contínuas.
§3º Alterações de data sujeitam-se à agenda da CONTRATADA; havendo disponibilidade, o
reagendamento comunicado com 30 (trinta) dias de antecedência não gera custo adicional."""


def _obj_cobertura(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de COBERTURA AUDIOVISUAL DE EVENTO, compreendendo captação de imagens
e áudio e pós-produção, conforme os itens da proposta:
{_itens_texto(itens)}
§1º A cobertura de momentos específicos constitui obrigação de meio, executada com
diligência profissional e captação de segurança do material.
§2º A CONTRATANTE garantirá credenciamento e acesso da equipe a todas as áreas necessárias
do evento, e refeição quando a cobertura exceder 6 (seis) horas contínuas."""


def _obj_locacao(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
LOCAÇÃO DE EQUIPAMENTO CINEMATOGRÁFICO (arts. 565 e seguintes do Código Civil), pelos
períodos e valores da proposta:
{_itens_texto(itens)}
§1º O equipamento será entregue conferido e em perfeito funcionamento, mediante termo de
retirada com checklist assinado pelas partes; a devolução observa o mesmo procedimento.
§2º Durante a locação, a CONTRATANTE responde pela guarda, transporte e uso adequado do
equipamento, e por perda, furto, roubo ou dano, pelo valor de reposição constante do termo
de responsabilidade que integra este contrato.
§3º Atraso na devolução gera cobrança de diária adicional por dia de atraso, sem prejuízo de
perdas e danos.
§4º É vedado sublocar, emprestar ou ceder o equipamento sem anuência escrita da CONTRATADA.
§5º A locação não inclui operador, salvo item expresso na proposta."""


def _obj_gravacao_edicao(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de PRODUÇÃO AUDIOVISUAL COMPLETA (captação e pós-produção),
compreendendo planejamento, diária(s) de gravação com equipe e equipamento profissionais,
edição, tratamento de cor, mixagem básica e finalização, conforme os itens da proposta:
{_itens_texto(itens)}
§1º Diárias de gravação excedentes, locações de cenário, elenco e demais itens não previstos
na proposta serão orçados à parte.
§2º Entregas em formatos e versões (resolução, cortes para redes) conforme a proposta."""


def _obj_filme(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de PRODUÇÃO DE FILME PUBLICITÁRIO/INSTITUCIONAL, compreendendo
desenvolvimento a partir de briefing aprovado, pré-produção, diária(s) de gravação,
pós-produção e finalização, conforme os itens da proposta:
{_itens_texto(itens)}
§1º Roteiro e diretrizes criativas serão submetidos à aprovação escrita da CONTRATANTE antes
da gravação; alterações de escopo após aprovação serão orçadas à parte.
§2º A licença de uso do filme final abrange os canais e finalidades indicados na proposta;
veiculação em mídia paga de fonograma ou imagem de terceiros depende dos respectivos
licenciamentos, por conta da CONTRATANTE.
§3º Participação de elenco, locução e trilha original, quando contratadas, observarão os
termos e prazos das respectivas cessões."""


def _obj_curta(q, itens):
    return f"""CLÁUSULA 1ª — OBJETO
Prestação de serviços de PRODUÇÃO DE CURTA-METRAGEM, compreendendo as etapas e itens da
proposta:
{_itens_texto(itens)}
§1º Os créditos da obra observarão as funções efetivamente exercidas, garantido o crédito da
CONTRATADA nas funções técnicas e artísticas que desempenhar (art. 24 da Lei 9.610/98 —
direitos morais são irrenunciáveis e intransferíveis).
§2º A titularidade patrimonial da obra e a estratégia de inscrição em festivais e mostras
serão as definidas no anexo de titularidade; na sua ausência, dependem de acordo escrito
entre as partes.
§3º Cada parte responde pelas autorizações e cessões que lhe couberem (elenco, locações,
obras preexistentes)."""


TEMPLATES = {
    "edicao": ("Contrato de Prestação de Serviços — Edição de Vídeo", _obj_edicao),
    "casamento": ("Contrato de Cobertura Audiovisual — Casamento", _obj_casamento),
    "cobertura": ("Contrato de Cobertura Audiovisual — Evento", _obj_cobertura),
    "locacao": ("Contrato de Locação de Equipamento Cinematográfico", _obj_locacao),
    "gravacao_edicao": ("Contrato de Produção Audiovisual — Gravação + Edição",
                        _obj_gravacao_edicao),
    "filme": ("Contrato de Produção — Filme Publicitário/Institucional", _obj_filme),
    "curta": ("Contrato de Produção — Curta-Metragem", _obj_curta),
}

# tipo_servico do negócio → template sugerido (o humano pode trocar no formulário)
SUGESTAO_POR_SERVICO = {"filmagem": "cobertura", "edicao": "edicao", "locacao": "locacao",
                        "pacote": "gravacao_edicao", "outro": "gravacao_edicao"}


def montar(chave, q, itens, contratante, contratada):
    """(titulo, corpo) da minuta — texto plano, editável na tela antes de imprimir."""
    titulo, objeto = TEMPLATES[chave]
    corpo = "\n\n".join([
        _parte("CONTRATANTE", contratante),
        _parte("CONTRATADA", contratada),
        "As partes celebram o presente contrato, que se regerá pelas cláusulas seguintes:",
        objeto(q, itens),
        _clausulas_comuns(q, itens),
        """E, por estarem justas e contratadas, as partes assinam o presente em 2 (duas) vias
de igual teor, na presença das testemunhas abaixo.""",
    ])
    return titulo, corpo
