Aqui está a versão final e completa do seu arquivo `README.md`, totalmente atualizada para refletir todas as funcionalidades e melhorias que implementamos no seu projeto.

Este guia serve como a documentação definitiva para instalar, configurar e rodar o seu aplicativo.

-----

# Kakeibo - Gestor Financeiro Pessoal

Um aplicativo de gestão financeira pessoal (Kakeibo) desenvolvido em Python com a interface Streamlit e um banco de dados MySQL. Este software permite gerenciar receitas e despesas de forma simples e intuitiva, com foco na usabilidade e na precisão financeira.

## 🚀 Funcionalidades

  * **Autenticação por Senha:** Proteção de acesso com uma senha inicial que pode ser alterada.
  * **Gestão de Transações:** Registre receitas e despesas com valor em JPY (sem decimais).
  * **Visão Geral Mensal:** Painel inicial com resumo financeiro do mês (receitas, despesas e saldo).
  * **Calendário Interativo:** Um calendário responsivo que exibe eventos coloridos para receitas, despesas a pagar, contas pagas e atrasadas.
  * **Análise de Gastos:** Visualize suas despesas por categoria através de um gráfico de barras interativo, com filtros de mês e ano.
  * **Histórico de Registros:** Visualização completa das transações com paginação.
  * **Ações de Registro:** Edite, pague ou **exclua** qualquer registro de transação.
  * **Formulários Otimizados:** Os campos dos formulários são limpos automaticamente após o registro ou edição, garantindo um fluxo de trabalho contínuo.
  * **Configurações Personalizáveis:** Gerencie a senha, adicione novas categorias de transações e formas de pagamento diretamente pelo aplicativo.

-----

## 🛠️ Tecnologias Utilizadas

  * **Python:** Linguagem de programação principal.
  * **Streamlit:** Framework para a construção da interface web interativa.
  * **MySQL:** Banco de dados relacional para armazenamento de dados.
  * **`streamlit-calendar`:** Componente de calendário responsivo para Streamlit.
  * **`pandas`:** Biblioteca para manipulação e análise de dados.
  * **`altair`:** Biblioteca para a criação de gráficos de barras robustos.
  * **`mysql-connector-python`:** Biblioteca para conexão do Python com o MySQL.

-----

## ⚙️ Instalação e Configuração

### Pré-requisitos

Certifique-se de que você tem o **Python 3.7+** e um servidor **MySQL** instalados em sua máquina.

### 1\. Crie a Estrutura de Arquivos

Em seu computador, crie a pasta do projeto e as subpastas necessárias:

```bash
/caminho/para/seu/projeto/
├── .streamlit/
│   └── secrets.toml
├── app.py
└── requirements.txt
```

### 2\. Instale as Bibliotecas

Copie o conteúdo do `requirements.txt` fornecido anteriormente para o arquivo correspondente em sua pasta. Em seguida, abra seu terminal, navegue até a pasta do projeto e execute o comando para instalar todas as dependências de uma vez:

```bash
pip install -r requirements.txt
```

### 3\. Configure o Banco de Dados

Abra um cliente MySQL (como o MySQL Workbench) e execute o script abaixo para criar o banco de dados e as tabelas necessárias.

```sql
-- Cria o banco de dados
CREATE DATABASE IF NOT EXISTS kakeibo_db;

-- Seleciona o banco de dados
USE kakeibo_db;

-- Tabela para armazenar todas as transações (valor sem decimais para JPY)
CREATE TABLE IF NOT EXISTS transacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    valor DECIMAL(10, 0) NOT NULL,
    data DATE NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    descricao TEXT,
    forma_pagamento VARCHAR(20),
    pago BOOLEAN NOT NULL DEFAULT 0
);

-- Tabela para armazenar configurações do sistema
CREATE TABLE IF NOT EXISTS configuracoes (
    nome VARCHAR(50) PRIMARY KEY,
    valor VARCHAR(255)
);

-- Insere os dados iniciais do sistema
INSERT INTO configuracoes (nome, valor) VALUES
('senha', '230788'),
('categorias', 'Salário,Vale,Alimentação,Transporte,Lazer,Contas,Moradia,Saúde,Outros'),
('formas_pagamento', 'Dinheiro,Cartão de Crédito,Cartão de Débito,Transferência,Pix');
```

### 4\. Configure as Credenciais

Dentro da pasta `.streamlit`, crie o arquivo **`secrets.toml`** e adicione suas credenciais do MySQL.

```toml
[mysql]
host = "localhost"
user = "seu_usuario"
password = "sua_senha"
database = "kakeibo_db"
```

### 5\. Cole o Código do Aplicativo

No arquivo **`app.py`**, cole o código completo do projeto.

-----

## 🚀 Como Rodar o Aplicativo

### Execução Local

Para rodar o aplicativo na sua máquina (acessível apenas por `localhost`), execute o comando na pasta do projeto:

```bash
streamlit run app.py
```

### Acesso Externo

Para que o aplicativo seja acessível por outros dispositivos na mesma rede ou pela internet (após configurar o roteador e o firewall), execute:

```bash
streamlit run app.py --server.port 8050 --server.address 0.0.0.0
```

-----

## ⏰ Execução Automática no Windows

Para iniciar o aplicativo automaticamente quando o PC ligar, use o **Agendador de Tarefas do Windows**.

1.  Abra o **Agendador de Tarefas**.
2.  Clique em **"Criar Tarefa Básica..."**.
3.  Defina o nome da tarefa (`Kakeibo App`).
4.  No disparador, selecione **"Quando o computador iniciar"**.
5.  Na ação, escolha **"Iniciar um programa"**.
6.  Preencha os campos exatamente assim:
      * **Programa/script:** `streamlit.exe` (ou o caminho completo para ele, ex: `C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python39\Scripts\streamlit.exe`)
      * **Adicionar argumentos:** `run "/caminho/para/seu/projeto/app.py" --server.port 8050 --server.address 0.0.0.0`
      * **Iniciar em:** `"/caminho/para/seu/projeto/"`
7.  Clique em `Concluir`.

Pronto\! Seu aplicativo Kakeibo será iniciado automaticamente no próximo boot do sistema.