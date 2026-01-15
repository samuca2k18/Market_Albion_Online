# 🔍 Debug: Email não está chegando

## ✅ Status 200 mas email não recebido

Se você recebeu status **200** mas não recebeu o email, siga este guia de diagnóstico:

---

## 📋 Checklist de Verificação

### 1. Verificar Logs do Render

**IMPORTANTE:** Os logs agora mostram exatamente o que está acontecendo.

1. Acesse: Render Dashboard → Seu Serviço → **Logs**
2. Procure por estas mensagens:

**Se aparecer:**
```
Iniciando envio de email de verificação para seu@email.com
Conectando ao SMTP smtp.gmail.com:587 como marketalbionbr@gmail.com
Iniciando TLS...
Fazendo login no SMTP...
Enviando email para seu@email.com...
Email enviado com sucesso para seu@email.com
```
✅ **Email foi enviado com sucesso!** Verifique spam.

**Se aparecer:**
```
ERRO ao reenviar email para seu@email.com: Erro de autenticação SMTP
```
❌ **Problema:** Senha de App do Gmail incorreta ou expirada

**Se aparecer:**
```
SMTP não configurado. Variáveis faltando: SMTP_PASS
```
❌ **Problema:** Variáveis de ambiente não configuradas

---

### 2. Verificar Variáveis de Ambiente no Render

Certifique-se de que TODAS estas variáveis estão configuradas:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx  # Senha de App (16 caracteres)
SMTP_FROM=marketalbionbr@gmail.com
APP_BASE_URL=https://seu-frontend.vercel.app
```

**Como verificar:**
1. Render Dashboard → Seu Serviço → **Environment**
2. Confirme que todas as variáveis `SMTP_*` estão lá
3. **IMPORTANTE:** `SMTP_PASS` deve ser a **Senha de App**, não a senha normal

---

### 3. Verificar Senha de App do Gmail

A senha de app pode ter expirado ou estar incorreta.

**Como gerar nova senha de app:**
1. Acesse: https://myaccount.google.com/apppasswords
2. Faça login com `marketalbionbr@gmail.com`
3. Se não tiver "Verificação em 2 etapas" ativada, ative primeiro
4. Gere uma nova senha de app:
   - App: **E-mail**
   - Dispositivo: **Outro** → Digite: "Albion Market"
5. Copie a senha (16 caracteres)
6. Atualize `SMTP_PASS` no Render

---

### 4. Verificar Pasta de Spam

O Gmail pode estar marcando como spam:
- ✅ Verifique a pasta **Spam/Lixo Eletrônico**
- ✅ Procure por emails de `marketalbionbr@gmail.com`
- ✅ Se encontrar, marque como "Não é spam"

---

### 5. Verificar Limite do Gmail

**Limites do Gmail:**
- **500 e-mails/dia** para contas pessoais
- Se exceder, o Gmail bloqueia temporariamente

**Como verificar:**
- Tente enviar um email manualmente do Gmail
- Se não conseguir, pode ter excedido o limite
- Aguarde algumas horas ou use outra conta

---

### 6. Testar Configuração SMTP Manualmente

Você pode testar se o SMTP está funcionando usando Python:

```python
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "marketalbionbr@gmail.com"
SMTP_PASS = "sua-senha-de-app-aqui"
SMTP_FROM = "marketalbionbr@gmail.com"
TO_EMAIL = "seu-email-de-teste@gmail.com"

msg = MIMEText("Teste de email")
msg["Subject"] = "Teste"
msg["From"] = SMTP_FROM
msg["To"] = TO_EMAIL

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [TO_EMAIL], msg.as_string())
    print("✅ Email enviado com sucesso!")
except Exception as e:
    print(f"❌ Erro: {e}")
```

---

## 🔍 Mensagens de Log Esperadas

### ✅ Sucesso (email enviado):
```
Iniciando envio de email de verificação para usuario@email.com
Conectando ao SMTP smtp.gmail.com:587 como marketalbionbr@gmail.com
Iniciando TLS...
Fazendo login no SMTP...
Enviando email para usuario@email.com...
Email enviado com sucesso para usuario@email.com
Email de verificação enviado com sucesso para usuario@email.com
```

### ❌ Erro de Autenticação:
```
ERRO ao reenviar email para usuario@email.com: Erro de autenticação SMTP. Verifique SMTP_USER e SMTP_PASS: ...
```
**Solução:** Gere nova senha de app do Gmail

### ❌ Variáveis não configuradas:
```
ERRO ao reenviar email para usuario@email.com: SMTP não configurado. Variáveis faltando: SMTP_PASS
```
**Solução:** Configure todas as variáveis SMTP no Render

### ❌ Erro de Conexão:
```
ERRO ao reenviar email para usuario@email.com: Erro de conexão SMTP: ...
```
**Solução:** Verifique firewall ou rede

---

## 💡 Próximos Passos

1. **Verifique os logs do Render** (mais importante!)
2. **Confirme todas as variáveis SMTP** estão configuradas
3. **Gere nova senha de app** se necessário
4. **Verifique spam** no email de destino
5. **Aguarde alguns minutos** - emails podem demorar

---

## 🆘 Se Nada Funcionar

Considere migrar para **Resend API**:
- Mais confiável
- Melhor deliverability
- Dashboard com estatísticas
- 100 emails/dia grátis

Veja: `EMAIL_SETUP.md` → Seção "Alternativa: Resend API"

