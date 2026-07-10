Abaixo estão detalhados os fundamentos técnicos e os trade-offs de engenharia ponderados para a concepção desta versão (v1) da camada de ingestão, servindo como registro de governança e tomadas de decisão do projeto.

# 📂 Estratégia de Ingestão: Camada Raw (Bronze)

A camada *Raw* foi projetada sob o princípio da **imutabilidade** e da **preservação histórica total**. O objetivo é armazenar os dados exatamente como foram extraídos da fonte, permitindo reprocessamentos futuros sem perdas.

## 🔄 Método de Captura em Lote (Bulk Download)

O pipeline utiliza o método `yf.download()`, ideal para a extração simultânea de uma lista de ativos (`tickers`) em uma única requisição de rede.
- **Dinâmica do Mercado:** O parâmetro `end=today` garante o comportamento ideal do fluxo. Se o pregão estiver aberto, capturamos a volatilidade do dia em tempo real; se o mercado estiver fechado, a API do Yahoo Finance consolida automaticamente o preço de fechamento definitivo do pregão atual ou do último dia útil anterior.

## 📅 Abordagem por Snapshot Histórico Completo

A cada execução, o pipeline extrai a série histórica completa de todas as ações a partir de uma data de corte fixa (**01/01/2020**), gravando o resultado em partições físicas diárias (`data/raw/ANO/MES/DIA/`).

Essa abordagem de *Snapshot* (redundância estratégica) foi escolhida em vez de uma carga incremental diária devido a três fatores críticos de resiliência:

1. **Idempotência e Tolerância a Falhas:** Se o pipeline falhar ou for interrompido no meio da execução, o estado anterior do Data Lake permanece intacto. Como não há sobrescritas diretas, o processo é 100% idempotente (pode ser executado novamente sem corromper dados passados).

2. **Custo Computacional de I/O (Input/Output):** Fazer a leitura de uma série histórica de 5 anos para concatenar o dia de hoje na memória e reescrever o arquivo consolidado tornaria o pipeline excessivamente lento e caro à medida que o volume de dados crescesse.

3. **Proteção contra Eventos Corporativos Retroativos:** Ativos financeiros sofrem ajustes constantes devido a dividendos, desdobramentos (*splits*) e agrupamentos (*inplits*). Ao salvar o snapshot completo do histórico diariamente, preservamos o rastro exato de como o mercado enxergava o passado naquele momento do tempo, garantindo a **linhagem de dados (Data Lineage)** para auditoria.

## 🛠️ Normalização do Esquema (Achatamento de MultiIndex Colunar)
Por padrão, ao baixar múltiplos ativos simultaneamente, o `yfinance` retorna um DataFrame com duas camadas de colunas (*MultiIndex*), organizadas hierarquicamente por `(Métrica, Ticker)`.

- **O Problema:** Estruturas de índices multiníveis violam a compatibilidade nativa de formatos de armazenamento modernos (como o Parquet) e dificultam a leitura por motores de processamento distribuído (como o Apache Spark).

- **A Solução:** Aplicamos uma etapa de engenharia de recursos para "achatar" o esquema. Primeiro, transformamos o índice de datas em uma coluna comum (`Date`). Em seguida, combinamos as camadas colunares em strings únicas padronizadas no formato `Metrica_Ticker` (ex: `Close_ABEV3.SA`, `Open_BBDC4.SA`). Isso resulta em uma **Wide Table (Tabela Larga)** limpa, otimizada e tipada.

## ⏱️ Mecanismo de Auditoria e Particionamento Cross-Platform
- **Segurança de Escrita:** Para suportar múltiplas execuções intradiárias (micro-lotes) sem riscos de colisão de arquivos, o nome do arquivo gerado recebe a hora exata da extração limpa de caracteres especiais (ex: `b3_extract_153000.parquet`). Se uma carga específica falhar, o engenheiro consegue isolar e reprocessar aquele arquivo sem afetar as extrações anteriores do mesmo dia.

- **Injeção de Metadados:** Injetamos a coluna interna `extracted_at` com o timestamp em formato UTC diretamente no corpo do dado. Isso garante que a informação do momento da coleta não dependa do nome do arquivo, permitindo que as camadas futuras (Silver/Gold) apliquem regras de deduplicação eficientes.

- **Infraestrutura Portável:** Toda a resolução de caminhos de diretórios e criação física de pastas foi desenvolvida utilizando a biblioteca `pathlib.Path`. Isso assegura que o pipeline funcione de forma agnóstica em qualquer sistema operacional (Windows, Linux ou macOS) ou contêiner Docker.

## 🚀 Otimização do Armazenamento (Formato Parquet)
Embora o tratamento inicial dos dados utilize estruturas comuns do ecossistema Python, a persistência final na camada Raw foi implementada utilizando o formato de arquivo **Apache Parquet** (`to_parquet`) em substituição ao tradicional CSV. Esta decisão técnica baseia-se em três pilares analíticos:

- **Compressão e Performance:** O Parquet é um formato colunar binário. Ele reduz drasticamente o espaço em disco através de dicionários de compressão nativos e acelera as consultas de leitura (I/O).

- **Preservação de Tipagem Forte:** Diferente do CSV (que armazena tudo como texto bruto e exige inferência de tipos na leitura), o Parquet armazena nativamente os metadados dos tipos de dados. Isso garante que colunas de preço permaneçam estritamente como numéricas (`float`) e datas permaneçam como timestamps (`datetime`), evitando corrupção de tipos em processos subsequentes (*downstream*).
