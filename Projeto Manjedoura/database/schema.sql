CREATE TABLE Doencas (
  id_doenca INT AUTO_INCREMENT PRIMARY KEY,
  nome_doenca VARCHAR(255) NOT NULL,
  descricao TEXT
);

CREATE TABLE Vacinas (
  id_vacina INT AUTO_INCREMENT PRIMARY KEY,
  nome_vacina VARCHAR(255) NOT NULL,
  descricao TEXT
);

CREATE TABLE Gestacoes_Doencas (
  id_gest INT NOT NULL,
  id_doenca INT NOT NULL,
  data_diagnostico DATE NOT NULL,
  observacoes TEXT,
  PRIMARY KEY (id_gest, id_doenca),
  FOREIGN KEY (id_gest) REFERENCES Gestacoes(id_gest),
  FOREIGN KEY (id_doenca) REFERENCES Doencas(id_doenca)
);

CREATE TABLE CPAR (
  id_condicao INT AUTO_INCREMENT PRIMARY KEY,
  nome_condicao VARCHAR(255) NOT NULL,
  descricao TEXT
);

CREATE TABLE Gestacoes_Condicoes (
  id_gest INT NOT NULL,
  id_condicao INT NOT NULL,
  data_diagnostico DATE NOT NULL,
  observacoes TEXT,
  PRIMARY KEY (id_gest, id_condicao),
  FOREIGN KEY (id_gest) REFERENCES Gestacoes(id_gest),
  FOREIGN KEY (id_condicao) REFERENCES CPAR(id_condicao)
);

CREATE TABLE Registro_Consultas (
    id_cons INTEGER PRIMARY KEY AUTOINCREMENT,
    id_gest INTEGER NOT NULL,
    id_prof INTEGER NOT NULL,
    data_cons DATE NOT NULL,
    peso FLOAT,
    press_art CHAR(10),
    bat_fet CHAR(10),
    alt_ute FLOAT,
    obs TEXT,
    FOREIGN KEY (id_gest) REFERENCES Gestacoes (id) ON DELETE CASCADE,
    FOREIGN KEY (id_prof) REFERENCES Cadastro_Profissionais (id) ON DELETE CASCADE
);

CREATE TABLE Gestacoes_Vacinas (
    id_gest INTEGER NOT NULL,
    id_vacina INTEGER NOT NULL,
    data_aplicacao DATE,
    PRIMARY KEY (id_gest, id_vacina),
    FOREIGN KEY (id_gest) REFERENCES Gestacoes (id),
    FOREIGN KEY (id_vacina) REFERENCES Vacinas (id)
);

CREATE TABLE Gestacoes (
    id_gest INTEGER PRIMARY KEY AUTOINCREMENT,
    cns TEXT NOT NULL,
    dum DATE NOT NULL,
    dpp DATE NOT NULL,
    num_gestas INTEGER NOT NULL,
    risco TEXT
);

CREATE TABLE IF NOT EXISTS Cadastro_Gestantes (
    id INTEGER PRIMARY KEY,
    nome_gest TEXT NOT NULL,
    data_nasc DATE NOT NULL,
    cns INTEGER NOT NULL,
    pront TEXT NOT NULL,
    blood_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Cadastro_Profissionais (
    id_prof INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_prof TEXT NOT NULL,
    tipo_prof VARCHAR(20) NOT NULL DEFAULT 'Indefinido',
    username TEXT UNIQUE,
    senha TEXT
);
