# 🛡️ Albion Market API

API REST profissional desenvolvida em **Python (FastAPI)** para autenticação de usuários, verificação de e-mail, gerenciamento de itens monitorados, alertas de preço inteligentes e consulta de preços/histórico do mercado do jogo **Albion Online**. O banco de dados é hospedado no **Supabase (PostgreSQL)**.

Albion Online é um MMORPG Sandbox mundo aberto onde você que faz a sua história, em vez de seguir um caminho pré-definido. Explore um mundo aberto gigante com 5 ecossistemas diferentes. Tudo que você faz afeta o mundo, porque em Albion a economia é feita pelos jogadores.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-blue.svg)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Estrutura do Projeto](#️-estrutura-do-projeto)
- [Diagramas Arquiteturais](#️-diagramas-arquiteturais)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#️-configuração)
- [Executando o Projeto](#️-executando-o-projeto)
- [Documentação da API](#-documentação-da-api)
- [Endpoints](#-endpoints)
- [Exemplos de Uso](#-exemplos-de-uso)
- [Segurança](#-segurança)
- [Melhorias Futuras](#-melhorias-futuras)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

---

## ✨ Funcionalidades

### 🔐 Autenticação e Autorização
- ✅ Cadastro de usuários com validação de dados
- ✅ **Verificação de e-mail obrigatória** (token com expiração de 24h)
- ✅ **Reenvio de e-mail de verificação**
- ✅ Login bloqueado para e-mails não verificados
- ✅ JWT (JSON Web Tokens) com expiração configurável
- ✅ Autenticação Bearer Token para rotas protegidas
- ✅ Hash seguro de senhas usando PBKDF2-SHA256
- ✅ Validação de e-mail e nome de usuário único

### 📦 Gerenciamento de Itens
- ✅ Cadastro de itens por UniqueName (`T4_BAG`), nome PT-BR ou nome EN-US
- ✅ Resolução automática de nome para UniqueName via índice local
- ✅ Nome de exibição (display_name) personalizado por item
- ✅ Listagem de itens do usuário autenticado
- ✅ Remoção de itens da lista
- ✅ Ordenação por data de criação

### 💰 Integração com Albion Online
- ✅ Consulta de preços em tempo real via API oficial
- ✅ **Suporte a múltiplas regiões** (Europe, America, Asia)
- ✅ **Cache TTL** de preços (5 min) e histórico (10 min) com `cachetools`
- ✅ **Histórico de preços** por item e cidade
- ✅ Busca da cidade mais barata entre múltiplas cidades
- ✅ Consulta em lote para todos os itens do usuário
- ✅ **Indicador de frescor** — campo `updated_at` nos preços
- ✅ Tratamento robusto de erros e timeouts
- ✅ Suporte para todas as cidades principais do jogo

### 💱 Monitor de Ouro (Gold Tracker)
- ✅ Preço atual do ouro em tempo real
- ✅ Variação percentual (últimas 24h)
- ✅ Histórico com até 200 pontos de dados

### ⚖️ Calculadora de Arbitragem
- ✅ Identificação de oportunidades de trade entre cidades
- ✅ Cálculo de lucro líquido com taxas reais (8% normal, 4% premium)
- ✅ Diferenciação por **qualidade de item** (Normal a Obra-prima)
- ✅ ROI (%) e ranking das top 100 oportunidades

### 🚩 Monitor de Evento Bandit
- ✅ Endpoint `/albion/bandit-event` com status do ciclo
- ✅ Fases: ativo, em breve, esperando
- ✅ Countdown em minutos até o próximo evento

### 🗡️ Killboard
- ✅ Proxy para API oficial de kills (`gameinfo.albiononline.com`)
- ✅ Dados simplificados: killer/victim, guild, aliança, IP, arma, fame

### 🔔 Alertas de Preço
- ✅ Criação de alertas com **preço alvo manual** ou **percentual abaixo da média**
- ✅ **Preço esperado via IA** (calculado pelo histórico: média ou mediana)
- ✅ Configuração de cooldown entre notificações (anti-spam)
- ✅ Notificação por e-mail quando o preço atingir a meta
- ✅ Ativação/desativação e remoção de alertas
- ✅ Trigger manual via cron job com `CRON_SECRET`

### 🔍 Busca de Itens
- ✅ **Índice local com todos os itens do Albion** em PT-BR e EN-US
- ✅ Busca exata e busca aproximada (score-based fuzzy search)
- ✅ Endpoint `/albion/search/pt-br` e `/albion/search/en-us`
- ✅ Rota legada `/albion/search` com fallback automático de idioma

### 🛠️ Recursos Profissionais
- ✅ Documentação automática (Swagger/OpenAPI)
- ✅ Logging estruturado
- ✅ Tratamento global de exceções
- ✅ Validação de dados com Pydantic v2
- ✅ CORS configurado
- ✅ Health check endpoint
- ✅ Pool de conexões otimizado
- ✅ Variáveis de ambiente para configuração
- ✅ **Envio de e-mail via Resend API** (produção) ou SMTP (desenvolvimento)

---

## 🧩 Tecnologias

| Categoria | Tecnologia |
|-----------|------------|
| **Backend Framework** | FastAPI 0.121.1 |
| **Linguagem** | Python 3.12+ |
| **Banco de Dados** | PostgreSQL (Supabase) |
| **ORM** | SQLAlchemy 2.0.44 |
| **Autenticação** | JWT (python-jose) + Passlib |
| **Validação** | Pydantic 2.12.4 + pydantic-settings 2.5.2 |
| **HTTP Client** | Requests 2.32.3 + HTTPX 0.27.2 |
| **Servidor ASGI** | Uvicorn 0.38.0 |
| **Cache** | cachetools 5.5.0 (TTLCache) |
| **E-mail** | Resend API / SMTP |
| **Variáveis de Ambiente** | python-dotenv 1.2.1 |

---

## 🗂️ Estrutura do Projeto

```
Market_Albion_Online/
│
├── app/                        # Pacote principal da aplicação
│   ├── __init__.py
│   ├── main.py                 # Inicialização do FastAPI e registro de routers
│   ├── database.py             # Configuração do banco de dados (SQLAlchemy)
│   ├── models.py               # Modelos ORM (User, UserItem, PriceAlert)
│   ├── schemas.py              # Schemas Pydantic para validação e serialização
│   ├── dependencies.py         # Dependências reutilizáveis (get_db, get_current_user)
│   │
│   ├── core/                   # Configurações e segurança centrais
│   │   ├── config.py           # Settings via pydantic-settings (.env)
│   │   └── security.py        # JWT, hash de senha, get_current_user
│   │
│   ├── routers/                # Endpoints organizados por domínio
│   │   ├── auth.py             # /signup, /login, /verify-email, /resend-verification
│   │   ├── items.py            # /items (CRUD de itens do usuário)
│   │   ├── albion.py           # /albion/search, /albion/price, /albion/history, etc.
│   │   ├── alerts.py           # /alerts (CRUD + trigger de alertas de preço)
│   │   └── health.py           # /health (health check)
│   │
│   ├── services/               # Serviços de negócio
│   │   ├── mailer.py           # Envio de e-mails (Resend API / SMTP)
│   │   └── email_verify.py     # Geração e expiração de tokens de verificação
│   │
│   └── utils/                  # Utilitários e clientes externos
│       ├── albion_client.py    # Cliente HTTP para Albion Data API (com cache TTL)
│       └── albion_index.py     # Índice local de itens PT-BR/EN-US com busca fuzzy
│
├── nomes_pt_br.json            # Nomes dos itens em PT-BR (~1.1 MB)
├── nomes_en_us.json            # Nomes dos itens em EN-US (~1.0 MB)
├── nomes_simplificados.json    # Índice simplificado (~1.8 MB)
├── requirements.txt            # Dependências do projeto
├── .env.example                # Exemplo de variáveis de ambiente
├── .gitignore                  # Arquivos ignorados pelo Git
├── API.md                      # Documentação detalhada dos endpoints
├── CHANGELOG.md                # Histórico de mudanças
├── SECURITY.md                 # Guia de segurança
├── EMAIL_SETUP.md              # Guia de configuração de e-mail
├── VARIAVEIS_AMBIENTE.md       # Guia de variáveis de ambiente
└── README.md                   # Este arquivo
```

---

## 🏗️ Diagramas Arquiteturais

### Arquitetura Geral do Sistema

```mermaid
graph TB
    Client[Cliente/Usuário] -->|HTTP/HTTPS| API[FastAPI Application]

    subgraph "Camada de Apresentação"
        API --> Router[Routers por domínio]
    end

    subgraph "Camada de Aplicação"
        Router --> Auth[auth.py - Autenticação JWT]
        Router --> Items[items.py - Itens do Usuário]
        Router --> Albion[albion.py - Preços & Busca]
        Router --> Alerts[alerts.py - Alertas de Preço]
    end

    subgraph "Camada de Negócio"
        Auth --> Security[core/security.py]
        Alerts --> Mailer[services/mailer.py]
        Albion --> AlbionClient[utils/albion_client.py]
        Albion --> AlbionIndex[utils/albion_index.py]
    end

    subgraph "Camada de Dados"
        Security --> ORM[SQLAlchemy ORM]
        ORM --> DB[(PostgreSQL / Supabase)]
    end

    subgraph "Serviços Externos"
        AlbionClient --> AlbionAPI[Albion Online Data API]
        Mailer --> Resend[Resend API]
        Mailer --> SMTP[SMTP]
    end

    style API fill:#009688
    style DB fill:#336791
    style AlbionAPI fill:#FF6B6B
    style Security fill:#FFA726
    style Resend fill:#4CAF50
```

### Fluxo de Autenticação com Verificação de E-mail

```mermaid
sequenceDiagram
    participant C as Cliente
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Email as Resend/SMTP

    Note over C,Email: Cadastro de Usuário
    C->>API: POST /signup (username, email, password)
    API->>DB: INSERT user (is_verified=False, token=xyz)
    DB-->>API: User criado
    API->>Email: send_verification_email(email, token) [background]
    API-->>C: 201 UserOut

    Note over C,Email: Verificação de E-mail
    C->>API: GET /verify-email?token=xyz
    API->>DB: UPDATE user SET is_verified=True
    API-->>C: 200 {"message": "E-mail verificado!"}

    Note over C,DB: Login
    C->>API: POST /login (username, password)
    API->>DB: SELECT user WHERE username
    API->>API: verify_password + check is_verified
    alt E-mail verificado e senha válida
        API-->>C: {access_token, token_type: "bearer"}
    else E-mail não verificado
        API-->>C: 403 Forbidden
    else Senha inválida
        API-->>C: 401 Unauthorized
    end
```

### Fluxo de Alertas de Preço

```mermaid
sequenceDiagram
    participant C as Cliente
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Albion as Albion API
    participant Email as Resend API

    C->>API: POST /alerts (item_id, target_price, city)
    API->>DB: INSERT PriceAlert
    API-->>C: PriceAlertOut

    Note over API,Email: Trigger periódico (Cron Job)
    API->>DB: SELECT alertas ativos
    loop Para cada alerta
        API->>Albion: GET preços atuais do item
        Albion-->>API: Preços por cidade
        alt Preço <= target_price e cooldown OK
            API->>Email: send_price_alert_email(user, item, price)
            API->>DB: UPDATE last_triggered_at
        end
    end
```

### Modelo de Dados (Diagrama ER)

```mermaid
erDiagram
    USERS ||--o{ USER_ITEMS : "possui"
    USERS ||--o{ PRICE_ALERTS : "configura"

    USERS {
        int id PK
        string username UK
        string email UK
        string hashed_password
        bool is_verified
        string verification_token
        datetime verification_token_expires_at
    }

    USER_ITEMS {
        int id PK
        int user_id FK
        string item_name
        string display_name
        datetime created_at
    }

    PRICE_ALERTS {
        int id PK
        int user_id FK
        string item_id
        string display_name
        string city
        int quality
        float target_price
        float expected_price
        float percent_below
        bool use_ai_expected
        int ai_days
        string ai_resolution
        string ai_stat
        int ai_min_points
        int cooldown_minutes
        bool is_active
        datetime last_triggered_at
    }
}
```

### Arquitetura de Camadas

```mermaid
graph LR
    subgraph "Camada de Apresentação"
        A[Routers<br/>app/routers/]
    end

    subgraph "Camada de Aplicação"
        B[Schemas Pydantic<br/>app/schemas.py]
        C[Segurança / Auth<br/>app/core/security.py]
        D[Configurações<br/>app/core/config.py]
    end

    subgraph "Camada de Domínio"
        E[Modelos ORM<br/>app/models.py]
        F[Dependências<br/>app/dependencies.py]
    end

    subgraph "Camada de Infraestrutura"
        G[Database Config<br/>app/database.py]
        H[(PostgreSQL / Supabase)]
    end

    subgraph "Serviços e Utilitários"
        I[Mailer<br/>app/services/mailer.py]
        J[Albion Client<br/>app/utils/albion_client.py]
        K[Albion Index<br/>app/utils/albion_index.py]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    E --> G
    G --> H
    A --> I
    A --> J
    A --> K

    style A fill:#009688
    style B fill:#4CAF50
    style C fill:#FFA726
    style D fill:#FF9800
    style E fill:#2196F3
    style G fill:#9C27B0
    style H fill:#336791
    style I fill:#E91E63
    style J fill:#FF6B6B
    style K fill:#795548
```

---

## 📦 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.12 ou superior**
- **PostgreSQL** (ou acesso a um banco Supabase)
- **pip** (gerenciador de pacotes Python)
- **Git** (para clonar o repositório)
- **Conta Resend** (para envio de e-mails em produção) — [resend.com](https://resend.com)

---

## 🚀 Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/samuca2k18/Market_Albion_Online.git
cd Market_Albion_Online
```

### 2. Criar ambiente virtual

```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### 3. Ativar o ambiente virtual

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração

### 1. Criar arquivo `.env`

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2. Configurar variáveis de ambiente

Edite o arquivo `.env` com suas configurações:

```env
# === Banco de Dados ===
DATABASE_URL=postgresql+psycopg2://usuario:senha@host:porta/database

# === JWT ===
SECRET_KEY=sua_chave_secreta_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=60

# === Albion Online API ===
ALBION_REGION=europe          # europe | america | asia
ALBION_API_TIMEOUT=10

# === E-mail — Resend API (produção / Render) ===
RESEND_API_KEY=re_xxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=Market Albion <no-reply@seudominio.com>
RESEND_REPLY_TO=seu@email.com   # opcional

# === E-mail — SMTP (desenvolvimento local apenas) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu@email.com
SMTP_PASS=sua_senha_de_app

# === URL base para links de e-mail ===
FRONTEND_URL=https://seudominio.com

# === Cron Job (trigger de alertas) ===
CRON_SECRET=segredo_do_cron_aqui

# === Servidor ===
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True
ENVIRONMENT=development
```

### 3. Gerar chave secreta segura para JWT

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Configurar banco de dados

#### Opção A: Supabase (Recomendado)

1. Crie uma conta no [Supabase](https://supabase.com/)
2. Crie um novo projeto
3. Vá em **Settings** > **Database**
4. Copie a **Connection String** (URI) e cole no campo `DATABASE_URL` do `.env`

#### Opção B: PostgreSQL Local

```env
DATABASE_URL=postgresql+psycopg2://postgres:senha@localhost:5432/albion_market
```

### 5. Configurar Resend para e-mails (Produção)

1. Crie uma conta em [resend.com](https://resend.com)
2. Verifique seu domínio em **Domains**
3. Gere uma API Key em **API Keys**
4. Configure `RESEND_API_KEY` e `RESEND_FROM_EMAIL` no `.env`

> 📖 Veja mais detalhes em [EMAIL_SETUP.md](EMAIL_SETUP.md) e [VARIAVEIS_AMBIENTE.md](VARIAVEIS_AMBIENTE.md)

---

## ▶️ Executando o Projeto

### Modo Desenvolvimento

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Modo Produção

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

A API estará disponível em:
- **API**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Documentação ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 📚 Documentação da API

A documentação interativa está disponível automaticamente:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

A documentação inclui:
- Descrição de todos os endpoints
- Schemas de requisição e resposta
- Exemplos de uso
- Teste interativo das rotas

> 📖 Veja a documentação completa dos endpoints em [API.md](API.md)

---

## 🔌 Endpoints

### Autenticação

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/signup` | Cadastrar novo usuário (envia e-mail de verificação) | ❌ |
| POST | `/login` | Fazer login (requer e-mail verificado) | ❌ |
| GET | `/verify-email?token=...` | Confirmar e-mail pelo token | ❌ |
| POST | `/resend-verification` | Reenviar e-mail de verificação | ❌ |
| GET | `/me` | Dados do usuário autenticado | ✅ |

### Itens do Usuário

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/items` | Adicionar item (UniqueName, PT-BR ou EN-US) | ✅ |
| GET | `/items` | Listar itens do usuário | ✅ |
| DELETE | `/items/{item_id}` | Remover item da lista | ✅ |

### Albion Online

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/albion/search/pt-br?q=...` | Buscar itens por nome em PT-BR | ✅ |
| GET | `/albion/search/en-us?q=...` | Buscar itens por nome em EN-US | ✅ |
| GET | `/albion/search?q=...` | Buscar itens (PT-BR com fallback EN) | ✅ |
| GET | `/albion/price/pt-br` | Consultar preços (idioma PT-BR) | ✅ |
| GET | `/albion/price/en-us` | Consultar preços (idioma EN-US) | ✅ |
| GET | `/albion/my-items-prices` | Preços dos meus itens (com `updated_at`) | ✅ |
| GET | `/albion/gold` | Preço do ouro e variação | ❌ |
| GET | `/albion/history/{item_id}` | Histórico de preços (1h/6h/24h) | ✅ |
| GET | `/albion/arbitrage` | Oportunidades de arbitragem entre cidades | ✅ |
| GET | `/albion/bandit-event` | Status do Bandit Event (fase e countdown) | ❌ |
| GET | `/albion/killboard` | Feed de kills em tempo real (proxy) | ❌ |

### Alertas de Preço

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/alerts` | Criar alerta de preço | ✅ |
| GET | `/alerts` | Listar meus alertas | ✅ |
| DELETE | `/alerts/{alert_id}` | Remover alerta | ✅ |
| POST | `/alerts/trigger` | Disparar verificação de alertas (cron) | 🔑 |

### Sistema

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/health` | Health check | ❌ |

> 🔑 = requer header `X-Cron-Secret` com o valor de `CRON_SECRET`

---

## 💡 Exemplos de Uso

### 1. Cadastrar Usuário

```bash
curl -X POST "http://localhost:8000/signup" \
  -H "Content-Type: application/json" \
  -d '{"username": "jogador123", "email": "jogador@example.com", "password": "senha123"}'
```

**Resposta:**
```json
{
  "id": 1,
  "username": "jogador123",
  "email": "jogador@example.com",
  "is_verified": false
}
```

### 2. Verificar E-mail

```bash
curl "http://localhost:8000/verify-email?token=TOKEN_RECEBIDO_NO_EMAIL"
```

**Resposta:**
```json
{
  "message": "E-mail verificado com sucesso!"
}
```

### 3. Fazer Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jogador123&password=senha123"
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 4. Buscar Item por Nome

```bash
# Busca em PT-BR
curl "http://localhost:8000/albion/search/pt-br?q=bolsa" \
  -H "Authorization: Bearer SEU_TOKEN"
```

**Resposta:**
```json
[
  {
    "unique_name": "T4_BAG",
    "name_pt": "Bolsa do Adepto",
    "name_en": "Adept's Bag",
    "matched": "Bolsa do Adepto"
  }
]
```

### 5. Adicionar Item à Lista

```bash
# Por UniqueName
curl -X POST "http://localhost:8000/items" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_name": "T4_BAG", "display_name": "Minha Bolsa"}'

# Ou por nome PT-BR
curl -X POST "http://localhost:8000/items?lang=pt_br" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Bolsa do Adepto"}'
```

### 6. Criar Alerta de Preço

```bash
# Alerta com preço alvo manual
curl -X POST "http://localhost:8000/alerts" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_id": "T4_BAG", "display_name": "Bolsa do Adepto", "city": "Bridgewatch", "quality": 1, "target_price": 10000, "cooldown_minutes": 60}'

# Alerta com preço esperado via histórico (IA)
curl -X POST "http://localhost:8000/alerts" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_id": "T4_BAG", "city": "Bridgewatch", "use_ai_expected": true, "percent_below": 10, "ai_days": 7, "ai_resolution": "6h", "ai_stat": "median"}'
```

---

## 🔒 Segurança

### Implementações de Segurança

- ✅ **Hash de senhas**: PBKDF2-SHA256 (via Passlib)
- ✅ **Verificação de e-mail**: token seguro com expiração de 24h
- ✅ **JWT Tokens**: tokens com expiração configurável
- ✅ **Validação de dados**: Pydantic v2 para validação rigorosa de entrada
- ✅ **SQL Injection**: protegido pelo SQLAlchemy ORM
- ✅ **CORS**: configurado para controle de origem
- ✅ **Variáveis de ambiente**: credenciais nunca expostas no código
- ✅ **Logging**: registro de tentativas de login e erros
- ✅ **CRON_SECRET**: proteção do endpoint de trigger de alertas

### Boas Práticas

1. **Nunca commite o arquivo `.env`** no Git
2. **Use uma chave secreta forte** para JWT em produção
3. **Configure CORS adequadamente** para produção
4. **Use HTTPS** em produção
5. **Use Resend API** no Render (SMTP é bloqueado)
6. **Mantenha as dependências atualizadas**

> 📖 Veja o guia completo em [SECURITY.md](SECURITY.md)

---

## 🌐 API Externa Utilizada

**Albion Online Data API**
- URL Europa: `https://europe.albion-online-data.com/api/v2/stats/prices`
- URL América: `https://america.albion-online-data.com/api/v2/stats/prices`
- URL Ásia: `https://asia.albion-online-data.com/api/v2/stats/prices`
- Documentação: https://www.albion-online-data.com/
- Tipo: API pública REST
- Rate Limit: consulte a documentação oficial

---

## 🚀 Melhorias Futuras

- [ ] Testes automatizados (pytest + httpx AsyncClient)
- [ ] CI/CD com GitHub Actions
- [x] Frontend web (React + Vite + TypeScript)
- [x] Dashboard de preços com gráficos históricos
- [x] Monitor de preço do ouro em tempo real
- [x] Calculadora de arbitragem com qualidade
- [x] Killboard com feed de kills em tempo real
- [x] Monitor de Bandit Event com countdown
- [x] Indicador de frescor de dados
- [ ] Paginação e filtros avançados nas listagens
- [ ] Suporte a mais idiomas (DE, FR, RU, etc.)
- [ ] Exportação de dados (CSV/Excel)
- [ ] Rate limiting por usuário
- [ ] Métricas e monitoramento (Prometheus / Grafana)
- [ ] Notificações via Telegram/Discord além de e-mail
- [ ] Integração NATS para Bandit Event em tempo real
- [ ] Heatmap de preços multi-cidade
- [ ] Comparação de preços entre regiões (Europe vs America vs Asia)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um Fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: add MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abrir um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

Desenvolvido com ❤️ por [@samuca2k18](https://github.com/samuca2k18) para a comunidade de Albion Online

---

## 📞 Suporte

Se você encontrar algum problema ou tiver dúvidas:

1. Abra uma [Issue](https://github.com/samuca2k18/Market_Albion_Online/issues)
2. Consulte a [Documentação da API](http://localhost:8000/docs)
3. Leia os guias: [EMAIL_SETUP.md](EMAIL_SETUP.md) | [VARIAVEIS_AMBIENTE.md](VARIAVEIS_AMBIENTE.md) | [TROUBLESHOOTING_502.md](TROUBLESHOOTING_502.md)

---

**⭐ Se este projeto foi útil para você, considere dar uma estrela!**