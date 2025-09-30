# API Universidade

API REST em Node.js com dados em memória, representando Disciplinas e Professores.

## Recursos

### Disciplinas
- **GET** `/disciplinas` → Lista todas as disciplinas
- **GET** `/disciplinas/:id` → Retorna uma disciplina específica
- **POST** `/disciplinas` → Cria uma nova disciplina
- **PUT** `/disciplinas/:id` → Atualiza uma disciplina
- **DELETE** `/disciplinas/:id` → Remove uma disciplina

### Professores
- **GET** `/professores` → Lista todos os professores
- **GET** `/professores/:id` → Retorna um professor específico
- **POST** `/professores` → Cria um novo professor
- **PUT** `/professores/:id` → Atualiza um professor
- **DELETE** `/professores/:id` → Remove um professor

## Como executar

```bash
npm install
node index.js
