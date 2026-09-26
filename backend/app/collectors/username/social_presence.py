import asyncio
import httpx
from typing import List, Optional
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus

# Verificação de presença de username em múltiplas plataformas públicas —
# mesma técnica usada por ferramentas como userrecon/Sherlock (requisição
# HTTP simples à URL pública de perfil + checagem de status/marcador de
# texto). Diferente de copiar um script de terceiros não mantido, esta
# lista é curada e checada por método mais confiável quando possível
# (status HTTP), com fallback para marcador textual quando o site sempre
# responde 200. Sites que mudam layout com frequência podem gerar
# falso positivo/negativo — por isso o campo "confidence" é mais baixo
# nesses casos e o resultado nunca é apresentado como definitivo.

class SiteCheck:
    def __init__(self, name: str, url_template: str, method: str = "status",
                 not_found_markers: Optional[List[str]] = None,
                 not_found_status: Optional[List[int]] = None):
        self.name = name
        self.url_template = url_template
        self.method = method  # "status" (mais confiável) ou "text" (heurístico)
        self.not_found_markers = not_found_markers or []
        self.not_found_status = not_found_status or [404]


SITES = [
    SiteCheck("Twitter / X", "https://x.com/{u}", method="status", not_found_status=[404]),
    SiteCheck("Instagram", "https://www.instagram.com/{u}/", method="text",
              not_found_markers=["Sorry, this page isn't available"]),
    SiteCheck("TikTok", "https://www.tiktok.com/@{u}", method="text",
              not_found_markers=["Couldn't find this account"]),
    SiteCheck("Reddit", "https://www.reddit.com/user/{u}/about.json", method="status", not_found_status=[404]),
    SiteCheck("Telegram", "https://t.me/{u}", method="text",
              not_found_markers=["If you have Telegram, you can contact", "tgme_page_title"]),
    SiteCheck("YouTube", "https://www.youtube.com/@{u}", method="status", not_found_status=[404]),
    SiteCheck("Twitch", "https://www.twitch.tv/{u}", method="text",
              not_found_markers=["Sorry. Unless you've got a time machine"]),
    SiteCheck("Pinterest", "https://www.pinterest.com/{u}/", method="status", not_found_status=[404]),
    SiteCheck("Medium", "https://medium.com/@{u}", method="status", not_found_status=[404]),
    SiteCheck("Steam", "https://steamcommunity.com/id/{u}", method="text",
              not_found_markers=["The specified profile could not be found"]),
    SiteCheck("GitLab", "https://gitlab.com/{u}", method="status", not_found_status=[404]),
    SiteCheck("Keybase", "https://keybase.io/{u}", method="status", not_found_status=[404]),
    SiteCheck("Dev.to", "https://dev.to/{u}", method="status", not_found_status=[404]),
    SiteCheck("Replit", "https://replit.com/@{u}", method="status", not_found_status=[404]),
    SiteCheck("HackerNews", "https://news.ycombinator.com/user?id={u}", method="text",
              not_found_markers=["No such user."]),
]


class SocialPresenceCollector(BaseCollector):
    name = "Verificação de Presença em Redes Sociais (multi-plataforma)"
    supported_types = [IndicatorType.USERNAME]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip().lstrip("@")

    async def _check_site(self, client: httpx.AsyncClient, site: SiteCheck, username: str) -> Optional[CollectorResult]:
        url = site.url_template.format(u=username)
        try:
            resp = await client.get(url, timeout=5.0, follow_redirects=True)
        except Exception:
            return None  # rede indisponível para este site — não reporta nada (nunca inventa)

        if site.method == "status":
            exists = resp.status_code not in site.not_found_status and resp.status_code < 400
            confidence = 0.85
        else:
            body = resp.text[:20000] if resp.status_code < 500 else ""
            exists = resp.status_code < 400 and not any(marker.lower() in body.lower() for marker in site.not_found_markers)
            confidence = 0.6  # heurístico textual, mais sujeito a falso positivo/negativo

        return CollectorResult(
            field=f"Presença Pública em {site.name}",
            value=f"Perfil @{username} provavelmente existe" if exists else f"Nenhum perfil @{username} encontrado",
            source_name=site.name,
            source_reference=url if exists else None,
            confidence=confidence if exists else confidence * 0.7,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        )

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        username = self.normalize(value, indicator_type)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        async with httpx.AsyncClient(headers=headers) as client:
            tasks = [self._check_site(client, site, username) for site in SITES]
            outcomes = await asyncio.gather(*tasks, return_exceptions=False)

        results = [r for r in outcomes if r is not None]
        found = [r for r in results if "provavelmente existe" in r.value]

        results.insert(0, CollectorResult(
            field="Resumo de Varredura Multi-Plataforma",
            value=(
                f"Username @{username} verificado em {len(SITES)} plataformas públicas — "
                f"{len(found)} indício(s) de perfil existente. Cada item abaixo é uma checagem "
                f"HTTP independente (não uma confirmação de titularidade) e pode conter falsos "
                f"positivos/negativos quando o layout do site muda."
            ),
            source_name=self.name,
            confidence=0.7,
            verification_status=VerificationStatus.UNVERIFIED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
