const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

// Base de dados em memória
let disciplinas = [
  { id: 1, nome: "Matemática", professor: "Carlos" },
  { id: 2, nome: "Física", professor: "Ana" },
  { id: 3, nome: "Química", professor: "José" }
];

let professores = [
  { id: 1, nome: "Carlos", departamento: "Matemática" },
  { id: 2, nome: "Ana", departamento: "Física" },
  { id: 3, nome: "José", departamento: "Química" }
];

// Rota raiz
app.get('/', (req, res) => {
  res.send('API Universidade funcionando! Use /disciplinas ou /professores');
});

// Disciplinas
app.get('/disciplinas', (req, res) => res.json(disciplinas));
app.get('/disciplinas/:id', (req, res) => {
  const disciplina = disciplinas.find(d => d.id == req.params.id);
  disciplina ? res.json(disciplina) : res.status(404).send("Disciplina não encontrada");
});
app.post('/disciplinas', (req, res) => {
  const nova = { id: disciplinas.length + 1, ...req.body };
  disciplinas.push(nova);
  res.status(201).json(nova);
});
app.put('/disciplinas/:id', (req, res) => {
  const index = disciplinas.findIndex(d => d.id == req.params.id);
  if(index !== -1){
    disciplinas[index] = { id: disciplinas[index].id, ...req.body };
    res.json(disciplinas[index]);
  } else res.status(404).send("Disciplina não encontrada");
});
app.delete('/disciplinas/:id', (req, res) => {
  const index = disciplinas.findIndex(d => d.id == req.params.id);
  if(index !== -1){
    const deleted = disciplinas.splice(index,1);
    res.json(deleted[0]);
  } else res.status(404).send("Disciplina não encontrada");
});

// Professores
app.get('/professores', (req, res) => res.json(professores));
app.get('/professores/:id', (req, res) => {
  const prof = professores.find(p => p.id == req.params.id);
  prof ? res.json(prof) : res.status(404).send("Professor não encontrado");
});
app.post('/professores', (req, res) => {
  const novo = { id: professores.length + 1, ...req.body };
  professores.push(novo);
  res.status(201).json(novo);
});
app.put('/professores/:id', (req, res) => {
  const index = professores.findIndex(p => p.id == req.params.id);
  if(index !== -1){
    professores[index] = { id: professores[index].id, ...req.body };
    res.json(professores[index]);
  } else res.status(404).send("Professor não encontrado");
});
app.delete('/professores/:id', (req, res) => {
  const index = professores.findIndex(p => p.id == req.params.id);
  if(index !== -1){
    const deleted = professores.splice(index,1);
    res.json(deleted[0]);
  } else res.status(404).send("Professor não encontrado");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
