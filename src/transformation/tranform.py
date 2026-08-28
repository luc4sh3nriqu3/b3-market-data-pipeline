#%%
from ntpath import isfile
import pandas as pd
from pathlib import Path

# Dados da camada bronze
raw_data = Path(__file__).parent.parent.parent / 'data' / 'raw'

# Lendo todos os arquivos a partir do diretório data/raw
for path in raw_data.rglob('*'):
    if path.is_file():
        


#df = pd.read_parquet('../../data/raw/2026/07/14/b3_extract_210049.parquet')
#df.head(10)
# %%
