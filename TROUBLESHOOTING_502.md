# 🔧 Solução para Erro 502 no Reenvio de Email

## 🐛 Problema

Erro **502 Bad Gateway** ao tentar reenviar email de verificação.

## 🔍 Causas Possíveis

1. **Timeout do SMTP** - Conexão com Gmail demorando muito
2. **Timeout do Render** - Requisição excedendo 30 segundos
3. **Erro não tratado** - Exceção causando crash da requisição

## ✅ Soluções Implementadas

### 1. Timeout no SMTP (10 segundos)

O código agora tem timeout de 10 segundos na conexão SMTP:

```python
with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_FROM, [to_email], msg.as_string())
```

### 2. Tratamento de Erros Melhorado

Todos os erros são capturados e logados, mas retornam resposta neutra ao usuário:

```python
try:
    send_verification_email(user.email, token)
except Exception as e:
    logging.error(f"Erro ao reenviar email: {str(e)}")
    return neutral  # Não expõe erro, evita 502
```

## 🧪 Como Testar

1. Tente reenviar o email novamente
2. Verifique os logs do Render para ver se há erros específicos
3. Se ainda der 502, verifique:
   - ✅ Variáveis SMTP estão configuradas corretamente
   - ✅ Senha de App do Gmail está correta
   - ✅ Não há bloqueio de firewall

## 🔍 Verificar Logs no Render

1. Acesse o Dashboard do Render
2. Vá em **Logs** do seu serviço
3. Procure por erros relacionados a SMTP ou email
4. Os erros agora são logados com: `"Erro ao reenviar email para {email}: {erro}"`

## ⚠️ Se o Problema Persistir

### Verificar Configuração SMTP

Certifique-se de que todas as variáveis estão corretas no Render:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx  # Senha de App (16 caracteres)
SMTP_FROM=marketalbionbr@gmail.com
```

### Verificar Senha de App do Gmail

1. Acesse: https://myaccount.google.com/apppasswords
2. Verifique se a senha de app ainda está válida
3. Se necessário, gere uma nova senha de app
4. Atualize `SMTP_PASS` no Render

### Limites do Gmail

- **500 e-mails/dia** para contas pessoais
- Se exceder, o Gmail pode bloquear temporariamente
- Aguarde algumas horas ou use outra conta

## 💡 Alternativa: Usar Resend API

Se o problema persistir, considere migrar para Resend API:

1. Crie conta em: https://resend.com
2. Configure `RESEND_API_KEY` e `RESEND_FROM_EMAIL`
3. O código automaticamente usará Resend se essas variáveis estiverem configuradas

## 📝 Checklist de Diagnóstico

- [ ] Variáveis SMTP configuradas no Render
- [ ] Senha de App do Gmail válida
- [ ] Verificação em 2 etapas ativada no Gmail
- [ ] Não excedeu limite de 500 e-mails/dia
- [ ] Logs do Render não mostram erros específicos
- [ ] Timeout de 10 segundos está funcionando

---

**Última atualização:** Correções aplicadas com timeout e melhor tratamento de erros.

