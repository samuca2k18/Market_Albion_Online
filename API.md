# 📖 Documentação Completa da API

Documentação detalhada de todos os endpoints da **Albion Market API**.

---

## 🔐 Autenticação

A API utiliza **JWT (JSON Web Tokens)** para autenticação. A maioria dos endpoints requer autenticação via Bearer Token.

### Como obter um token:

1. Faça login em `/login` com suas credenciais
2. Copie o `access_token` da resposta
3. Use o token no header `Authorization: Bearer <token>`

### Exemplo:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📋 Endpoints

### 🔹 Autenticação

#### POST `/signup`

Cadastra um novo usuário no sistema.

**Autenticação:** Não requerida

**Body (JSON):**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "senha123"
}
```

**Validações:**
- `username`: 3-50 caracteres, apenas letras, números, `_` e `-`
- `email`: E-mail válido e único
- `password`: Mínimo 6 caracteres

**Resposta de Sucesso (201):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

**Erros Possíveis:**
- `400`: Nome de usuário ou e-mail já cadastrado
- `400`: Dados inválidos (validação falhou)
- `422`: Erro de validação do schema

---

#### POST `/login`

Autentica um usuário e retorna um token JWT.

**Autenticação:** Não requerida

**Body (Form Data):**
```
username: johndoe
password: senha123
```

**Resposta de Sucesso (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Erros Possíveis:**
- `401`: Usuário ou senha incorretos
- `422`: Erro de validação

**Nota:** O token expira após o tempo configurado em `ACCESS_TOKEN_EXPIRE_MINUTES` (padrão: 60 minutos).

---

### 🔹 Usuário

#### GET `/me`

Retorna as informações do usuário autenticado.

**Autenticação:** ✅ Requerida

**Headers:**
```http
Authorization: Bearer <token>
```

**Resposta de Sucesso (200):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

**Erros Possíveis:**
- `401`: Token inválido ou expirado

---

### 🔹 Itens

#### POST `/items`

Adiciona um novo item à lista de monitoramento do usuário.

**Autenticação:** ✅ Requerida

**Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "item_name": "T4_BAG"
}
```

**Validações:**
- `item_name`: 1-100 caracteres, não pode estar vazio
- O item será normalizado para UPPERCASE
- Não permite duplicatas (mesmo item para o mesmo usuário)

**Resposta de Sucesso (201):**
```json
{
  "id": 1,
  "item_name": "T4_BAG",
  "created_at": "2024-01-15T10:30:00"
}
```

**Erros Possíveis:**
- `400`: Item já está na lista de monitoramento
- `401`: Token inválido ou expirado
- `422`: Erro de validação

---

#### GET `/items`

Lista todos os itens na lista de monitoramento do usuário.

**Autenticação:** ✅ Requerida

**Headers:**
```http
Authorization: Bearer <token>
```

**Resposta de Sucesso (200):**
```json
[
  {
    "id": 1,
    "item_name": "T4_BAG",
    "created_at": "2024-01-15T10:30:00"
  },
  {
    "id": 2,
    "item_name": "T5_HEAD_PLATE_SET1",
    "created_at": "2024-01-14T15:20:00"
  }
]
```

**Nota:** Os itens são ordenados por data de criação (mais recentes primeiro).

**Erros Possíveis:**
- `401`: Token inválido ou expirado

---

### 🔹 Albion Online

#### GET `/albion/price`

Consulta o preço de um item específico nas cidades do Albion Online.

**Autenticação:** ✅ Requerida

**Headers:**
```http
Authorization: Bearer <token>
```

**Query Parameters:**
- `item_name` (obrigatório): Nome interno do item (ex: `T4_BAG`, `T5_HEAD_PLATE_SET1`)
- `cities` (opcional): Lista de cidades separadas por vírgula

**Cidades Disponíveis:**
- `Bridgewatch`
- `Martlock`
- `Thetford`
- `Lymhurst`
- `FortSterling`
- `Caerleon`

**Exemplo de Requisição:**
```http
GET /albion/price?item_name=T4_BAG&cities=Bridgewatch,Martlock,Thetford
```

**Resposta de Sucesso (200):**
```json
{
  "item": "T4_BAG",
  "cities_checked": ["Bridgewatch", "Martlock", "Thetford"],
  "cheapest_city": "Bridgewatch",
  "cheapest_price": 11000,
  "all_data": [
    {
      "item_id": "T4_BAG",
      "city": "Bridgewatch",
      "quality": 1,
      "sell_price_min": 11000,
      "sell_price_min_date": "2024-01-15T10:00:00",
      "sell_price_max": 12000,
      "buy_price_min": 10500,
      "buy_price_max": 11500
    },
    ...
  ]
}
```

**Resposta quando não há dados (200):**
```json
{
  "item": "T4_BAG",
  "cities_checked": ["Bridgewatch", "Martlock"],
  "message": "Nenhum dado retornado para esse item/cidades",
  "data": []
}
```

**Resposta quando não há preço (200):**
```json
{
  "item": "T4_BAG",
  "cities_checked": ["Bridgewatch"],
  "message": "Item encontrado, mas sem preço de venda disponível nas cidades informadas",
  "data": [...]
}
```

**Erros Possíveis:**
- `400`: Pelo menos uma cidade deve ser especificada
- `401`: Token inválido ou expirado
- `502`: Erro ao consultar a API do Albion Online
- `504`: Timeout ao consultar a API do Albion Online

---

#### GET `/albion/my-items-prices`

Consulta os preços de todos os itens na lista de monitoramento do usuário.

**Autenticação:** ✅ Requerida

**Headers:**
```http
Authorization: Bearer <token>
```

**Query Parameters:**
- `cities` (opcional): Lista de cidades separadas por vírgula

**Exemplo de Requisição:**
```http
GET /albion/my-items-prices?cities=Bridgewatch,Martlock,Thetford
```

**Resposta de Sucesso (200):**
```json
{
  "user_id": 1,
  "cities_checked": ["Bridgewatch", "Martlock", "Thetford"],
  "total_items": 2,
  "items": [
    {
      "item": "T4_BAG",
      "status": "success",
      "cheapest_city": "Bridgewatch",
      "cheapest_price": 11000
    },
    {
      "item": "T5_HEAD_PLATE_SET1",
      "status": "no_price",
      "message": "Sem preço de venda disponível nas cidades informadas"
    },
    {
      "item": "T6_WEAPON",
      "status": "error",
      "message": "Erro ao consultar API do Albion Online"
    }
  ]
}
```

**Status dos Itens:**
- `success`: Preço encontrado com sucesso
- `no_price`: Item encontrado, mas sem preço de venda
- `no_data`: Nenhum dado retornado
- `error`: Erro ao consultar a API

**Resposta quando não há itens (200):**
```json
{
  "user_id": 1,
  "cities_checked": ["Bridgewatch", "Martlock"],
  "items": [],
  "message": "Nenhum item na sua lista de monitoramento"
}
```

**Erros Possíveis:**
- `400`: Pelo menos uma cidade deve ser especificada
- `401`: Token inválido ou expirado

---

### 🔹 Sistema

#### GET `/health`

Endpoint de health check para monitoramento da API.

**Autenticação:** Não requerida

**Resposta de Sucesso (200):**
```json
{
  "status": "healthy",
  "service": "Albion Market API",
  "version": "1.0.0"
}
```

---

## 📊 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `201` | Criado com sucesso |
| `400` | Requisição inválida |
| `401` | Não autorizado (token inválido/expirado) |
| `404` | Recurso não encontrado |
| `422` | Erro de validação |
| `500` | Erro interno do servidor |
| `502` | Erro ao consultar API externa |
| `504` | Timeout na requisição |

---

## 🔍 Formato de Nomes de Itens

Os nomes de itens seguem o padrão do jogo Albion Online:

**Formato:** `T[NÍVEL]_[TIPO]_[NOME]`

**Exemplos:**
- `T4_BAG` - Mochila nível 4
- `T5_HEAD_PLATE_SET1` - Capacete de placa nível 5, conjunto 1
- `T6_WEAPON_AXE` - Machado nível 6
- `T7_OFF_SHIELD` - Escudo nível 7

**Nota:** A API normaliza automaticamente os nomes para UPPERCASE.

---

## ⚠️ Tratamento de Erros

Todos os erros retornam um JSON no seguinte formato:

```json
{
  "detail": "Mensagem de erro descritiva"
}
```

**Exemplos:**

```json
{
  "detail": "Token inválido ou expirado"
}
```

```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "Nome de usuário deve conter apenas letras, números, _ e -",
      "type": "value_error"
    }
  ]
}
```

---

## 🚀 Exemplos de Uso com cURL

### Cadastrar Usuário
```bash
curl -X POST "http://localhost:8000/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "senha123"
  }'
```

### Fazer Login
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=senha123"
```

### Adicionar Item
```bash
curl -X POST "http://localhost:8000/items" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_name": "T4_BAG"}'
```

### Consultar Preço
```bash
curl -X GET "http://localhost:8000/albion/price?item_name=T4_BAG" \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

## 📝 Notas Importantes

1. **Tokens JWT**: Os tokens expiram após o tempo configurado. Faça login novamente para obter um novo token.

2. **Rate Limiting**: A API do Albion Online pode ter limites de requisição. Use com moderação.

3. **Cidades**: Use os nomes exatos das cidades (case-sensitive). A API valida e normaliza automaticamente.

4. **Itens Duplicados**: Um mesmo item não pode ser adicionado duas vezes para o mesmo usuário.

5. **Timeout**: O timeout padrão para requisições à API do Albion é de 10 segundos. Pode ser configurado via variável de ambiente.

---

## 🔗 Links Úteis

- [Documentação Swagger](http://localhost:8000/docs)
- [Documentação ReDoc](http://localhost:8000/redoc)
- [API do Albion Online](https://www.albion-online-data.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Última atualização:** 2024-01-15

