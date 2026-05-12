from sqlalchemy import create_engine

# URL limpa! Lembre-se de colocar a senha correta que você descobriu/alterou
DATABASE_URL = "postgresql+psycopg2://postgres:gatodebotas@localhost:5433/radar_goiano"

engine = create_engine(DATABASE_URL)