import pytest
import pandas as pd
import datetime
from unittest.mock import patch, MagicMock

# Importamos as funções do seu script principal (ajuste 'extract' para o nome do seu arquivo)
from extract import extract_data, save_raw_data

# ======================= FIXTURES =======================

@pytest.fixture
def fake_yfinance_data():
    """Cria um DataFrame falso imitando a estrutura exata (MultiIndex) que o yfinance devolve."""
    # O yfinance devolve colunas com 2 níveis (Métrica e Ticker)
    colunas_multiindex = pd.MultiIndex.from_tuples([
        ('Close', 'ITUB3.SA'),
        ('Close', 'ABEV3.SA'),
        ('Volume', 'ITUB3.SA')
    ])
    
    # O index do yfinance é a Data
    indice_datas = pd.to_datetime(['2026-08-01', '2026-08-02'])
    
    # Preenchemos com números aleatórios (2 linhas, 3 colunas)
    df_falso = pd.DataFrame(
        [[10.5, 15.0, 1000], [11.0, 14.8, 1200]], 
        index=indice_datas, 
        columns=colunas_multiindex
    )
    df_falso.index.name = 'Date'
    return df_falso


# ======================= TESTES =======================

# 1. Testando a Extração (Interceptamos o yfinance)
@patch('extract.yf.download')
def test_extract_data(mock_download, fake_yfinance_data):
    # Damos a instrução: quando rodar yf.download, devolva nosso df falso
    mock_download.return_value = fake_yfinance_data
    
    tickers = ['ITUB3.SA', 'ABEV3.SA']
    
    # Rodamos a sua função
    resultado = extract_data(tickers, '2026-08-01', '2026-08-03')
    
    # Garantimos que a sua função chamou o yfinance com os parâmetros corretos
    mock_download.assert_called_once_with(tickers=tickers, start='2026-08-01', end='2026-08-03')
    
    # Verificamos se o reset_index() funcionou (Date virou coluna)
    assert 'Date' in resultado.columns
    
    # Verificamos se o achatamento das colunas (MultiIndex) funcionou
    assert 'Close_ITUB3.SA' in resultado.columns
    assert 'Volume_ITUB3.SA' in resultado.columns
    
    # Verificamos se a coluna de auditoria foi criada
    assert 'extracted_at' in resultado.columns
    assert len(resultado) == 2  # Deve ter 2 linhas, igual ao nosso dado falso


# 2. Testando o Salvamento (Interceptamos a criação de pasta e arquivo)
@patch('extract.Path.mkdir')
@patch('pandas.DataFrame.to_parquet')
def test_save_raw_data(mock_to_parquet, mock_mkdir):
    # Criamos um DataFrame genérico qualquer só para testar o salvamento
    df_teste = pd.DataFrame({'coluna1': [1, 2]})
    
    # Fixamos uma data específica para saber exatamente qual nome de pasta o código deve gerar
    data_falsa = datetime.datetime(2026, 8, 27, 15, 30, 45, tzinfo=datetime.timezone.utc)
    
    # Rodamos a sua função
    save_raw_data(df_teste, data_falsa)
    
    # Verificamos se a função tentou criar a pasta com parents=True e exist_ok=True
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    # Pegamos o caminho que a sua função passou para o 'to_parquet'
    caminho_salvo = mock_to_parquet.call_args[0][0]
    
    # Verificamos se o particionamento ANO/MÊS/DIA está correto na string do caminho
    # No Windows usa \, no Linux/Mac usa /. Usamos 'in' para funcionar em qualquer um.
    assert '2026' in caminho_salvo
    assert '08' in caminho_salvo
    assert '27' in caminho_salvo
    
    # Verificamos se o nome do arquivo ignorou os milissegundos e os dois-pontos
    assert 'b3_extract_153045.parquet' in caminho_salvo