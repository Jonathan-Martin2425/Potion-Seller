import os
import dotenv
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()
    return os.environ.get("POSTGRES_URI")


i = 1
i_str = str(i)
print(i_str)
engine = create_engine(database_connection_url(), pool_pre_ping=True)
