import re
from typing import List, Dict
from app.models.models import Entity, Relationship, IndicatorType

# Marcadores usados para classificar cada Finding num tipo de entidade do
# grafo (Seção 18 da arquitetura). Mapeados nos nomes de campo reais que os
# collectors emitem hoje — ver backend/app/collectors/*.
FIELD_TYPE_RULES = [
    ("Email", ["e-mail", "email"]),
    ("Company", ["razão social", "empresa", "qsa", "nome fantasia", "cnpj"]),
    ("Domain", ["domínio", "hospedagem"]),
    ("URL", ["url", "página", "site", "link"]),
    ("Phone", ["telefone", "linha telefônica", "whatsapp"]),
    ("IP", [" ip ", "ip:", "endereço ip", "provedor de internet"]),
    ("PixKey", ["chave pix", "dict"]),
    ("SocialProfile", ["github", "presença pública em", "perfil"]),
    ("Person", ["titular", "identidade", "nome completo"]),
    ("PublicRecord", ["sanção", "ceis", "cnep", "diário", "citação"]),
]


class EntityResolutionEngine:
    """
    Engine responsável por agrupar os Findings coletados em entidades e
    gerar o grafo de relacionamento (nós + arestas) — Seção 18 da
    arquitetura, consumido tanto pela aba "Grafo de Entidades" do front
    quanto pelo Relatório Final (Seção 28: bloco GRAFO DE RELACIONAMENTOS).
    """

    @staticmethod
    def _classify(field: str) -> str:
        f = field.lower()
        for entity_type, markers in FIELD_TYPE_RULES:
            if any(m in f for m in markers):
                return entity_type
        return None

    @staticmethod
    def resolve_entities_and_graph(investigation_id: str, indicators: List[Dict], findings: List[Dict]):
        nodes = []
        edges = []

        main_entity_id = f"ent_root_{investigation_id[:8]}"
        main_label = indicators[0]["display_value"] if indicators else "Investigação"
        main_type = indicators[0]["type"] if indicators else "ROOT"

        nodes.append({
            "id": main_entity_id,
            "name": main_label,
            "entity_type": main_type,
            "metadata_json": {"root": True}
        })

        # Evita duplicar o mesmo valor de entidade várias vezes no grafo
        # (ex.: 5 findings diferentes citando o mesmo e-mail).
        seen_values = {}

        # Termos que indicam resultado negativo/ausência — não viram nó no grafo
        NEGATIVE_MARKERS = [
            "nenhum", "não encontrad", "não verificad", "não confirmável",
            "não confirmavel", "sem dados públicos", "não disponível",
            "não reconhecido", "indisponível"
        ]

        for idx, finding in enumerate(findings):
            field = finding.get("field", "")
            val = (finding.get("value") or "").strip()
            entity_type = EntityResolutionEngine._classify(field)
            if not entity_type or not val:
                continue
            if any(marker in val.lower() for marker in NEGATIVE_MARKERS):
                continue

            dedup_key = (entity_type, val[:120])
            if dedup_key in seen_values:
                continue
            seen_values[dedup_key] = True

            entity_id = f"ent_{idx}_{investigation_id[:8]}"
            nodes.append({
                "id": entity_id,
                "name": val[:120],
                "entity_type": entity_type,
                "metadata_json": {"field": field, "source": finding.get("source_name")}
            })

            edges.append({
                "id": f"rel_{idx}_{investigation_id[:8]}",
                "source_entity_id": main_entity_id,
                "target_entity_id": entity_id,
                "relation_type": f"ASSOCIATED_WITH_{entity_type.upper()}",
                "confidence": finding.get("confidence", 1.0)
            })

        return nodes, edges
