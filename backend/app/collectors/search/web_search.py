import re
import httpx
from urllib.parse import unquote
from typing import List
from app.collectors.base import BaseCollector, CollectorResult
from app.models.models import IndicatorType, DisplayPolicy, VerificationStatus
from app.core.config import settings

class SearchEngineCollector(BaseCollector):
    name = "Busca Web Pública em Tempo Real (Fontes Brasileiras .BR)"
    supported_types = [
        IndicatorType.CPF, IndicatorType.CNPJ, IndicatorType.PHONE,
        IndicatorType.EMAIL, IndicatorType.DOMAIN, IndicatorType.URL,
        IndicatorType.USERNAME, IndicatorType.NAME, IndicatorType.PIX
    ]

    EXCLUDED_DOMAINS = [
        "peoplefinders.com", "411.com", "robokiller.com", "numlookup.com",
        "spokeo.com", "truepeoplesearch.com", "anywho.com", "whitepages.com",
        "duckduckgo.com"
    ]

    def normalize(self, value: str, indicator_type: IndicatorType) -> str:
        return value.strip()

    def build_br_queries(self, query: str, indicator_type: IndicatorType) -> List[str]:
        clean_num = re.sub(r'\D', '', query)
        queries = []

        if indicator_type == IndicatorType.CPF:
            formatted = f"{clean_num[:3]}.{clean_num[3:6]}.{clean_num[6:9]}-{clean_num[9:]}" if len(clean_num) == 11 else query
            queries.append(f'CPF "{formatted}" site:.br')
            queries.append(f'"{formatted}" site:jusbrasil.com.br OR site:gov.br')
            queries.append(f'"{clean_num}" site:com.br')
        elif indicator_type == IndicatorType.CNPJ:
            queries.append(f'CNPJ "{query}" site:.br')
            queries.append(f'"{clean_num}" site:cnpj.biz OR site:brasilapi.com.br')
        elif indicator_type == IndicatorType.PHONE:
            queries.append(f'telefone "{query}" site:.br')
            queries.append(f'"{clean_num}" site:reclameaqui.com.br OR site:jusbrasil.com.br')
        elif indicator_type == IndicatorType.EMAIL:
            queries.append(f'email "{query}" site:.br')
        else:
            queries.append(f'"{query}" site:.br')
            queries.append(query)

        return queries

    async def fetch(self, indicator_type: IndicatorType, value: str) -> List[CollectorResult]:
        raw_val = self.normalize(value, indicator_type)
        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        queries = self.build_br_queries(raw_val, indicator_type)
        # Adicionar fallbacks mais amplos caso os termos com aspas não retornem resultados
        clean_num = re.sub(r'\D', '', raw_val)
        if clean_num:
            queries.append(clean_num)
        queries.append(raw_val)

        # 1. Tentar Google Custom Search API se as credenciais estiverem configuradas
        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX and "sua_chave" not in settings.GOOGLE_SEARCH_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    for term in queries[:2]:
                        resp = await client.get(
                            "https://www.googleapis.com/customsearch/v1",
                            params={
                                "key": settings.GOOGLE_SEARCH_API_KEY,
                                "cx": settings.GOOGLE_SEARCH_CX,
                                "q": term
                            }
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            items = data.get("items", [])
                            if items:
                                count = 0
                                for item in items:
                                    link = item.get("link", "")
                                    title = item.get("title", "")
                                    snippet = item.get("snippet", "")
                                    if any(dom in link for dom in self.EXCLUDED_DOMAINS):
                                        continue
                                    count += 1
                                    results.append(CollectorResult(
                                        field=f"Publicação / Citação na Web Brasileira [{count}]",
                                        value=f"Título: {title}\nLink: {link}\nResumo: {snippet}",
                                        source_name="Google Custom Search API",
                                        source_reference=link,
                                        confidence=0.98,
                                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                        display_policy=DisplayPolicy.FULL
                                    ))
                                    if count >= 5:
                                        break
                                if count > 0:
                                    results.insert(0, CollectorResult(
                                        field="Mapeamento de Presença em Fontes Públicas (Google Custom Search)",
                                        value=f"Encontradas {count} citações e publicações públicas indexadas no Google para '{raw_val}'",
                                        source_name="Google Custom Search API",
                                        source_reference="Google Cloud API",
                                        confidence=0.98,
                                        verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                        display_policy=DisplayPolicy.FULL
                                    ))
                                    return results
            except Exception as e:
                print(f"Erro ao consultar Google Custom Search API: {e}")

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for term in queries:
                try:
                    resp = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": term},
                        headers=headers
                    )

                    if resp.status_code == 200:
                        html = resp.text
                        
                        title_matches = re.findall(
                            r'<a[^>]+class=[\'\"][^\'\"]*result__a[^\'\"]*[\'\"][^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*>(.*?)</a>',
                            html, re.DOTALL
                        )

                        snippet_matches = re.findall(
                            r'<a[^>]+class=[\'\"][^\'\"]*result__snippet[^\'\"]*[\'\"][^>]*>(.*?)</a>',
                            html, re.DOTALL
                        )

                        count = 0
                        for idx, (raw_url, raw_title) in enumerate(title_matches):
                            clean_url = raw_url
                            if "uddg=" in raw_url:
                                try:
                                    clean_url = unquote(raw_url.split("uddg=")[1].split("&")[0])
                                except Exception:
                                    pass
                            elif raw_url.startswith("//"):
                                clean_url = "https:" + raw_url

                            # Filter out non-relevant foreign spam lookup sites
                            if any(dom in clean_url for dom in self.EXCLUDED_DOMAINS):
                                continue

                            clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
                            snippet_raw = snippet_matches[idx] if idx < len(snippet_matches) else ""
                            clean_snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()

                            if clean_url:
                                count += 1
                                results.append(CollectorResult(
                                    field=f"Publicação / Citação na Web Brasileira [{count}]",
                                    value=f"Título: {clean_title}\nLink: {clean_url}\nResumo: {clean_snippet}",
                                    source_name=self.name,
                                    source_reference=clean_url,
                                    confidence=0.95,
                                    verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                    display_policy=DisplayPolicy.FULL
                                ))
                                if count >= 5:
                                    break

                        if count > 0:
                            results.insert(0, CollectorResult(
                                field="Mapeamento de Presença em Fontes Públicas Brasileiras (.BR / Jusbrasil / Diários)",
                                value=f"Encontradas {count} citações e publicações públicas indexadas no Brasil para '{raw_val}'",
                                source_name=self.name,
                                source_reference="DuckDuckGo Brasil",
                                confidence=0.95,
                                verification_status=VerificationStatus.SOURCE_CONFIRMED,
                                display_policy=DisplayPolicy.FULL
                            ))
                            return results

                except Exception as e:
                    print(f"Error executing BR query '{term}': {e}")

        # Informative notice if no public web publications indexed
        results.append(CollectorResult(
            field="Busca em Diários Oficiais e Fontes Abertas (.BR)",
            value=f"Nenhum diário oficial, citação judicial ou publicação empresarial indexada publicamente no Brasil para '{raw_val}'",
            source_name=self.name,
            confidence=0.85,
            verification_status=VerificationStatus.SOURCE_CONFIRMED,
            display_policy=DisplayPolicy.FULL
        ))
        return results
