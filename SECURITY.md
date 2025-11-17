# 🔒 Guia de Segurança

Este documento descreve as práticas de segurança implementadas e recomendações para uso em produção.

---

## 🛡️ Medidas de Segurança Implementadas

### 1. Autenticação e Autorização

- ✅ **JWT Tokens**: Tokens com expiração configurável
- ✅ **Hash de Senhas**: PBKDF2-SHA256 (sem limite de 72 bytes)
- ✅ **Validação de Credenciais**: Verificação rigorosa de usuário e senha
- ✅ **Proteção de Rotas**: Endpoints protegidos requerem autenticação

### 2. Validação de Dados

- ✅ **Pydantic Schemas**: Validação automática de entrada
- ✅ **Sanitização**: Normalização e limpeza de dados
- ✅ **Validação de E-mail**: Verificação de formato válido
- ✅ **Validação de Username**: Apenas caracteres alfanuméricos, `_` e `-`

### 3. Banco de Dados

- ✅ **SQL Injection Protection**: Uso de ORM (SQLAlchemy) com prepared statements
- ✅ **Pool de Conexões**: Configuração otimizada e segura
- ✅ **Transações**: Rollback automático em caso de erro

### 4. Configuração

- ✅ **Variáveis de Ambiente**: Credenciais não expostas no código
- ✅ **Arquivo .env**: Ignorado pelo Git
- ✅ **Chave Secreta**: Validação de presença obrigatória

### 5. Logging e Monitoramento

- ✅ **Logging Estruturado**: Registro de eventos importantes
- ✅ **Tratamento de Erros**: Handler global de exceções
- ✅ **Logs de Segurança**: Tentativas de login falhadas

---

## ⚠️ Configurações de Produção

### 1. Chave Secreta JWT

**IMPORTANTE:** Nunca use a chave padrão em produção!

**Gerar chave segura:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Configurar no .env:**
```env
SECRET_KEY=sua_chave_gerada_aqui
```

### 2. CORS (Cross-Origin Resource Sharing)

**Desenvolvimento:**
```python
allow_origins=["*"]  # Permite todas as origens
```

**Produção:**
```python
allow_origins=[
    "https://seu-dominio.com",
    "https://www.seu-dominio.com"
]
```

### 3. HTTPS

- ✅ Sempre use HTTPS em produção
- ✅ Configure certificados SSL válidos
- ✅ Use reverse proxy (Nginx, Traefik) com SSL

### 4. Variáveis de Ambiente

**Nunca commite:**
- ❌ Arquivo `.env`
- ❌ Credenciais de banco de dados
- ❌ Chaves secretas
- ❌ Tokens de API

**Use:**
- ✅ Variáveis de ambiente do servidor
- ✅ Serviços de gerenciamento de secrets (AWS Secrets Manager, HashiCorp Vault)
- ✅ Arquivo `.env.example` (sem valores reais)

### 5. Banco de Dados

**Recomendações:**
- ✅ Use conexões SSL/TLS
- ✅ Configure firewall para permitir apenas IPs autorizados
- ✅ Use usuário com permissões mínimas necessárias
- ✅ Faça backups regulares
- ✅ Monitore tentativas de acesso suspeitas

### 6. Rate Limiting

**Recomendado para produção:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/login")
@limiter.limit("5/minute")
def login(...):
    ...
```

### 7. Logging

**Configuração recomendada:**
- ✅ Logs em arquivo (não apenas console)
- ✅ Rotação de logs
- ✅ Nível de log apropriado (INFO em produção, DEBUG em desenvolvimento)
- ✅ Não logar informações sensíveis (senhas, tokens)

---

## 🔐 Boas Práticas

### 1. Senhas

- ✅ Mínimo de 6 caracteres (considere aumentar para 8+ em produção)
- ✅ Hash seguro (PBKDF2-SHA256)
- ✅ Nunca armazene senhas em texto plano
- ✅ Considere implementar política de senhas fortes

### 2. Tokens JWT

- ✅ Tempo de expiração adequado (60 minutos padrão)
- ✅ Use HTTPS para transmitir tokens
- ✅ Armazene tokens de forma segura no cliente
- ✅ Implemente refresh tokens para produção

### 3. Validação de Entrada

- ✅ Valide todos os dados de entrada
- ✅ Sanitize dados antes de processar
- ✅ Use whitelist ao invés de blacklist
- ✅ Limite tamanho de campos

### 4. Tratamento de Erros

- ✅ Não exponha detalhes internos em erros
- ✅ Use mensagens genéricas para usuários
- ✅ Log detalhes completos no servidor
- ✅ Implemente monitoramento de erros

---

## 🚨 Checklist de Segurança para Produção

Antes de colocar em produção, verifique:

- [ ] Chave secreta JWT configurada e segura
- [ ] CORS configurado apenas para domínios permitidos
- [ ] HTTPS habilitado
- [ ] Variáveis de ambiente configuradas corretamente
- [ ] Banco de dados com SSL/TLS
- [ ] Firewall configurado
- [ ] Rate limiting implementado
- [ ] Logging configurado adequadamente
- [ ] Backups do banco de dados configurados
- [ ] Monitoramento e alertas configurados
- [ ] Dependências atualizadas
- [ ] Testes de segurança realizados

---

## 📞 Reportar Vulnerabilidades

Se você encontrar uma vulnerabilidade de segurança:

1. **NÃO** abra uma issue pública
2. Entre em contato diretamente com o mantenedor
3. Forneça detalhes sobre a vulnerabilidade
4. Aguarde a correção antes de divulgar

---

## 📚 Recursos Adicionais

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Python Security](https://python.readthedocs.io/en/stable/library/secrets.html)

---

**Última atualização:** 2024-01-15

