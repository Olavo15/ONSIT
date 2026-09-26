# Plataforma de OSINT, Antifraude e Correlação de Evidências (`fraud-recon`)

Plataforma completa de inteligência OSINT e antifraude construída estritamente com base no documento de arquitetura [arquitetura_osint_antifraude.md].

---

## 🚀 Tecnologias

- **Backend**: Python 3.11/3.13, FastAPI, SQLAlchemy, Pydantic v2, httpx, phonenumbers, Pytest.
- **Frontend**: React 18, Vite, Lucide Icons, Glassmorphism OSINT Dark Mode visual styling.
- **Banco & Cache**: PostgreSQL / SQLite, Redis, Celery (Jobs assíncronos).
- **Infraestrutura**: Docker & Docker Compose.

---

## ⚡ Como Executar

### Opção 1: Via Docker Compose (Recomendado)

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs

---

### Opção 2: Execução Local para Desenvolvimento

#### 1. Iniciar o Backend FastAPI

```bash
./venv/bin/pytest backend/tests          # Executar testes unitários
./venv/bin/uvicorn app.main:app --reload  # Iniciar API na porta 8000
```

#### 2. Iniciar o Frontend React/Vite

```bash
cd frontend
npm run dev                               # Iniciar Dashboard Web na porta 3000
```

---

## 🔍 Identificadores Suportados (MVP)

- **CPF** & **CNPJ** (Receita Federal, Portal da Transparência - CEIS/CNEP)
- **Telefone** (Twilio Lookup & ITU-E164)
- **E-mail** (Have I Been Pwned API)
- **Chave Pix** (Diretório de Identificadores DICT - Provedor Autorizado)
- **Domínio & DNS** (ICANN RDAP & DNS Resolver)
- **URL** (urlscan.io & Threat Intel)
- **Username** (GitHub API)
- **IP & ASN** (IPinfo & GeoIP)
- **Denúncias Internas** (Banco Próprio Colaborativo)

---

## ⚖️ Conformidade LGPD & Princípios do Produto

- **Transparência & Auditabilidade**: Cada evidência exibe **FONTE**, **DATA**, **CONFIANÇA**, **VERIFICAÇÃO** e **POLÍTICA DE EXIBIÇÃO** (`FULL` ou `MASKED`).
- **Relatos vs Fatos Confirmados**: O sistema diferencia claramente denúncias de usuários de fatos confirmados por fontes governamentais e autorizadas.
