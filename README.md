# 📈 Pipeline ETL de Dados Financeiros da B3 (Ações & FIIs)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-pro)
![SQL](https://img.shields.io/badge/Banco%20de%20Dados-SQL-blue)
![Status](https://img.shields.io/badge/Status-Vers%C3%A3o%201.0-brightgreen)
![Educação](https://img.shields.io/badge/Foco-Engenharia%20de%20Dados-orange)

## 📖 Sobre o Projeto

Este projeto consiste na construção de um pipeline ETL (Extração, Transformação e Carga) para automação e estruturação de dados históricos de ativos da B3 (Ações e Fundos Imobiliários), utilizando dados públicos obtidos via biblioteca `yfinance` (Yahoo Finance).

O objetivo principal é simular o fluxo de engenharia de uma instituição financeira: capturar os dados diários de ativos selecionados (como PETR4, VALE3, HGLG11 e MXRF11), centralizar o histórico de forma segura e organizá-lo em uma arquitetura de camadas (**Raw, Silver e Gold**). Isso garante a qualidade, padronização e governança dos dados antes de sua disponibilização para consumo de analistas de negócio ou ferramentas de BI.

## 🎯 Problema de Negócio

Instituições financeiras e mesas de operações dependem de dados analíticos rápidos e confiáveis para tomar decisões de investimento. Consumir dados diretamente de APIs externas em tempo de execução gera gargalos de performance, custos desnecessários e riscos de inconsistência (dados nulos ou formatos incorretos).

Este pipeline resolve esse problema ao automatizar a ingestão e o saneamento dos dados de mercado. Ele preserva o histórico imutável na camada de entrada e materializa tabelas pré-agregadas no banco de dados, prontas para uso analítico com máxima performance e zero retrabalho de limpeza por parte dos analistas.

## 🛠️ Stack Utilizada

| Camada         | Tecnologia / Ferramenta |
| -------------- | ----------------------- |
| Fonte de Dados | API Yahoo Finance (`yfinance`) |
| Linguagem      | Python 3.10+            |
| Transformação  | Pandas                  |
| Armazenamento  | Sistema de Arquivos Local (CSV) e Banco Relacional (PostgreSQL/SQLite) |
| Carga/Conexão  | SQLAlchemy / Psycopg2   |
| Versionamento  | Git e GitHub            |

## 🏗️ Arquitetura de Medalhão (Medallion)

O pipeline segue o padrão de mercado para organização de Data Lakes e Data Warehouses:

### 📂 Raw (Bronze)
Armazena os dados históricos em formato `.csv` exatamente como foram retornados pela API, garantindo a imutabilidade e a possibilidade de reprocessamento em caso de falhas catastróficas.

### 📂 Silver (Trusted)
Camada onde o Python entra em ação com Pandas para aplicar as regras de saneamento: remoção de linhas nulas, tipagem correta de valores financeiros e padronização dos nomes das colunas para o padrão do banco (*snake_case*).

### 📂 Gold (Refined)
Os dados tratados são persistidos em um banco de dados relacional. Utilizando **SQL**, os dados são modelados e materializados em tabelas agregadas de performance (ex: valorização acumulada de 15 dias), otimizando o consumo de ferramentas de BI e Analytics.

## 📂 Estrutura do Projeto

```text
b3-market-data-pipeline/
│
├── data/               # Camada de Armazenamento Local (Ignorada no Git)
│   └── raw/            # Arquivos CSV brutos extraídos do yfinance
│
├── sql/                # Scripts de modelagem de dados
│   └── gold_queries.sql # Queries de criação e materialização da Camada Gold
│
├── src/                # Scripts modulares em Python (Código Fonte)
│   ├── extract.py      # Script de ingestão da API para a pasta Raw
│   ├── transform.py    # Script de limpeza e transformação com Pandas
│   └── load.py         # Script de conexão e carga para o Banco de Dados
│
├── main.py             # Script orquestrador principal do pipeline
├── requirements.txt    # Dependências do projeto
├── README.md           # Documentação
└── .gitignore          # Filtro de arquivos para o Git
```

## 🔄 Fluxo do Pipeline
```text
Yahoo Finance API
               │
               ▼
       Extração (Python)
               │
               ▼
        Camada RAW (CSV)
               │
               ▼
     Transformação (Pandas)
               │
               ▼
    Banco de Dados Relacional
     (Camada Silver/Trusted)
               │
               ▼
     Agregações / Views SQL
      (Camada Gold/Refined)
               │
               ▼
Tabelas Prontas para Consumo (BI / Analytics)
```

## 📌 Funcionalidades da V1.0

- Extração automatizada de histórico de preços de Ações e FIIs da B3.
- Salvamento imutável de arquivos na camada Raw (Data Lake local).
- Pipeline de higienização com Pandas (tratamento de nulos e renomeação técnica).
- Carga automatizada via SQLAlchemy em banco relacional.
- Scripts SQL para criação de tabelas gerenciais na camada Gold.


## 🚀 Próximas Melhorias (Roadmap)
- V2.0: Migrar a camada Raw e Silver para a nuvem utilizando buckets AWS S3 ou Azure Blob Storage.

- V2.1: Implementar modelagem dimensional (Star Schema) na camada de banco de dados.

- V3.0: Substituir a execução manual pela orquestração de fluxos com Apache Airflow ou Prefect rodando em containers Docker.

## 👩‍💻 Autor
**Lucas Henrique Amorim da Silva**
- Estudante de Ciência da Computação
- Foco de estudos em Engenharia de Dados e Arquitetura de Big Data


## 📄 Licença
Este projeto foi desenvolvido estritamente para fins educacionais e composição de portfólio de Engenharia de Dados.