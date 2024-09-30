import os
import dotenv
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()
    return os.environ.get("POSTGRES_URI")

engine = create_engine("postgresql://postgres.lszbbhqpvvcfxicvybyw:zF_9uGSj64zgYKB@aws-0-us-west-1.pooler.supabase.com:6543/postgres", pool_pre_ping=True)
