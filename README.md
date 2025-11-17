# 🛡️ Albion Market API

API REST profissional desenvolvida em **Python (FastAPI)** para autenticação de usuários, gerenciamento de itens monitorados e consulta de preços do mercado do jogo **Albion Online**. O banco de dados é hospedado no **Supabase (PostgreSQL)**.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-blue.svg)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Executando o Projeto](#-executando-o-projeto)
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
- ✅ Login com JWT (JSON Web Tokens)
- ✅ Autenticação Bearer Token para rotas protegidas
- ✅ Hash seguro de senhas usando PBKDF2-SHA256
- ✅ Validação de e-mail e nome de usuário único

### 📦 Gerenciamento de Itens
- ✅ Cadastro de itens para monitoramento
- ✅ Listagem de itens do usuário autenticado
- ✅ Validação de duplicatas
- ✅ Ordenação por data de criação

### 💰 Integração com Albion Online
- ✅ Consulta de preços em tempo real via API oficial
- ✅ Busca da cidade mais barata entre múltiplas cidades
- ✅ Consulta em lote para todos os itens do usuário
- ✅ Tratamento robusto de erros e timeouts
- ✅ Suporte para todas as cidades principais do jogo

### 🛠️ Recursos Profissionais
- ✅ Documentação automática (Swagger/OpenAPI)
- ✅ Logging estruturado
- ✅ Tratamento global de exceções
- ✅ Validação de dados com Pydantic
- ✅ CORS configurado
- ✅ Health check endpoint
- ✅ Pool de conexões otimizado
- ✅ Variáveis de ambiente para configuração

---

## 🧩 Tecnologias

| Categoria | Tecnologias |
|-----------|-------------|
| **Backend Framework** | FastAPI 0.121.1 |
| **Linguagem** | Python 3.12+ |
| **Banco de Dados** | PostgreSQL (Supabase) |
| **ORM** | SQLAlchemy 2.0.44 |
| **Autenticação** | JWT (python-jose) + Passlib |
| **Validação** | Pydantic 2.12.4 |
| **HTTP Client** | Requests 2.32.5 |
| **Servidor ASGI** | Uvicorn 0.38.0 |
| **Variáveis de Ambiente** | python-dotenv 1.2.1 |

---

## 🗂️ Estrutura do Projeto

```
Market_Albion_Online/
│
├── main.py              # Ponto de entrada da API e rotas
├── auth.py              # Lógica de autenticação e JWT
├── database.py          # Configuração do banco de dados
├── models.py            # Modelos ORM (User, UserItem)
├── schemas.py           # Schemas Pydantic para validação
├── requirements.txt     # Dependências do projeto
├── .env.example         # Exemplo de variáveis de ambiente
├── .gitignore           # Arquivos ignorados pelo Git
└── README.md            # Este arquivo
```

---

## 📦 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.12 ou superior**
- **PostgreSQL** (ou acesso a um banco Supabase)
- **pip** (gerenciador de pacotes Python)
- **Git** (opcional, para clonar o repositório)

---

## 🚀 Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/Market_Albion_Online.git
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

Copie o arquivo `.env.example` para `.env`:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2. Configurar variáveis de ambiente

Edite o arquivo `.env` com suas configurações:

```env
# Configurações do Banco de Dados
DATABASE_URL=postgresql+psycopg2://usuario:senha@host:porta/database

# Chave Secreta para JWT (IMPORTANTE: gere uma chave segura!)
SECRET_KEY=sua_chave_secreta_aqui

# Configurações de Token JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Configurações da API do Albion Online
ALBION_API_BASE_URL=https://www.albion-online-data.com/api/v2/stats/prices
ALBION_API_TIMEOUT=10

# Configurações do Servidor
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Ambiente
ENVIRONMENT=development
```

### 3. Gerar chave secreta segura

Para gerar uma chave secreta segura para JWT, execute:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o resultado e cole no campo `SECRET_KEY` do arquivo `.env`.

### 4. Configurar banco de dados

#### Opção A: Supabase (Recomendado)

1. Crie uma conta no [Supabase](https://supabase.com/)
2. Crie um novo projeto
3. Vá em **Settings** > **Database**
4. Copie a **Connection String** (URI)
5. Cole no campo `DATABASE_URL` do arquivo `.env`

#### Opção B: PostgreSQL Local

Se preferir usar PostgreSQL local:

```env
DATABASE_URL=postgresql+psycopg2://postgres:senha@localhost:5432/albion_market
```

---

## ▶️ Executando o Projeto

### Modo Desenvolvimento

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Modo Produção

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
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

---

## 🔌 Endpoints

### Autenticação

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| POST | `/signup` | Cadastrar novo usuário | ❌ |
| POST | `/login` | Fazer login | ❌ |

### Usuário

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| GET | `/me` | Obter informações do usuário atual | ✅ |

### Itens

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| POST | `/items` | Adicionar item à lista | ✅ |
| GET | `/items` | Listar itens do usuário | ✅ |

### Albion Online

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| GET | `/albion/price` | Consultar preço de item | ✅ |
| GET | `/albion/my-items-prices` | Consultar preços dos meus itens | ✅ |

### Sistema

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| GET | `/health` | Health check | ❌ |

---

## 💡 Exemplos de Uso

### 1. Cadastrar Usuário

```bash
curl -X POST "http://localhost:8000/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "senha123"
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

### 2. Fazer Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=senha123"
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Adicionar Item (Autenticado)

```bash
curl -X POST "http://localhost:8000/items" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "item_name": "T4_BAG"
  }'
```

### 4. Consultar Preço de Item

```bash
curl -X GET "http://localhost:8000/albion/price?item_name=T4_BAG" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

**Resposta:**
```json
{
  "item": "T4_BAG",
  "cities_checked": ["Bridgewatch", "Martlock", "Thetford", "Lymhurst", "FortSterling", "Caerleon"],
  "cheapest_city": "Bridgewatch",
  "cheapest_price": 11000,
  "all_data": [...]
}
```

### 5. Consultar Preços dos Meus Itens

```bash
curl -X GET "http://localhost:8000/albion/my-items-prices" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

---

## 🔒 Segurança

### Implementações de Segurança

- ✅ **Hash de senhas**: PBKDF2-SHA256 (sem limite de 72 bytes)
- ✅ **JWT Tokens**: Tokens com expiração configurável
- ✅ **Validação de dados**: Pydantic para validação de entrada
- ✅ **SQL Injection**: Protegido pelo SQLAlchemy ORM
- ✅ **CORS**: Configurado para controle de origem
- ✅ **Variáveis de ambiente**: Credenciais não expostas no código
- ✅ **Logging**: Registro de tentativas de login e erros

### Boas Práticas

1. **Nunca commite o arquivo `.env`** no Git
2. **Use uma chave secreta forte** para JWT em produção
3. **Configure CORS adequadamente** para produção
4. **Use HTTPS** em produção
5. **Mantenha as dependências atualizadas**

---

## 🌐 API Externa Utilizada

**Albion Online Data API**
- URL: https://www.albion-online-data.com/api/v2/stats/prices/
- Documentação: https://www.albion-online-data.com/
- Tipo: API pública REST
- Rate Limit: Consulte a documentação oficial

---

## 🚀 Melhorias Futuras

- [ ] Implementar cache de preços (Redis)
- [ ] Adicionar rate limiting
- [ ] Criar sistema de notificações (preço abaixo de X)
- [ ] Adicionar testes automatizados (pytest)
- [ ] Implementar CI/CD
- [ ] Adicionar métricas e monitoramento
- [ ] Criar frontend web
- [ ] Adicionar suporte a múltiplos idiomas
- [ ] Implementar paginação nas listagens
- [ ] Adicionar filtros e busca avançada

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um Fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abrir um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

## 👨‍💻 Autor

Desenvolvido com ❤️ para a comunidade de Albion Online

---

## 📞 Suporte

Se você encontrar algum problema ou tiver dúvidas:

1. Abra uma [Issue](https://github.com/SEU_USUARIO/Market_Albion_Online/issues)
2. Consulte a [Documentação da API](http://localhost:8000/docs)
3. Verifique os [Logs](logs/) para mais detalhes

---

**⭐ Se este projeto foi útil para você, considere dar uma estrela!**
