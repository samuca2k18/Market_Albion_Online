# 🔧 Configuração de Variáveis de Ambiente

Este documento explica **exatamente** onde configurar cada variável de ambiente.

## 🎯 Resumo Rápido

**Duas variáveis diferentes para dois propósitos:**

1. **`APP_BASE_URL`** (Backend/Render) → URL do **FRONTEND**
   - Usado para gerar o link no email de verificação
   - Deve apontar para o Vercel (frontend)
   - Exemplo: `https://marketalbion.vercel.app`

2. **`VITE_API_BASE_URL`** (Frontend/Vercel) → URL do **BACKEND**
   - Usado pelo frontend para fazer chamadas à API
   - Deve apontar para o Render (backend)
   - Exemplo: `https://market-albion-online.onrender.com`

**Por que são diferentes?**
- O email precisa de um link que abre no **frontend** (página `/verify-email`)
- O frontend precisa saber onde está o **backend** (para chamadas API)

---

## 📍 Onde Configurar

### 🟢 BACKEND (Render) - Variáveis SMTP e Email

**Localização:** Render Dashboard → Seu Serviço → Environment

**Variáveis necessárias:**

```env
# === SMTP Gmail (para envio de emails) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx  # Senha de App do Gmail
SMTP_FROM=marketalbionbr@gmail.com

# === URL do FRONTEND (importante!) ===
# Este é o link que vai no email de verificação
# Deve apontar para a URL do Vercel (frontend)
APP_BASE_URL=https://seu-frontend.vercel.app

# === Outras variáveis do backend ===
DATABASE_URL=postgresql+psycopg2://...
SECRET_KEY=sua_chave_secreta_aqui
```

**⚠️ IMPORTANTE sobre `APP_BASE_URL`:**
- Deve ser a URL do **FRONTEND** (Vercel), não do backend!
- O link no email vai para a página `/verify-email` do frontend
- Exemplo: `https://marketalbion.vercel.app` ou `https://seu-dominio.com`

---

### 🔵 FRONTEND (Vercel) - URL da API

**Localização:** Vercel Dashboard → Seu Projeto → Settings → Environment Variables

**Variáveis necessárias:**

```env
# === URL do BACKEND (Render) ===
# O frontend usa isso para fazer chamadas à API
VITE_API_BASE_URL=https://market-albion-online.onrender.com
```

**⚠️ IMPORTANTE:**
- Deve ser a URL do **BACKEND** (Render)
- Sem barra no final (`/`)
- Exemplo: `https://market-albion-online.onrender.com`

---

## 📋 Resumo Visual

```
┌─────────────────────────────────────────────────────────┐
│                    FLUXO DE EMAIL                       │
└─────────────────────────────────────────────────────────┘

1. Usuário se cadastra no FRONTEND (Vercel)
   ↓
2. Frontend chama API do BACKEND (Render)
   ↓
3. Backend envia email usando SMTP (Gmail)
   ↓
4. Email contém link: APP_BASE_URL/verify-email?token=xxx
   ↓
5. Link aponta para FRONTEND (Vercel)
   ↓
6. Frontend chama API do BACKEND para verificar token
```

---

## 🔍 Verificação Rápida

### ✅ Backend (Render) está correto se:
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` estão configurados
- [ ] `APP_BASE_URL` aponta para a URL do **FRONTEND** (Vercel)
- [ ] `DATABASE_URL` e `SECRET_KEY` estão configurados

### ✅ Frontend (Vercel) está correto se:
- [ ] `VITE_API_BASE_URL` aponta para a URL do **BACKEND** (Render)
- [ ] Não tem barra no final da URL

---

## 🧪 Como Testar

### 1. Testar Backend:
```bash
# No Render, verifique os logs após criar um usuário
# Deve aparecer: "E-mail enviado com sucesso" ou erro de SMTP
```

### 2. Testar Frontend:
```bash
# Abra o console do navegador
# Ao fazer login/signup, verifique se as chamadas vão para:
# https://market-albion-online.onrender.com/...
```

### 3. Testar Email:
1. Crie um novo usuário
2. Verifique a caixa de entrada do email cadastrado
3. O link no email deve abrir: `https://seu-frontend.vercel.app/verify-email?token=...`

---

## ⚠️ Erros Comuns

### Erro: "SMTP não configurado"
**Causa:** Variáveis SMTP não estão no Render  
**Solução:** Adicione todas as variáveis `SMTP_*` no Render

### Erro: Link no email não funciona
**Causa:** `APP_BASE_URL` está apontando para o backend ao invés do frontend  
**Solução:** Configure `APP_BASE_URL` com a URL do Vercel (frontend)

### Erro: Frontend não consegue chamar API
**Causa:** `VITE_API_BASE_URL` está incorreto ou não configurado  
**Solução:** Configure `VITE_API_BASE_URL` com a URL do Render (backend)

### Erro: CORS
**Causa:** Backend não permite origem do frontend  
**Solução:** Verifique `allow_origins` no `main.py` do backend

---

## 📝 Exemplo Completo

### Render (Backend):
```
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = marketalbionbr@gmail.com
SMTP_PASS = abcd efgh ijkl mnop
SMTP_FROM = marketalbionbr@gmail.com
APP_BASE_URL = https://marketalbion.vercel.app
DATABASE_URL = postgresql+psycopg2://...
SECRET_KEY = sua_chave_aqui
```

### Vercel (Frontend):
```
VITE_API_BASE_URL = https://market-albion-online.onrender.com
```

---

## 💡 Dica

**Para desenvolvimento local:**

**Backend (.env):**
```env
APP_BASE_URL=http://localhost:5173  # URL do frontend local
```

**Frontend (.env.local):**
```env
VITE_API_BASE_URL=http://localhost:8000  # URL do backend local
```

