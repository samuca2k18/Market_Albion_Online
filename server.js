// server.js
const express = require('express');
const app = express();
app.use(express.json());

// --- Banco em memória ---
let disciplinas = [
  { id: 1, codigo: 'INF101', nome: 'Introdução à Programação', creditos: 4, periodo: 1 },
  { id: 2, codigo: 'MAT201', nome: 'Cálculo I', creditos: 5, periodo: 1 },
  { id: 3, codigo: 'FIS101', nome: 'Física Geral', creditos: 4, periodo: 1 }
];

let professores = [
  { id: 1, nome: 'Ana Souza', email: 'ana.souza@uni.edu', departamento: 'Computação' },
  { id: 2, nome: 'Bruno Lima', email: 'bruno.lima@uni.edu', departamento: 'Matemática' },
  { id: 3, nome: 'Carla Mendes', email: 'carla.mendes@uni.edu', departamento: 'Física' }
];

// Função para gerar próximo ID
function nextId(collection) {
  return collection.length === 0 ? 1 : Math.max(...collection.map(r => r.id)) + 1;
}

// --------------------- Rotas Disciplinas ---------------------

// Listar todas
app.get('/api/disciplinas', (req, res) => {
  res.json(disciplinas);
});

// Mostrar por id
app.get('/api/disciplinas/:id', (req, res) => {
  const id = Number(req.params.id);
  const disc = disciplinas.find(d => d.id === id);
  if (!disc) return res.status(404).json({ error: 'Disciplina não encontrada' });
  res.json(disc);
});

// Criar
app.post('/api/disciplinas', (req, res) => {
  const { codigo, nome, creditos, periodo } = req.body;
  if (!codigo || !nome || typeof creditos !== 'number' || typeof periodo !== 'number') {
    return res.status(400).json({ error: 'Dados inválidos. esperado: codigo, nome, creditos(number), periodo(number)' });
  }
  const exists = disciplinas.some(d => d.codigo === codigo);
  if (exists) return res.status(409).json({ error: 'Já existe disciplina com esse código' });

  const newDisc = { id: nextId(disciplinas), codigo, nome, creditos, periodo };
  disciplinas.push(newDisc);
  res.status(201).json(newDisc);
});

// Editar
app.put('/api/disciplinas/:id', (req, res) => {
  const id = Number(req.params.id);
  const discIndex = disciplinas.findIndex(d => d.id === id);
  if (discIndex === -1) return res.status(404).json({ error: 'Disciplina não encontrada' });

  const { codigo, nome, creditos, periodo } = req.body;
  if (!codigo || !nome || typeof creditos !== 'number' || typeof periodo !== 'number') {
    return res.status(400).json({ error: 'Dados inválidos. esperado: codigo, nome, creditos(number), periodo(number)' });
  }

  const conflict = disciplinas.some(d => d.codigo === codigo && d.id !== id);
  if (conflict) return res.status(409).json({ error: 'Outra disciplina já usa esse código' });

  const updated = { id, codigo, nome, creditos, periodo };
  disciplinas[discIndex] = updated;
  res.json(updated);
});

// Apagar
app.delete('/api/disciplinas/:id', (req, res) => {
  const id = Number(req.params.id);
  const before = disciplinas.length;
  disciplinas = disciplinas.filter(d => d.id !== id);
  if (disciplinas.length === before) return res.status(404).json({ error: 'Disciplina não encontrada' });
  res.status(204).send();
});

// --------------------- Rotas Professores ---------------------

// Listar todos
app.get('/api/professores', (req, res) => {
  res.json(professores);
});

// Mostrar por id
app.get('/api/professores/:id', (req, res) => {
  const id = Number(req.params.id);
  const p = professores.find(p => p.id === id);
  if (!p) return res.status(404).json({ error: 'Professor não encontrado' });
  res.json(p);
});

// Criar
app.post('/api/professores', (req, res) => {
  const { nome, email, departamento } = req.body;
  if (!nome || !email || !departamento) {
    return res.status(400).json({ error: 'Dados inválidos. esperado: nome, email, departamento' });
  }
  const exists = professores.some(p => p.email === email);
  if (exists) return res.status(409).json({ error: 'Já existe professor com esse email' });

  const newP = { id: nextId(professores), nome, email, departamento };
  professores.push(newP);
  res.status(201).json(newP);
});

// Editar
app.put('/api/professores/:id', (req, res) => {
  const id = Number(req.params.id);
  const idx = professores.findIndex(p => p.id === id);
  if (idx === -1) return res.status(404).json({ error: 'Professor não encontrado' });

  const { nome, email, departamento } = req.body;
  if (!nome || !email || !departamento) {
    return res.status(400).json({ error: 'Dados inválidos. esperado: nome, email, departamento' });
  }

  const conflict = professores.some(p => p.email === email && p.id !== id);
  if (conflict) return res.status(409).json({ error: 'Outro professor já usa esse email' });

  const updated = { id, nome, email, departamento };
  professores[idx] = updated;
  res.json(updated);
});

// Apagar
app.delete('/api/professores/:id', (req, res) => {
  const id = Number(req.params.id);
  const before = professores.length;
  professores = professores.filter(p => p.id !== id);
  if (professores.length === before) return res.status(404).json({ error: 'Professor não encontrado' });
  res.status(204).send();
});

// --------------------- Health check ---------------------
app.get('/api/health', (req, res) => res.json({ status: 'ok' }));

// Porta
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});

