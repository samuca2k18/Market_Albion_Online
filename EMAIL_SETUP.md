# 📧 Configuração de Envio de E-mails

Este projeto suporta **dois modos** de envio de e-mail:

## 🚀 Modo 1: Resend API (Recomendado para Produção)

**Melhor para:** Render, Vercel, Railway, ou qualquer plataforma cloud.

### Vantagens:
- ✅ Mais confiável (não depende de servidor SMTP próprio)
- ✅ Melhor deliverability (menos chance de ir para spam)
- ✅ Dashboard com estatísticas de envio
- ✅ Fácil de configurar (apenas API key)

### Como configurar:

1. **Criar conta no Resend:**
   - Acesse: https://resend.com
   - Crie uma conta gratuita (100 e-mails/dia grátis)
   - Vá em **API Keys** e crie uma nova chave

2. **Configurar domínio (opcional mas recomendado):**
   - Vá em **Domains** e adicione seu domínio
   - Configure os registros DNS conforme instruções
   - Isso melhora a deliverability

3. **Configurar variáveis de ambiente no Render/Vercel:**

```env
# Resend API (recomendado para produção)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@seudominio.com

# URL base da aplicação (importante!)
APP_BASE_URL=https://seu-backend.onrender.com
```

### Instalar dependência (se necessário):

```bash
pip install httpx
```

---

## 🔧 Modo 2: SMTP Direto

**Melhor para:** Desenvolvimento local ou servidor próprio com SMTP configurado.

### Vantagens:
- ✅ Funciona sem serviços externos
- ✅ Bom para desenvolvimento/testes
- ✅ Pode usar Gmail, Outlook, etc. (não recomendado para produção)

### Como configurar:

1. **Para desenvolvimento local (Gmail exemplo):**

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASS=sua-senha-de-app  # Use "Senha de App" do Gmail, não a senha normal!
SMTP_FROM=seu-email@gmail.com

# URL base (local)
APP_BASE_URL=http://localhost:8000
```

2. **Para produção com servidor SMTP próprio:**

```env
SMTP_HOST=smtp.seudominio.com
SMTP_PORT=587
SMTP_USER=noreply@seudominio.com
SMTP_PASS=senha-segura
SMTP_FROM=noreply@seudominio.com

APP_BASE_URL=https://seu-backend.onrender.com
```

### ⚠️ Importante sobre Gmail:

Se usar Gmail, você precisa:
1. Ativar "Verificação em 2 etapas"
2. Criar uma "Senha de App" em: https://myaccount.google.com/apppasswords
3. Usar essa senha de app (não a senha normal da conta)

---

## 🎯 Qual modo usar?

### Desenvolvimento Local:
- Use **SMTP** com Gmail ou servidor local

### Produção (Render/Vercel):
- Use **Resend API** (mais confiável e fácil)

---

## 📝 Exemplo de Configuração no Render

1. Vá em **Environment** no seu serviço
2. Adicione as variáveis:

```
RESEND_API_KEY=re_xxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@seudominio.com
APP_BASE_URL=https://seu-backend.onrender.com
```

3. Salve e faça deploy

---

## 🧪 Testando

Após configurar, teste criando um novo usuário. O e-mail de verificação deve ser enviado automaticamente.

Se houver erro, verifique:
- ✅ Variáveis de ambiente configuradas corretamente
- ✅ No caso do Resend: API key válida e domínio verificado (ou use o domínio de teste)
- ✅ No caso do SMTP: credenciais corretas e porta não bloqueada

---

## 💡 Dica

O código automaticamente escolhe o modo:
- Se `RESEND_API_KEY` estiver configurado → usa Resend
- Caso contrário → usa SMTP

Isso permite desenvolvimento local com SMTP e produção com Resend sem mudar código!

