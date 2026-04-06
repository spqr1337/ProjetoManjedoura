# Projeto Manjedoura

Aplicacao Flask para cadastro e acompanhamento de gestantes, gestações, consultas e relatorios administrativos.

## Contexto academico

Este projeto faz parte da dissertacao de mestrado intitulada **"Desenvolvimento de um sistema local para o gerenciamento de dados de acompanhamento gestacional em Unidades Basicas de Saude: Uma alternativa segura e eficiente"**, de **Mohamad Nagashima de Oliveira**.

A pesquisa foi apresentada como requisito final para obtencao do titulo de **Mestre em Telessaude e Saude Digital** no **Programa de Pos-Graduacao em Telessaude e Saude Digital da Universidade do Estado do Rio de Janeiro (UERJ)**, no ano de **2025**, sob orientacao da **Profª. Drª. Rosa Maria Esteves Moreira da Costa**.

De acordo com a descricao do trabalho academico, o sistema foi proposto para enfrentar problemas de desorganizacao de dados gestacionais em Unidades Basicas de Saude, reduzindo a dependencia de planilhas online e oferecendo uma alternativa local mais aderente aos requisitos de seguranca e privacidade da **LGPD**.

O projeto adota um banco de dados relacional e uma interface web para apoiar o registro e a consulta de informacoes de acompanhamento gestacional, incluindo cadastro de gestantes, gestações, consultas, condicoes pre-existentes e doencas monitoradas.

## Estrutura

```text
Projeto Manjedoura/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── routes.py
│   ├── static/
│   └── templates/
├── data/
├── database/
│   └── schema.sql
├── .env.example
├── .gitignore
├── backend.py
├── README.md
├── requirements.txt
└── run.py
```

## Como executar

1. Crie e ative um ambiente virtual.
2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Coloque o banco SQLite em `data/projeto_manjedoura.db`.
4. Ajuste as variaveis de ambiente com base em `.env.example`, se necessario.
5. Inicie a aplicacao:

```bash
python run.py
```

Tambem funciona com:

```bash
python backend.py
```

## Banco de dados

O arquivo SQLite foi movido para `data/` e esta ignorado no Git para evitar publicar dados locais ou sensiveis. A estrutura do banco esta em `database/schema.sql`.

## Antes de subir para o GitHub

- Revise o banco local e remova dados sensiveis.
- Troque a `SECRET_KEY`.
- Confirme se usuarios e senhas de teste nao devem ser publicados.
- Execute `git init`, `git add .` e faça o primeiro commit.
