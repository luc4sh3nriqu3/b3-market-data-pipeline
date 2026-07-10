# ====================== IMPORTAÇÃO DE BIBLIOTECAS ======================

import yfinance as yf     # Biblioteca para extração de dados financeiros do Yahoo Finance
import datetime           # Para manipulação de datas e registro do momento da extração
from pathlib import Path  # Para manipulação de caminhos de arquivos e pastas de forma cross-platform (funciona em Windows, Mac, Linux)

# =======================================================================


# =============================== FUNÇÕES ===============================

def extract_data(tickers, start, end):

    # Extração dos dados: OHLCV (Open, High, Low, Close, Volume)
    # Parâmetros:
    # - tickers: lista de ativos definidos acima.
    # - start: data inicial para buscar o histórico.
    # - end: data final (hoje). O yfinance traz os dados até o dia anterior ou o momento atual se o mercado estiver aberto.
    tickets = yf.download(tickers=tickers, start=start, end=end)

    # Achtando o Multiindex das colunas para armazenamento em formato parquet
    # Transforma o índice de datas (Index) em uma coluna comum chamada 'Date'
    tickets = tickets.reset_index()

    # Combina as colunas de duas camadas (Ex: 'Close' e 'ABEV3.SA') em uma só (Ex: 'Close_ABEV3.SA')
    # Se a coluna não tiver segunda camada (como a 'Date'), mantém apenas o nome dela
    tickets.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in tickets.columns]

    # Criação de uma coluna de auditoria (metadado)
    # Isso é essencial em engenharia de dados para saber exatamente quando este lote específico foi extraído
    tickets['extracted_at'] = datetime.datetime.now(datetime.timezone.utc)

    return tickets


def save_raw_data(df, today):

    # Extração dos componentes da data atual para criar uma estrutura de pastas particionada (Data Lake)
    # O particionamento por ano, mês e dia facilita a leitura de dados incrementais no futuro
    YEAR = str(today.year)
    MONTH = f'{today.month:02d}'
    DAY = f'{today.day:02d}'

    # Pega a hora atual, remove os milissegundos para ficar limpo e tira os dois-pontos (:) 
    # para evitar problemas ao nomear arquivos no Windows
    TIME = str(today.time().replace(microsecond=0)).replace(':', '')
    
    # Definição do diretório base de destino dos dados.
    # '__file__' pega o caminho do script atual. '.parent.parent' sobe duas pastas.
    # O objetivo é salvar em uma camada "raw" (dados crus, exatamente como vieram da fonte)
    DATA_DIR = Path(__file__).parent.parent / 'data' / 'raw'

    # Construção do caminho particionado: data/raw/ANO/MES/DIA
    OUTPUT_DIR = DATA_DIR / YEAR / MONTH / DAY

    # Definição do nome do arquivo contendo o timestamp exato da extração para evitar sobrescrita
    name = f'b3_extract_{TIME}.parquet'

    OUTPUT_FILE = OUTPUT_DIR / name

    # Criação das pastas de destino fisicamente no sistema operacional
    # Parâmetros:
    # - parents=True: cria todas as pastas intermediárias (ex: data, raw, ANO, etc) caso não existam.
    # - exist_ok=True: não gera erro se a pasta já existir.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Exportação do dataframe para arquivo CSV.
    # ATENÇÃO: Mudei para index=True. O yfinance usa a Data dos pregões como o index do Dataframe. 
    # Se usar index=False, você perderá a coluna de Datas e terá apenas os valores das ações!
    df.to_parquet(str(OUTPUT_FILE))

# =======================================================================


# ========================== BLOCO DE EXECUÇÃO ==========================

# Definição dos ativos que serão extraídos. 
# No Yahoo Finance, todas as empresas listadas na bolsa brasileira (B3) precisam do sufixo '.SA'
tickers = ['BBDC4.SA', 'ABEV3.SA', 'ITUB3.SA']

# Definição do horizonte de tempo (janela de dados) para a extração
initial_date = '2020-01-01'                             # Data de início do histórico desejado
today = datetime.datetime.now(datetime.timezone.utc)    # Data e hora atual (limite final da extração)

df = extract_data(tickers, initial_date, today)

save_raw_data(df, today)

# =======================================================================
