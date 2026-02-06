# 🚨 Solução: Render Bloqueia SMTP

## ❌ Problema Identificado

**Erro:** `[Errno 101] Network is unreachable`

**Causa:** O Render **bloqueia conexões SMTP de saída** (porta 587) por segurança. Isso é comum em plataformas cloud.

**Solução:** Use **Resend API** ao invés de SMTP direto.

---

## ✅ Solução: Configurar Resend API

### Passo 1: Criar Conta no Resend

1. Acesse: **https://resend.com**
2. Crie uma conta gratuita (100 e-mails/dia grátis)
3. Faça login

### Passo 2: Obter API Key

1. No dashboard do Resend, vá em **API Keys**
2. Clique em **Create API Key**
3. Dê um nome (ex: "Albion Market")
4. Copie a chave gerada (começa com `re_`)

### Passo 3: Configurar Email Remetente

**Opção A: Usar domínio de teste (rápido para testar)**

1. No Resend, você pode usar o domínio de teste
2. O email será algo como: `onboarding@resend.dev`
3. **Limitação:** Só funciona para emails que você adicionar manualmente

**Opção B: Verificar seu próprio domínio (recomendado para produção)**

1. No Resend, vá em **Domains** → **Add Domain**
2. Digite seu domínio (ex: `marketalbion.com`)
3. Configure os registros DNS conforme instruções
4. Aguarde verificação (5-30 minutos)
5. Use: `noreply@marketalbion.com`

**Para começar rápido, use a Opção A!**

### Passo 4: Configurar Variáveis no Render

No Render Dashboard → Seu Serviço → **Environment**, adicione:

```env
# Resend API (substitui SMTP)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev  # Ou seu domínio verificado

# URL do frontend (para o link no email)
APP_BASE_URL=https://seu-frontend.vercel.app

# REMOVA ou deixe vazio estas variáveis SMTP:
# SMTP_HOST=
# SMTP_PORT=
# SMTP_USER=
# SMTP_PASS=
# SMTP_FROM=
```

### Passo 5: Fazer Deploy

1. Salve as variáveis no Render
2. O Render vai fazer deploy automaticamente
3. Teste novamente o reenvio de email

---

## 🎯 Como Funciona Agora

**Antes (SMTP - bloqueado):**
```
Backend → Tentar conectar SMTP → ❌ Bloqueado pelo Render
```

**Agora (Resend API - funciona):**
```
Backend → Chamar API do Resend → ✅ Resend envia o email
```

---

## 📝 Exemplo Completo de Configuração

### Variáveis no Render:

```
RESEND_API_KEY = re_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
RESEND_FROM_EMAIL = onboarding@resend.dev
APP_BASE_URL = https://seu-frontend.vercel.app
```

### Variáveis que NÃO são mais necessárias:

```
# Pode remover ou deixar vazio:
SMTP_HOST = 
SMTP_PORT = 
SMTP_USER = 
SMTP_PASS = 
SMTP_FROM = 
```

---

## ✅ Vantagens do Resend

- ✅ **Funciona no Render** (não bloqueado)
- ✅ **Mais confiável** (melhor deliverability)
- ✅ **Dashboard com estatísticas** (veja quantos emails foram enviados)
- ✅ **100 e-mails/dia grátis**
- ✅ **Mais rápido** (API HTTP ao invés de SMTP)

---

## 🧪 Testando

Após configurar:

1. Faça deploy no Render
2. Tente reenviar o email de verificação
3. Verifique os logs do Render - deve aparecer:
   ```
   Email de verificação enviado com sucesso para usuario@email.com
   ```
4. Verifique a caixa de entrada (e spam)

---

## 💡 Dica: Verificar Domínio Próprio (Opcional)

Se quiser usar `noreply@marketalbion.com`:

1. Compre um domínio (se não tiver)
2. No Resend → Domains → Add Domain
3. Configure DNS conforme instruções
4. Use `RESEND_FROM_EMAIL=noreply@marketalbion.com`

Mas para começar, `onboarding@resend.dev` funciona perfeitamente!

---

## 🆘 Se Ainda Não Funcionar

1. Verifique se `RESEND_API_KEY` está correto (começa com `re_`)
2. Verifique se `RESEND_FROM_EMAIL` está correto
3. Verifique os logs do Render para erros específicos
4. No Resend Dashboard → Emails, veja se há tentativas de envio

---

**Pronto!** Com Resend API, o email vai funcionar perfeitamente no Render! 🚀


