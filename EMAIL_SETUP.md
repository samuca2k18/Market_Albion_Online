# 📧 Configuração de Envio de E-mails com Gmail

Este projeto usa **SMTP do Gmail** para envio de e-mails de verificação.

## ⚡ Configuração Rápida

### Passo 1: Obter Senha de App do Gmail

**IMPORTANTE:** Você não pode usar a senha normal da conta. Precisa criar uma "Senha de App".

1. **Acesse:** https://myaccount.google.com/apppasswords
2. **Faça login** com `marketalbionbr@gmail.com`
3. **Se não tiver "Verificação em 2 etapas" ativada:**
   - Vá em: https://myaccount.google.com/security
   - Ative "Verificação em 2 etapas" primeiro
   - Volte para criar a senha de app
4. **Criar Senha de App:**
   - Em "Selecione o app" → escolha **"E-mail"**
   - Em "Selecione o dispositivo" → escolha **"Outro"** e digite: `Albion Market`
   - Clique em **"Gerar"**
5. **Copie a senha gerada:**
   - Será algo como: `abcd efgh ijkl mnop` (16 caracteres)
   - Você pode copiar com ou sem espaços

### Passo 2: Configurar Variáveis de Ambiente

#### Para Desenvolvimento Local (.env):

Crie um arquivo `.env` na raiz do projeto:

```env
# SMTP Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=abcd efgh ijkl mnop  # Cole a senha de app aqui
SMTP_FROM=marketalbionbr@gmail.com

# URL base do FRONTEND (importante!)
# O link no email vai para a página de verificação do frontend
APP_BASE_URL=http://localhost:5173  # URL do frontend local (Vite)
```

#### Para Produção (Render/Vercel):

1. Vá em **Environment Variables** no seu serviço
2. Adicione estas variáveis:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=abcd efgh ijkl mnop  # Senha de app do Gmail
SMTP_FROM=marketalbionbr@gmail.com

# URL base do FRONTEND (importante!)
# O link no email vai para a página de verificação do frontend
APP_BASE_URL=https://seu-frontend.vercel.app  # URL do frontend (Vercel)
```

3. **Salve** e faça deploy

### Passo 3: Testar

1. Inicie o servidor
2. Crie um novo usuário via `/signup`
3. Verifique se o e-mail de verificação foi enviado para a caixa de entrada

---

## 🔧 Solução de Problemas

### Erro: "SMTP não configurado"

**Causa:** Variáveis de ambiente não estão configuradas.

**Solução:**
- Verifique se todas as variáveis `SMTP_*` estão definidas
- No Render/Vercel, confirme que salvou as variáveis corretamente

### Erro: "Authentication failed" ou "Username and Password not accepted"

**Causa:** Senha de app incorreta ou não foi criada.

**Solução:**
1. Certifique-se de usar a **Senha de App**, não a senha normal
2. Verifique se a "Verificação em 2 etapas" está ativada
3. Gere uma nova senha de app se necessário
4. No `SMTP_PASS`, você pode usar com ou sem espaços

### E-mail não chega / Vai para spam

**Causa:** Gmail pode marcar como spam em alguns casos.

**Solução:**
- Verifique a pasta de **Spam/Lixo Eletrônico**
- Peça para o usuário marcar como "Não é spam"
- Para produção, considere usar um serviço profissional (Resend, SendGrid)

### Limite de envio do Gmail

**Limites do Gmail gratuito:**
- **500 e-mails/dia** para contas pessoais
- **2000 e-mails/dia** para contas Google Workspace

Se precisar enviar mais, considere:
- Criar múltiplas contas Gmail
- Usar um serviço profissional (Resend, SendGrid)

---

## 📝 Exemplo Completo

### Arquivo .env (desenvolvimento):

```env
# Banco de Dados
DATABASE_URL=postgresql+psycopg2://...

# JWT
SECRET_KEY=sua_chave_secreta_aqui

# SMTP Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=marketalbionbr@gmail.com
SMTP_PASS=abcd efgh ijkl mnop
SMTP_FROM=marketalbionbr@gmail.com

# URL base do FRONTEND (importante!)
# O link no email vai para a página de verificação do frontend
APP_BASE_URL=http://localhost:5173  # URL do frontend local (Vite)
```

### Variáveis no Render:

```
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = marketalbionbr@gmail.com
SMTP_PASS = abcd efgh ijkl mnop
SMTP_FROM = marketalbionbr@gmail.com
APP_BASE_URL = https://seu-frontend.vercel.app  # URL do FRONTEND (Vercel)
```

---

## 💡 Dicas

1. **Segurança:**
   - Nunca commite o arquivo `.env` no Git
   - A senha de app é específica para este uso, pode ser revogada a qualquer momento

2. **Testes:**
   - Teste primeiro localmente antes de fazer deploy
   - Use um e-mail de teste para verificar se está funcionando

3. **Produção:**
   - O Gmail funciona bem para começar
   - Se o projeto crescer, considere migrar para Resend ou SendGrid para melhor deliverability

---

## 🚀 Alternativa: Resend API (Futuro)

Se quiser usar um serviço profissional no futuro:

1. Crie conta em: https://resend.com
2. Configure `RESEND_API_KEY` e `RESEND_FROM_EMAIL`
3. O código automaticamente usará Resend se essas variáveis estiverem configuradas
4. Se não estiverem, usará SMTP do Gmail (como está agora)
