# 📈 Pipeline ETL de Dados Financeiros da B3 (Ações & FIIs)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-pro)
![SQL](https://img.shields.io/badge/Banco%20de%20Dados-PostgreSQL-blue)
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
| Armazenamento  | Sistema de Arquivos Local (CSV) e Banco Relacional (PostgreSQL) |
| Carga/Conexão  | SQLAlchemy / Psycopg2   |
| Versionamento  | Git e GitHub            |

## 🏗️ Decisões de Arquitetura e Fluxo dos Dados

O pipeline segue o padrão de mercado para organização de Data Lakes e Data Warehouses, a **Arquitetura Medalhão**:

<p align=\"center">
        <img src="assets/pipeline-b3-v1.drawio.png" alt="Arquitetura do Projeto" width="800" height="270">
</p>

Abaixo estão detalhados os fundamentos técnicos e os trade-offs de engenharia ponderados para a concepção desta versão (v1) do pipeline, servindo como registro de governança e tomadas de decisão do projeto.

### 📂 Estratégia de Ingestão: Camada Raw (Bronze)

A camada *Raw* foi projetada sob o princípio da **imutabilidade** e da **preservação histórica total**. O objetivo é armazenar os dados exatamente como foram extraídos da fonte, permitindo reprocessamentos futuros sem perdas.

#### 🔄 Método de Captura em Lote (Bulk Download)

O pipeline utiliza o método `yf.download()`, ideal para a extração simultânea de uma lista de ativos (`tickers`) em uma única requisição de rede.
- **Dinâmica do Mercado:** O parâmetro `end=today` garante o comportamento ideal do fluxo. Se o pregão estiver aberto, capturamos a volatilidade do dia em tempo real; se o mercado estiver fechado, a API do Yahoo Finance consolida automaticamente o preço de fechamento definitivo do pregão atual ou do último dia útil anterior.

#### 📅 Abordagem por Snapshot Histórico Completo

A cada execução, o pipeline extrai a série histórica completa de todas as ações a partir de uma data de corte fixa (**01/01/2020**), gravando o resultado em partições físicas diárias (`data/raw/ANO/MES/DIA/`).

Essa abordagem de *Snapshot* (redundância estratégica) foi escolhida em vez de uma carga incremental diária devido a três fatores críticos de resiliência:

1. **Idempotência e Tolerância a Falhas:** Se o pipeline falhar ou for interrompido no meio da execução, o estado anterior do Data Lake permanece intacto. Como não há sobrescritas diretas, o processo é 100% idempotente (pode ser executado novamente sem corromper dados passados).

2. **Custo Computacional de I/O (Input/Output):** Fazer a leitura de uma série histórica de 5 anos para concatenar o dia de hoje na memória e reescrever o arquivo consolidado tornaria o pipeline excessivamente lento e caro à medida que o volume de dados crescesse.

3. **Proteção contra Eventos Corporativos Retroativos:** Ativos financeiros sofrem ajustes constantes devido a dividendos, desdobramentos (*splits*) e agrupamentos (*inplits*). Ao salvar o snapshot completo do histórico diariamente, preservamos o rastro exato de como o mercado enxergava o passado naquele momento do tempo, garantindo a **linhagem de dados (Data Lineage)** para auditoria.

#### 🛠️ Normalização do Esquema (Achatamento de MultiIndex Colunar)
Por padrão, ao baixar múltiplos ativos simultaneamente, o `yfinance` retorna um DataFrame com duas camadas de colunas (*MultiIndex*), organizadas hierarquicamente por `(Métrica, Ticker)`.

- **O Problema:** Estruturas de índices multiníveis violam a compatibilidade nativa de formatos de armazenamento modernos (como o Parquet) e dificultam a leitura por motores de processamento distribuído (como o Apache Spark).

- **A Solução:** Aplicamos uma etapa de engenharia de recursos para "achatar" o esquema. Primeiro, transformamos o índice de datas em uma coluna comum (`Date`). Em seguida, combinamos as camadas colunares em strings únicas padronizadas no formato `Metrica_Ticker` (ex: `Close_ABEV3.SA`, `Open_BBDC4.SA`). Isso resulta em uma **Wide Table (Tabela Larga)** limpa, otimizada e tipada.

#### ⏱️ Mecanismo de Auditoria e Particionamento Cross-Platform
- **Segurança de Escrita:** Para suportar múltiplas execuções intradiárias (micro-lotes) sem riscos de colisão de arquivos, o nome do arquivo gerado recebe a hora exata da extração limpa de caracteres especiais (ex: `b3_extract_153000.parquet`). Se uma carga específica falhar, o engenheiro consegue isolar e reprocessar aquele arquivo sem afetar as extrações anteriores do mesmo dia.

- **Injeção de Metadados:** Injetamos a coluna interna `extracted_at` com o timestamp em formato UTC diretamente no corpo do dado. Isso garante que a informação do momento da coleta não dependa do nome do arquivo, permitindo que as camadas futuras (Silver/Gold) apliquem regras de deduplicação eficientes.

- **Infraestrutura Portável:** Toda a resolução de caminhos de diretórios e criação física de pastas foi desenvolvida utilizando a biblioteca `pathlib.Path`. Isso assegura que o pipeline funcione de forma agnóstica em qualquer sistema operacional (Windows, Linux ou macOS) ou contêiner Docker.

#### 🚀 Otimização do Armazenamento (Formato Parquet)
Embora o tratamento inicial dos dados utilize estruturas comuns do ecossistema Python, a persistência final na camada Raw foi implementada utilizando o formato de arquivo **Apache Parquet** (`to_parquet`) em substituição ao tradicional CSV. Esta decisão técnica baseia-se em três pilares analíticos:

- **Compressão e Performance:** O Parquet é um formato colunar binário. Ele reduz drasticamente o espaço em disco através de dicionários de compressão nativos e acelera as consultas de leitura (I/O).

- **Preservação de Tipagem Forte:** Diferente do CSV (que armazena tudo como texto bruto e exige inferência de tipos na leitura), o Parquet armazena nativamente os metadados dos tipos de dados. Isso garante que colunas de preço permaneçam estritamente como numéricas (`float`) e datas permaneçam como timestamps (`datetime`), evitando corrupção de tipos em processos subsequentes (*downstream*).

### 📂 Silver (Trusted)
Camada onde o Python entra em ação com Pandas para aplicar as regras de saneamento: remoção de linhas nulas, tipagem correta de valores financeiros e padronização dos nomes das colunas para o padrão do banco (*snake_case*).

### 📂 Gold (Refined)
Os dados tratados são persistidos em um banco de dados relacional. Utilizando **SQL**, os dados são modelados e materializados em tabelas agregadas de performance (ex: valorização acumulada de 15 dias), otimizando o consumo de ferramentas de BI e Analytics.

## 📂 Estrutura do Projeto

```text
b3-market-data-pipeline/
│
├── assets/             # Imagens e recursos adicionais da documentação
│   └── pipeline-b3-v1.drawio.png
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

## ⚙️ Como Executar
**Pré-requisitos**
- Python 3.10 ou superior instalado.
- Banco de dados PostgreSQL configurado (ou utilização do SQLite nativo).

**Passo a Passo**
1. Clone o repositório:
```bash
git clone https://github.com/luc4sh3nriqu3/b3-market-data-pipeline.git
cd b3-market-data-pipeline
```
2. Crie o ambiente virtual:
```bash
python -m venv .venv
# No Windows:
.\.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```
4. Execute o pipeline:
```bash
python main.py
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