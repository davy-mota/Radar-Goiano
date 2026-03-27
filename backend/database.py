from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Coloque a sua password e o nome do seu banco de dados
senha_segura = quote_plus("gatodebotas") 
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') 

# Cria o "motor" de ligação
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais')