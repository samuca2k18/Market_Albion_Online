# 📝 Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

---

## [1.0.0] - 2024-01-15

### ✨ Adicionado

#### Segurança
- ✅ Validação obrigatória de `SECRET_KEY` via variáveis de ambiente
- ✅ Remoção de credenciais hardcoded do código
- ✅ Arquivo `.env.example` para configuração segura
- ✅ Melhorias no `.gitignore` para proteger arquivos sensíveis
- ✅ Validação de senha com mínimo de 6 caracteres
- ✅ Validação de username com regras específicas

#### Funcionalidades
- ✅ Endpoint `/health` para health check
- ✅ Tratamento global de exceções
- ✅ Logging estruturado em todas as operações
- ✅ Validação de duplicatas ao adicionar itens
- ✅ Normalização automática de nomes de itens (UPPERCASE)
- ✅ Ordenação de itens por data de criação
- ✅ Status detalhado nas respostas de preços

#### Documentação
- ✅ README.md completo e profissional
- ✅ API.md com documentação detalhada de todos os endpoints
- ✅ SECURITY.md com guia de segurança
- ✅ CHANGELOG.md para rastreamento de mudanças
- ✅ Documentação Swagger/OpenAPI melhorada
- ✅ Exemplos de uso com cURL
- ✅ Tags organizadas nos endpoints

#### Código
- ✅ Type hints em todas as funções
- ✅ Docstrings em todas as funções
- ✅ Validações Pydantic melhoradas
- ✅ Tratamento robusto de erros da API externa
- ✅ Timeout configurável para requisições externas
- ✅ Pool de conexões otimizado no banco de dados
- ✅ CORS configurado
- ✅ Validação de entrada aprimorada

#### Configuração
- ✅ Suporte completo a variáveis de ambiente
- ✅ Configuração de pool de conexões do banco
- ✅ Configuração de timeout da API externa
- ✅ Configuração de CORS
- ✅ Configuração de logging

### 🔧 Melhorado

- ✅ Tratamento de erros mais robusto e informativo
- ✅ Mensagens de erro mais descritivas
- ✅ Validação de dados mais rigorosa
- ✅ Performance do banco de dados (pool de conexões)
- ✅ Segurança geral do sistema
- ✅ Organização do código
- ✅ Documentação da API

### 🐛 Corrigido

- ✅ Remoção de credenciais hardcoded
- ✅ Validação de SECRET_KEY obrigatória
- ✅ Tratamento de erros da API externa
- ✅ Validação de dados de entrada
- ✅ Normalização de nomes de itens

### 🔒 Segurança

- ✅ Credenciais movidas para variáveis de ambiente
- ✅ Validação obrigatória de chave secreta
- ✅ Hash de senhas seguro (PBKDF2-SHA256)
- ✅ Proteção contra SQL Injection (ORM)
- ✅ Validação de entrada rigorosa
- ✅ Logging de tentativas de login falhadas

---

## Estrutura de Versionamento

Este projeto segue [Semantic Versioning](https://semver.org/):
- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Novas funcionalidades compatíveis
- **PATCH**: Correções de bugs compatíveis

---

## Formato

Este changelog segue o formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

**Última atualização:** 2024-01-15

