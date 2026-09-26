# Arquitetura — Plataforma de OSINT e Antifraude

## 1. Visão geral

A proposta é construir uma plataforma de **OSINT + antifraude + correlação de evidências** capaz de receber identificadores como:

- CPF
- CNPJ
- Telefone
- E-mail
- Chave Pix
- Nome
- URL
- Domínio
- Username
- IP
- Hash

O sistema consulta múltiplas fontes públicas e APIs autorizadas, normaliza os resultados, correlaciona entidades e gera um relatório consolidado.

> **Princípio:** o sistema deve apresentar fatos, evidências, fontes e datas. Não deve simplesmente declarar que uma pessoa é "golpista". Relatos de usuários também devem ser diferenciados de fatos confirmados.

---

# 2. Arquitetura geral

```text
                         ┌─────────────────────┐
                         │      FRONTEND       │
                         │ React / Next.js     │
                         │ Dashboard / Report  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      API GATEWAY    │
                         │       FastAPI       │
                         │ JWT / RBAC / Rate   │
                         │ Limit / Audit       │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ Investigation Engine│
                         │ Normalização        │
                         │ Orquestração        │
                         │ Correlação           │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │   PHONE     │       │    EMAIL    │       │    PIX      │
       │ Collectors  │       │ Collectors  │       │ Collectors  │
       └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │    CNPJ     │       │   DOMAIN    │       │  USERNAME   │
       │ Collectors  │       │ Collectors  │       │ Collectors  │
       └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Correlation Engine  │
                         │ Entity Resolution   │
                         │ Graph Relationships │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Evidence Engine     │
                         │ Fonte / Data /      │
                         │ Confiança / Prova   │
                         └──────────┬──────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
              PostgreSQL          Redis          Object Storage
              dados/evidências    cache          PDFs/evidências
```

---

# 3. Tipos de consulta

### MVP

```text
CPF
CNPJ
Telefone
E-mail
Chave Pix
Nome
URL
Domínio
Username
IP
Hash
```

### Expansões futuras

```text
Empresa
Documento público
Número de processo
Nome empresarial
Endereço empresarial publicado
Placa — somente com fonte e autorização adequadas
```

---

# 4. Fontes e APIs

## 4.1 Receita Federal — CNPJ

### Fonte

- Dados Abertos da Receita Federal:
  https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos

- Dados da base CNPJ:
  https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/convenios-e-transferencias/compartilhamento-de-bases-de-dados-2013-decreto-no-8-789-2016/leiaute-das-bases/dados-da-base-cnpj

### Collector

```text
RFBCollector
```

### Possíveis informações

```text
CNPJ
Razão social
Nome fantasia
Situação cadastral
Data de abertura
Natureza jurídica
CNAE
Endereço empresarial publicado
Telefone empresarial
E-mail empresarial
Capital social
QSA
```

### Observação

Dados de CPF de sócios/responsáveis devem ser tratados conforme a disponibilidade, finalidade, autorização e política da fonte. O sistema não deve fazer enriquecimento por bases vazadas ou não autorizadas.

---

# 5. Pix

## 5.1 Banco Central — DICT

O Banco Central possui o **DICT — Diretório de Identificadores de Contas Transacionais do Pix**.

Fonte oficial:

https://www.bcb.gov.br/content/estabilidadefinanceira/pix/API-DICT.html

### Possíveis identificadores

```text
CPF
CNPJ
Telefone
E-mail
EVP
```

### Arquitetura

```text
PixCollector
      │
      ▼
AuthorizedPixProvider
      │
      ▼
DICT / Instituição participante
```

### Exemplo de resultado normalizado

```json
{
  "key_type": "CPF",
  "key": "71645678912",
  "holder_name": "JOAO DA SILVA",
  "holder_document": "71645678912",
  "source": "AUTHORIZED_PIX_PROVIDER"
}
```

### Importante

O DICT não deve ser tratado como uma API pública para consultas arbitrárias de terceiros. O projeto deve utilizar integração de participante/provedor autorizado.

---

# 6. Portal da Transparência

### API oficial

https://portaldatransparencia.gov.br/api-de-dados

### Collector

```text
TransparenciaCollector
```

### Possíveis fontes

```text
CEIS
CNEP
CEAF
Servidores
Viagens
Contratos
Licitações
Convênios
Despesas
Benefícios
```

Algumas consultas permitem pesquisa por CPF/CNPJ conforme a base.

### Exemplo

```json
{
  "source": "PORTAL_TRANSPARENCIA",
  "findings": [
    {
      "type": "PUBLIC_REGISTRY",
      "registry": "CEIS",
      "document": "...",
      "status": "...",
      "date": "..."
    }
  ]
}
```

A utilização da API deve respeitar cadastro, autenticação, limites e termos definidos pelo Portal.

---

# 7. Telefone

## 7.1 Twilio Lookup

### API

https://www.twilio.com/docs/lookup/v2-api

### Collector

```text
PhoneCollector
```

### Possíveis informações

```text
Validade
Formatação
País
Tipo da linha
Operadora
SIM Swap — dependendo do produto
Line Status — dependendo do produto
Risk Information — dependendo do produto
```

### Arquitetura

```text
PhoneCollector
    ├── TwilioLookup
    ├── PublicWebSearch
    ├── OwnComplaintDB
    └── AuthorizedFraudProvider
```

### Exemplo

```text
TELEFONE

+55 88 99999-9999

Validação: válido
Tipo: mobile
País: BR
Operadora: XXXXX

Fontes públicas relacionadas:
- anúncio público
- site empresarial
- perfil público
- denúncia cadastrada

Última consulta:
21/09/2026
```

O sistema não deve tentar descobrir clandestinamente o titular de um telefone por bases privadas, vazadas ou mecanismos de acesso não autorizado.

---

# 8. E-mail

## 8.1 Have I Been Pwned

### API

https://haveibeenpwned.com/API/v3

### Collector

```text
HIBPCollector
```

### Objetivo

Verificar se o endereço apareceu em incidentes de exposição conhecidos.

### Exemplo

```text
EMAIL

teste@email.com

Exposição encontrada: SIM

Incidentes:

├── Breach A
│   ├── Data: 2024
│   └── Dados expostos: ...
│
└── Breach B
    ├── Data: 2025
    └── Dados expostos: ...
```

### Regra de segurança

O sistema deve informar exposição, mas não armazenar ou tentar recuperar senhas expostas.

---

# 9. Domínios

## 9.1 RDAP

### Fonte

https://www.icann.org/rdap/

RDAP é o padrão moderno para consultas de dados de registro de domínios, sujeito à disponibilidade e às políticas aplicáveis.

### Collector

```text
DomainCollector
```

### Resultado

```text
DOMÍNIO

empresa.com.br

Registrar: ...
Status: ...
Created: ...
Updated: ...
Expires: ...

Nameservers:
- ns1...
- ns2...
```

Não presumir que o RDAP fornecerá dados pessoais do registrante. A disponibilidade depende do registro, registrar e políticas aplicáveis.

---

# 10. URLs

## 10.1 Google Safe Browsing / Web Risk

### Documentação

https://developers.google.com/safe-browsing/v4/reference/rest

Para uso comercial, verificar o produto/licenciamento apropriado, como Google Web Risk.

### Collector

```text
URLSafetyCollector
```

### Objetivo

Verificar indicadores de:

```text
Phishing
Malware
Recursos perigosos
```

---

# 11. urlscan.io

### API

https://docs.urlscan.io/pages/api-intro

### Collector

```text
URLScanCollector
```

### Possíveis informações

```text
URL
Domínio
IP
ASN
Hash
HTTP Status
Título
Tecnologias
Histórico de scans
Relacionamentos
```

### Exemplo

```text
URL

https://exemplo.com/login

HTTP Status: 200
IP: xxx.xxx.xxx.xxx
ASN: ASxxxxx
Country: BR
Title: Login

Technologies:
    Cloudflare
    React
    Nginx

Histórico de scans:
    4
```

---

# 12. VirusTotal

### API

https://docs.virustotal.com/reference/overview

### Collector

```text
VirusTotalCollector
```

### Possíveis indicadores

```text
URL
Domínio
IP
Hash
Arquivo
Relacionamentos
Detecções
```

### Atenção

A API pública possui restrições de uso. Se o projeto se tornar comercial, verificar o plano/licença adequado antes de integrar ao produto.

---

# 13. GitHub

### API oficial

https://docs.github.com/en/rest

### Collector

```text
GitHubCollector
```

### Possíveis dados públicos

```text
Username
Nome público
Bio
Avatar
Organizações públicas
Repositórios
Contribuições públicas
Sites públicos
Localização declarada no perfil
```

A localização informada em um perfil não deve ser tratada como localização física atual.

---

# 14. Busca na internet

Criar:

```text
SearchEngineCollector
```

Possíveis provedores:

```text
Google Programmable Search
Bing Search API
SerpAPI
Brave Search API
```

### Consultas

```text
"telefone"
"email"
"nome"
"domínio"
"username"
"CNPJ"
```

### Resultado

```text
BUSCA WEB

1. Empresa XYZ
   https://empresa.com.br

2. Perfil profissional
   https://...

3. Documento público
   https://...

4. Anúncio público
   https://...
```

A finalidade é encontrar páginas públicas, não copiar indiscriminadamente informações privadas.

---

# 15. IP e infraestrutura

Criar:

```text
IPCollector
```

Possíveis provedores:

```text
IPinfo
MaxMind GeoIP
RDAP
DNS
Reverse DNS
ASN databases
```

### Possíveis informações

```text
IP
ASN
ISP
Organização
País
Região aproximada
Cidade aproximada
Reverse DNS
```

### Importante

Geolocalização de IP é aproximada e não deve ser apresentada como endereço residencial ou localização física exata.

---

# 16. Geocodificação

É possível transformar um endereço **publicamente divulgado** em coordenadas.

Exemplo:

```text
Endereço empresarial publicado
        │
        ▼
Geocoding
        │
        ▼
Latitude / Longitude
```

Possível serviço:

```text
OpenStreetMap / Nominatim
```

O sistema deve identificar:

```text
Tipo: localização do endereço publicado
```

e não:

```text
Localização atual da pessoa
```

Não implementar:

```text
CPF → GPS atual
Telefone → GPS atual
```

sem uma fonte e autorização legítimas para isso.

---

# 17. Banco próprio de denúncias

Uma das partes mais importantes do projeto.

Tabela:

```text
complaints
```

Exemplo:

```json
{
  "indicator_type": "PHONE",
  "indicator": "+5588999999999",
  "report_type": "SUSPECTED_SCAM",
  "description": "...",
  "reported_at": "2026-09-21",
  "evidence": [
    {
      "type": "SCREENSHOT",
      "hash": "..."
    }
  ]
}
```

### Classificação

Separar:

```text
RELATO DE USUÁRIO
```

de:

```text
FATO CONFIRMADO
```

Exemplo:

```text
⚠ 3 denúncias associadas ao número

Isso significa que usuários relataram ocorrências.
Não significa, isoladamente, que o titular do número
tenha cometido fraude.
```

---

# 18. Evidence Graph

O sistema deve possuir um grafo de relacionamento.

```text
                   ┌──────────────┐
                   │ João da Silva│
                   └───────┬──────┘
                           │
             ┌─────────────┼──────────────┐
             │             │              │
             ▼             ▼              ▼
          CPF X        Telefone X      Empresa X
                          │              │
                          │              │
                          ▼              ▼
                       Email X        Domínio X
                                          │
                                          ▼
                                       IP X
                                          │
                                          ▼
                                       ASN X
```

### Tecnologias possíveis

#### Opção inicial

```text
PostgreSQL
```

com tabelas de relacionamentos.

#### Opção avançada

```text
Neo4j
```

ou

```text
PostgreSQL + Apache AGE
```

---

# 19. Modelo de dados

## Tabelas principais

```text
users
investigations
indicators
findings
sources
source_requests
entities
relationships
complaints
evidence
reports
audit_logs
provider_credentials
retention_policies
```

---

## 19.1 indicators

```text
id
type
normalized_value
display_value
created_at
```

---

## 19.2 findings

```text
id
indicator_id
entity_id

field
value

source_id
source_reference

confidence
verification_status

retrieved_at
expires_at
```

---

## 19.3 sources

```text
id
name
type

PUBLIC
GOVERNMENT
AUTHORIZED_PROVIDER
USER_SUBMITTED

endpoint
terms_url
privacy_url
active
```

---

# 20. Proveniência dos dados

Nunca armazenar apenas:

```json
{
  "cpf": "12345678900"
}
```

O ideal é:

```json
{
  "field": "cpf",
  "value": "12345678900",

  "source": "AUTHORIZED_PROVIDER",

  "source_reference": "consulta-982731",

  "retrieved_at": "2026-09-21T22:30:00-03:00",

  "verification": "SOURCE_CONFIRMED",

  "display_policy": "FULL"
}
```

Assim cada informação possui:

```text
VALOR
FONTE
DATA
REFERÊNCIA
VERIFICAÇÃO
POLÍTICA DE EXIBIÇÃO
```

---

# 21. Política de exibição sem mascaramento

Como requisito do projeto, criar:

```text
display_policy
```

Valores:

```text
FULL
MASKED
HIDDEN
```

### Exemplo

```json
{
  "field": "cpf",
  "value": "71645678912",
  "display_policy": "FULL",
  "authorization": "AUTHORIZED_PROVIDER"
}
```

Resultado:

```text
CPF: 716.456.789-12
```

Se a fonte permitir somente visualização parcial:

```json
{
  "field": "cpf",
  "value": "...",
  "display_policy": "MASKED"
}
```

Resultado:

```text
CPF: ***.456.789-**
```

### Regra

O sistema não deve mascarar indiscriminadamente.

Porém, `FULL` somente deve ser utilizado quando a fonte, contrato, autorização e finalidade permitirem a exibição integral.

---

# 22. Orquestração

Quando o usuário pesquisar:

```text
+55 88 99999-9999
```

o sistema poderá executar:

```text
Phone Lookup
        │
        ├── Twilio
        ├── Web Search
        ├── Complaint DB
        └── Authorized Fraud Provider
                │
                ▼
          CORRELATION
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
     Email     Nome     Empresa
       │        │         │
       ▼        ▼         ▼
     HIBP      Web      CNPJ
                         │
                         ▼
                  Transparência
```

---

# 23. Celery + Redis

Arquitetura recomendada:

```text
FastAPI
   │
   ▼
Redis
   │
   ▼
Celery Workers
```

Cada investigação:

```text
investigation_id = 9a72...
```

gera jobs:

```text
phone_lookup
web_search
twilio_lookup
complaint_search
email_lookup
cnpj_lookup
domain_lookup
url_lookup
pix_lookup
```

### Status no frontend

```text
PROCESSANDO

████████████████░░░░ 78%

✓ Normalização
✓ Telefone
✓ Web
✓ Reclamações
✓ Empresas
✓ Domínios
○ Relatório
```

---

# 24. API do sistema

## Criar investigação

```http
POST /api/v1/investigations
```

Exemplo:

```json
{
  "indicators": [
    {
      "type": "PHONE",
      "value": "+5588999999999"
    },
    {
      "type": "PIX",
      "value": "email@example.com"
    }
  ]
}
```

---

## Consultar investigação

```http
GET /api/v1/investigations/{id}
```

## Consultar evidências

```http
GET /api/v1/investigations/{id}/findings
```

## Consultar grafo

```http
GET /api/v1/investigations/{id}/graph
```

## Gerar relatório

```http
GET /api/v1/investigations/{id}/report
```

## Registrar denúncia

```http
POST /api/v1/complaints
```

## Consultar indicador

```http
GET /api/v1/indicators/{type}/{value}
```

## Listar fontes

```http
GET /api/v1/sources
```

## Health check

```http
GET /api/v1/health
```

---

# 25. Estrutura do projeto

```text
fraud-recon/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── investigations.py
│   │   │       ├── indicators.py
│   │   │       ├── complaints.py
│   │   │       └── reports.py
│   │
│   │   ├── collectors/
│   │   │   ├── base.py
│   │   │   ├── phone/
│   │   │   │   ├── twilio.py
│   │   │   │   └── web.py
│   │   │   ├── email/
│   │   │   │   └── hibp.py
│   │   │   ├── pix/
│   │   │   │   └── authorized_provider.py
│   │   │   ├── cnpj/
│   │   │   │   └── receita.py
│   │   │   ├── transparency/
│   │   │   │   └── portal.py
│   │   │   ├── domain/
│   │   │   │   ├── rdap.py
│   │   │   │   └── dns.py
│   │   │   ├── url/
│   │   │   │   ├── urlscan.py
│   │   │   │   ├── virustotal.py
│   │   │   │   └── safer_browsing.py
│   │   │   └── username/
│   │   │       └── github.py
│   │
│   │   ├── correlation/
│   │   │   ├── engine.py
│   │   │   ├── entity_resolution.py
│   │   │   └── graph.py
│   │
│   │   ├── evidence/
│   │   │   ├── engine.py
│   │   │   ├── confidence.py
│   │   │   └── provenance.py
│   │
│   │   ├── reports/
│   │   │   ├── html.py
│   │   │   ├── pdf.py
│   │   │   └── json.py
│   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── workers/
│   │   └── security/
│   │
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   └── nextjs/
│
├── infrastructure/
│   ├── docker/
│   ├── postgres/
│   ├── redis/
│   └── nginx/
│
└── docker-compose.yml
```

---

# 26. Stack recomendada

| Componente      | Tecnologia        |
| --------------- | ----------------- |
| Backend         | Python + FastAPI  |
| ORM             | SQLAlchemy        |
| Validação       | Pydantic          |
| Banco           | PostgreSQL        |
| Cache           | Redis             |
| Jobs            | Celery            |
| Frontend        | Next.js           |
| UI              | Tailwind CSS      |
| Autenticação    | JWT/OAuth         |
| Relatórios      | HTML + PDF + JSON |
| Grafo           | PostgreSQL/Neo4j  |
| HTTP            | httpx             |
| DNS             | dnspython         |
| Telefone        | phonenumbers      |
| Testes          | Pytest            |
| E2E             | Cypress           |
| Observabilidade | OpenTelemetry     |
| Logs            | structlog         |
| Deploy          | Docker            |
| Proxy           | Nginx/Traefik     |

---

# 27. Catálogo inicial de fontes

| Área        | Fonte/API                     | Utilidade                         |
| ----------- | ----------------------------- | --------------------------------- |
| CNPJ        | Receita Federal               | Empresas e dados cadastrais       |
| Governo     | Portal Transparência          | Registros públicos governamentais |
| Pix         | DICT/BCB                      | Consulta autorizada de chaves Pix |
| Telefone    | Twilio Lookup                 | Validação, tipo e operadora       |
| E-mail      | Have I Been Pwned             | Exposição em breaches             |
| Domínio     | ICANN RDAP                    | Registro de domínio               |
| URL         | Google Safe Browsing/Web Risk | URLs perigosas                    |
| URL         | urlscan.io                    | Análise/histórico de páginas      |
| URL/IP/hash | VirusTotal                    | Threat intelligence               |
| Username    | GitHub API                    | Dados públicos do GitHub          |
| Web         | APIs de busca                 | Páginas públicas                  |
| Geocoding   | OSM/Nominatim                 | Endereço público → coordenadas    |
| IP          | IPinfo/MaxMind                | ASN/geolocalização aproximada     |
| Denúncias   | Banco próprio                 | Relatos de usuários               |

---

# 28. Exemplo de relatório final

```text
╔══════════════════════════════════════════════════╗
║              RESULTADO DA CONSULTA              ║
╚══════════════════════════════════════════════════╝

IDENTIFICADOR

Tipo: TELEFONE
Valor: +55 88 99999-9999


TELEFONE

Status: Válido
Tipo: Mobile
País: Brasil
Operadora: XXXXX


IDENTIDADE RELACIONADA

Nome: João da Silva
Fonte: Fonte autorizada
Verificação: CONFIRMADA PELA FONTE


EMPRESAS RELACIONADAS

CNPJ: 12.345.678/0001-90
Razão social: Empresa XYZ LTDA
Situação: ATIVA
Fonte: Receita Federal


E-MAILS PUBLICAMENTE ENCONTRADOS

joao@example.com
Fonte: página pública


DOMÍNIOS RELACIONADOS

empresa.com.br

Criado: ...
Registrar: ...


EXPOSIÇÃO DE E-MAIL

joao@example.com

Breaches encontrados: 2

[detalhes]


DENÚNCIAS

3 relatos associados ao telefone

⚠ Relatos de usuários não constituem,
isoladamente, comprovação de fraude.


URLS RELACIONADAS

https://empresa.com.br

Safe Browsing: ...
URLScan: ...
VirusTotal: ...


GRAFO DE RELACIONAMENTOS

João
 ├── CPF
 ├── Telefone
 ├── E-mail
 ├── Empresa
 │    └── CNPJ
 └── Domínio
      └── IP
          └── ASN


FONTES

✓ Receita Federal
✓ Banco Central / provedor Pix autorizado
✓ Twilio
✓ Have I Been Pwned
✓ RDAP
✓ URLScan
✓ GitHub
✓ Fontes públicas


DATA DA CONSULTA

21/09/2026
```

---

# 29. Segurança e privacidade

O sistema deve implementar desde o início:

```text
HTTPS
JWT/OAuth
RBAC
Rate limiting
Audit logs
Criptografia em repouso
Criptografia em trânsito
Segregação de credenciais
Secrets management
Controle de retenção
Logs de acesso
Controle de permissões
Exclusão de dados
Backup seguro
```

### Nunca implementar

```text
Brute force
Credential stuffing
Acesso a contas de terceiros
Bypass de autenticação
Bases vazadas
Compra de dumps ilícitos
Scraping de sistemas restritos
Rastreamento GPS clandestino
Engenharia social para obtenção de dados
```

---

# 30. LGPD by design

O projeto deve considerar:

```text
Finalidade
Necessidade
Adequação
Segurança
Qualidade dos dados
Controle de acesso
Transparência
Retenção
Correção
Exclusão quando aplicável
Auditoria
```

Cada consulta deve possuir:

```text
Quem consultou
Quando consultou
Qual indicador
Qual finalidade
Quais fontes foram utilizadas
Quais dados foram retornados
```

---

# 31. Roadmap de desenvolvimento

## Fase 1 — Core

```text
FastAPI
PostgreSQL
SQLAlchemy
Pydantic
Docker
Redis
```

Implementar:

```text
Users
Investigations
Indicators
Findings
Sources
Audit logs
```

---

## Fase 2 — Collectors

Implementar inicialmente:

```text
CNPJ
Telefone
E-mail
Domínio
URL
IP
Username
```

---

## Fase 3 — Correlação

Implementar:

```text
Entity Resolution
Relationship Engine
Evidence Graph
Duplicate Detection
Confidence
Provenance
```

---

## Fase 4 — Pix

Integrar somente por:

```text
Participante
Provedor autorizado
API contratada
```

---

## Fase 5 — Dashboard

Criar:

```text
Nova investigação
Indicadores
Evidências
Relacionamentos
Linha do tempo
Fontes
Denúncias
Relatório
```

---

## Fase 6 — Relatórios

Formatos:

```text
JSON
HTML
PDF
CSV
```

---

## Fase 7 — Banco colaborativo

Permitir:

```text
Registrar denúncia
Anexar evidência
Associar telefone
Associar e-mail
Associar URL
Associar Pix
Atualizar denúncia
Contestar informação
```

---

# 32. Princípio central do produto

A plataforma não deve funcionar como:

```text
CPF
 ↓
"É golpista"
```

Deve funcionar como:

```text
INDICADOR
    ↓
FONTES
    ↓
DADOS
    ↓
EVIDÊNCIAS
    ↓
CORRELAÇÕES
    ↓
CONTEXTUALIZAÇÃO
    ↓
RELATÓRIO
```

Cada informação deve responder:

```text
O que foi encontrado?
De onde veio?
Quando foi consultado?
A fonte é pública ou autorizada?
Qual o nível de confirmação?
Pode ser exibido integralmente?
```

Esse modelo permite construir uma plataforma de investigação antifraude muito mais robusta, auditável e escalável.
