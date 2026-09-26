import json
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Investigation, Indicator, Finding, Entity, Relationship, Report
from app.schemas.schemas import ReportResponse

router = APIRouter()

# Tipo de entidade (definido em correlation/entity_resolution.py) -> título
# de seção no relatório, seguindo a Seção 28 da arquitetura.
ENTITY_SECTION_TITLES = {
    "Person": "IDENTIDADE RELACIONADA",
    "Company": "EMPRESAS RELACIONADAS",
    "Email": "E-MAILS PUBLICAMENTE ENCONTRADOS",
    "Domain": "DOMÍNIOS RELACIONADOS",
    "URL": "URLS RELACIONADAS",
    "IP": "ENDEREÇOS IP RELACIONADOS",
    "PixKey": "CHAVES PIX RELACIONADAS",
    "SocialProfile": "PERFIS EM REDES SOCIAIS",
    "PublicRecord": "REGISTROS PÚBLICOS RELACIONADOS",
}
# Ordem de exibição igual à do exemplo da Seção 28
SECTION_ORDER = ["Person", "Company", "Email", "Domain", "URL", "IP", "PixKey", "SocialProfile", "PublicRecord"]


def _build_graph_tree(entities, relationships, root_entity_id: str) -> str:
    """Renderiza o grafo de entidades como árvore ASCII, no formato do
    exemplo da Seção 28 (bloco GRAFO DE RELACIONAMENTOS)."""
    by_id = {e.id: e for e in entities}
    children = defaultdict(list)
    for r in relationships:
        children[r.source_entity_id].append(r.target_entity_id)

    lines = []
    root = by_id.get(root_entity_id)
    if not root:
        return "Grafo indisponível (sem entidades resolvidas para esta investigação)."

    lines.append(root.name)
    kids = children.get(root_entity_id, [])
    for i, child_id in enumerate(kids):
        child = by_id.get(child_id)
        if not child:
            continue
        is_last = (i == len(kids) - 1)
        branch = "└──" if is_last else "├──"
        lines.append(f" {branch} [{child.entity_type}] {child.name}")
    return "\n".join(lines)


@router.get("/{investigation_id}", response_model=ReportResponse)
def get_or_generate_report(
    investigation_id: str,
    format: str = Query("JSON", pattern="^(JSON|HTML|TXT)$"),
    db: Session = Depends(get_db)
):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigação não encontrada")

    indicators = db.query(Indicator).filter(Indicator.investigation_id == investigation_id).all()
    findings = db.query(Finding).filter(Finding.investigation_id == investigation_id).all()
    entities = db.query(Entity).filter(Entity.investigation_id == investigation_id).all()
    relationships = db.query(Relationship).filter(Relationship.investigation_id == investigation_id).all()

    root_entity = next((e for e in entities if (e.metadata_json or {}).get("root")), None)
    entities_by_type = defaultdict(list)
    for e in entities:
        if e is root_entity:
            continue
        entities_by_type[e.entity_type].append(e)

    denuncias = [f for f in findings if "denúncia" in f.field.lower() or "relato" in f.field.lower()]
    breach_findings = [f for f in findings if "exposição" in f.field.lower() or "breach" in f.field.lower() or "incidente de exposição" in f.field.lower()]
    entity_field_markers = ["e-mail", "email", "razão social", "empresa", "qsa", "cnpj", "domínio",
                             "url", "página", "site", "link", "telefone", " ip ", "ip:", "chave pix",
                             "dict", "github", "presença pública", "perfil", "titular", "identidade",
                             "nome completo", "sanção", "ceis", "cnep", "diário", "citação"]
    outros = [
        f for f in findings
        if f not in denuncias and f not in breach_findings
        and not any(m in f.field.lower() for m in entity_field_markers)
    ]

    # ---------- TXT (Seção 28 da arquitetura) ----------
    lines = []
    lines.append("╔══════════════════════════════════════════════════╗")
    lines.append("║              RESULTADO DA CONSULTA              ║")
    lines.append("╚══════════════════════════════════════════════════╝\n")

    lines.append("IDENTIFICADOR")
    for ind in indicators:
        lines.append(f"Tipo: {ind.type.value}")
        lines.append(f"Valor: {ind.display_value}\n")

    for entity_type in SECTION_ORDER:
        group = entities_by_type.get(entity_type)
        if not group:
            continue
        lines.append(ENTITY_SECTION_TITLES[entity_type])
        for e in group:
            src = (e.metadata_json or {}).get("source", "N/D")
            lines.append(f"{e.name}")
            lines.append(f"Fonte: {src}\n")

    if breach_findings:
        lines.append("EXPOSIÇÃO DE E-MAIL")
        for f in breach_findings:
            lines.append(f"{f.field}: {f.value}")
            lines.append(f"Fonte: {f.source_name}\n")

    lines.append("EVIDÊNCIAS & DADOS DE REGISTRO")
    for f in outros:
        lines.append(f"• {f.field}: {f.value}")
        lines.append(f"  Fonte: {f.source_name} | Verificação: {f.verification_status.value} | Exibição: {f.display_policy.value}")

    lines.append("\nDENÚNCIAS & HISTÓRICO COLABORATIVO")
    if denuncias:
        for f in denuncias:
            lines.append(f"⚠ {f.value}")
    else:
        lines.append("Nenhuma denúncia cadastrada para este identificador no banco próprio")
    lines.append("\n⚠ Relatos de usuários não constituem, isoladamente, comprovação de fraude.")

    if root_entity:
        lines.append("\nGRAFO DE RELACIONAMENTOS\n")
        lines.append(_build_graph_tree(entities, relationships, root_entity.id))

    lines.append("\n" + "─"*50)
    lines.append("FONTES DE DADOS UTILIZADAS:")
    used_sources = sorted(list(set(f.source_name for f in findings)))
    for src in used_sources:
        lines.append(f"✓ {src}")

    lines.append(f"\nDATA DA CONSULTA: {datetime.utcnow().strftime('%d/%m/%Y')}")

    report_content = "\n".join(lines)

    if format == "JSON":
        report_content = json.dumps({
            "investigation_id": inv.id,
            "title": inv.title,
            "created_at": inv.created_at.isoformat(),
            "indicators": [{"type": i.type.value, "value": i.display_value} for i in indicators],
            **{
                f"entidades_{t.lower()}": [
                    {"nome": e.name, "fonte": (e.metadata_json or {}).get("source")}
                    for e in entities_by_type.get(t, [])
                ]
                for t in SECTION_ORDER if entities_by_type.get(t)
            },
            "exposicao_email": [
                {"field": f.field, "value": f.value, "source": f.source_name} for f in breach_findings
            ],
            "grafo": {
                "nodes": [{"id": e.id, "name": e.name, "entity_type": e.entity_type} for e in entities],
                "edges": [{"source": r.source_entity_id, "target": r.target_entity_id, "type": r.relation_type} for r in relationships]
            },
            "findings": [
                {
                    "field": f.field,
                    "value": f.value,
                    "source": f.source_name,
                    "confidence": f.confidence,
                    "verification": f.verification_status.value,
                    "display_policy": f.display_policy.value
                } for f in findings
            ],
            "denuncias": [{"value": f.value} for f in denuncias],
            "fontes_consultadas": used_sources,
            "disclaimer": "Relatos de usuários não constituem, isoladamente, comprovação de fraude."
        }, indent=2, ensure_ascii=False)

    report = Report(
        investigation_id=investigation_id,
        format=format,
        content=report_content
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report
