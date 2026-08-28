# 📂 Estratégia de Ingestão: Camada Raw (Bronze)

Este subdiretório contém o componente inicial do pipeline, responsável por realizar a coleta de dados brutos do mercado financeiro e persisti-los de forma estruturada no nosso Data Lake local.

## 🛠️ O Script `extract.py`
O script `extract.py` foi projetado para ser um processo leve, resiliente e altamente modular. Ele consome dados da API pública do Yahoo Finance e prepara a camada de entrada do nosso sistema.

## 🏗️ Decisões Técnicas e Arquitetura da Ingestão
Durante o desenvolvimento deste módulo, tomamos decisões estratégicas de engenharia para garantir a estabilidade do pipeline em ambiente de produção:

**1. Método de Captura em Lote (Bulk Download)**<br>
Utilizamos o método yf.download() da biblioteca yfinance, ideal para realizar a extração simultânea de uma lista de ativos (tickers) em uma única requisição de rede.

- Dinâmica de Execução: O pipeline é executado em lote diário (Daily Batch EOD - End of Day), programado para rodar após o fechamento do pregão da B3. Se o mercado estiver aberto, capturamos a última cotação em tempo real; se estiver fechado, a API retorna automaticamente o preço de fechamento definitivo do dia útil atual (ou do último anterior).

**2. Estratégia de Janela Deslizante (Sliding Window) de 30 Dias**<br>
Em vez de baixar todo o histórico de dados a cada execução diária, o pipeline adota uma **Janela Deslizante de 30 dias** (`initial_date` calculada dinamicamente ou parametrizada para cobrir o último mês).

Esta abordagem substitui a carga histórica total diária para mitigar três problemas clássicos de produção:

- **Prevenção de Rate Limits:** Evita requisições abusivas e volumosas à API gratuita do Yahoo Finance, eliminando o risco de termos nosso endereço IP bloqueado por comportamento anômalo.

- **Otimização de Custo de Rede e I/O:** Transferir e processar apenas 30 dias de dados é infinitamente mais rápido, consumindo menos banda de rede e memória do servidor do que manipular anos de histórico diariamente.

- **Resiliência a Ajustes Retroativos (Corporate Actions):** No mercado financeiro, preços históricos sofrem ajustes retroativos devido a distribuições de dividendos, desdobramentos (*splits*) ou agrupamentos (*inplits*). A janela de 30 dias garante que qualquer ajuste recente feito pela B3 seja capturado e atualizado no nosso banco de dados via operações de *Upsert* nas camadas seguintes, blindando nosso banco contra dados dessincronizados.

**3. Normalização do Esquema (Achatamento de MultiIndex Colunar)**<br>
Ao baixar múltiplos ativos simultaneamente, o `yfinance` retorna um DataFrame estruturado em um índice de colunas multinível (*MultiIndex*), organizado hierarquicamente por (`Métrica, Ticker`).

**O Problema:** Estruturas de índices multiníveis violam a compatibilidade nativa de formatos modernos de armazenamento colunar (como o Parquet) e criam gargalos em motores de processamento distribuído (como o Apache Spark).

**A Solução:** Aplicamos uma etapa de engenharia de dados para "achatar" o esquema. Primeiro, transformamos o índice de datas em uma coluna comum (`Date`). Em seguida, combinamos as duas camadas colunares em strings únicas padronizadas no formato `Metrica_Ticker` (ex: `Close_ABEV3.SA`, `Open_BBDC4.SA`). O resultado é uma **Wide Table (Tabela Larga)** limpa e otimizada para persistência rápida.

**4. Mecanismo de Auditoria e Particionamento Físico**<br>
- **Idempotência no Armazenamento:** Para suportar múltiplas execuções no mesmo dia (como em casos de reprocessamento por falhas temporárias) sem riscos de colisão ou corrupção de dados, criamos uma árvore de diretórios física particionada por data (`data/raw/ANO/MES/DIA/`).

- **timestamp no Nome do Arquivo:** O arquivo `.parquet` gerado recebe a marcação temporal exata da execução limpa de caracteres especiais (ex: `b3_extract_193000.parquet`). Se uma execução falhar, conseguimos reprocessá-la sem afetar ou sobrescrever os arquivos consolidados anteriormente no mesmo dia.

- **Injeção de Metadados (Lineage):** Injetamos a coluna interna `extracted_at` (com timestamp UTC) diretamente dentro da estrutura do dado. Isso garante que a rastreabilidade do momento exato da extração acompanhe o dado de forma independente, permitindo que a camada Silver aplique regras de deduplicação sem depender do nome do arquivo físico.

- **Design Cross-Platform:** Toda a navegação de diretórios e criação física de pastas utiliza a biblioteca `pathlib.Path`. Isso garante que o pipeline funcione de forma transparente e agnóstica em qualquer sistema operacional (Windows, Linux, macOS) ou dentro de contêineres Docker.

## 🚀 Otimização do Armazenamento (Formato Apache Parquet)
A escrita dos arquivos brutos na camada Raw é feita utilizando o formato **Apache Parquet** (`to_parquet`) em substituição ao tradicional CSV. Esta decisão técnica baseia-se em:

1. **Compressão Colunar Eficiente:** Reduz drasticamente o espaço de armazenamento local através de dicionários de compressão nativos.

2. **Preservação de Tipagem Forte:** O Parquet armazena nativamente os metadados dos tipos de dados. Isso evita que colunas numéricas de preços ou colunas de data sofram inferências errôneas ou se percam como texto bruto na hora de carregar os arquivos nas próximas etapas do pipeline.