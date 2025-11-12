
# 🛡️ Albion Market Online — Backend

API em **Python (FastAPI)** para autenticação de usuários, cadastro de itens monitorados e consulta de preços do mercado do jogo **Albion Online**.  
Banco de dados hospedado no **Supabase (PostgreSQL)**.

---

## 🚀 Funcionalidades

✅ **Cadastro e Login de Usuários**  
- Sistema de autenticação com JWT  
- Hash seguro de senha (PBKDF2)  
- Integração com banco PostgreSQL (Supabase)

✅ **Gerenciamento de Itens**  
- Usuários autenticados podem cadastrar itens que desejam acompanhar  
- Cada item fica vinculado ao usuário que o criou

✅ **Integração com a API Pública do Albion Online**  
- Consulta preços em tempo real diretamente da API oficial  
- Retorna a cidade mais barata entre:
  `Bridgewatch`, `Martlock`, `Thetford`, `Lymhurst`, `Fort Sterling` e `Caerleon`

✅ **Rota que mostra todos os itens do usuário com o preço mais barato**  
- Ideal para comparar rapidamente onde comprar cada item

---

## 🧩 Tecnologias Utilizadas

| Categoria | Tecnologias |
|------------|-------------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Banco de Dados** | PostgreSQL (Supabase) |
| **ORM** | SQLAlchemy |
| **Autenticação** | JWT (Python-JOSE) + Passlib |
| **HTTP Client** | Requests |
| **Outros** | Pydantic v2, python-dotenv, python-multipart, email-validator |

---

## 🗂️ Estrutura do Projeto

```

Market_Albion_Online/
│
├── main.py              # Ponto de entrada da API
├── auth.py              # Lógica de autenticação e geração de tokens JWT
├── database.py          # Conexão com o PostgreSQL (Supabase)
├── models.py            # Modelos ORM do SQLAlchemy (User, UserItem)
├── schemas.py           # Schemas Pydantic para entrada e saída de dados
├── requirements.txt     # Dependências do projeto
├── .gitignore
└── README.md

````

---

## ⚙️ Como Rodar Localmente

### 1️⃣ Clonar o repositório
```bash
git clone https://github.com/SEU_USUARIO/albion-market-backend.git
cd albion-market-backend
````

### 2️⃣ Criar ambiente virtual

```bash
python -m venv venv
```

### 3️⃣ Ativar o ambiente

```bash
# Windows
venv\Scripts\activate
```

### 4️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

### 5️⃣ Configurar variável de ambiente (Supabase)

Crie um arquivo `.env` na raiz com sua URL do banco:

```env
DATABASE_URL=postgresql://postgres.NOME_DO_SEU_PROJETO:[SENHA]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
SECRET_KEY=sua_chave_jwt_secreta
```

### 6️⃣ Rodar servidor local

```bash
uvicorn main:app --reload
```

Acesse a documentação Swagger em:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧠 Exemplos de Rotas

### 🔐 Cadastro

`POST /signup`

```json
{
  "username": "samuel",
  "email": "samuel@example.com",
  "password": "123456"
}
```

### 🔑 Login

`POST /login`

* Tipo: `form-data`
* Campos: `username`, `password`

Retorna:

```json
{
  "access_token": "eyJh...",
  "token_type": "bearer"
}
```

### ➕ Cadastrar Item

`POST /items`

```json
{
  "item_name": "T4_BAG"
}
```

### 📜 Listar Itens

`GET /items`

### 💰 Consultar Preço de Item do Albion

`GET /albion/price?item_name=T4_BAG`

Retorno:

```json
{
  "item": "T4_BAG",
  "cheapest_city": "Bridgewatch",
  "cheapest_price": 11000
}
```

### 🧾 Preços dos Itens do Usuário

`GET /albion/my-items-prices`

---

## 🌐 API de Terceiros Usada

**Albion Online Data API**
📎 [https://www.albion-online-data.com/api/v2/stats/prices/](https://www.albion-online-data.com/api/v2/stats/prices/)

---

## ✨ Futuras Melhorias

* [ ] Implementar cache local de preços (para evitar excesso de requisições)
* [ ] Adicionar agendador para atualização automática dos preços
* [ ] Criar dashboard web/frontend para visualização dos itens
* [ ] Envio de notificações quando o item estiver abaixo de um valor definido

---


Quer que eu inclua também a seção de **Deploy (Render/Railway)** no README, mostrando como hospedar o backend na nuvem?
```
