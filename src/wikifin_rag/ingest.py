from dotenv import load_dotenv
import os
import psycopg

load_dotenv(override=True)

def get_db_connection():
    db_host = "localhost"
    db_port = 5432
    db_name = os.environ['POSTGRES_DB']
    db_user = os.environ['POSTGRES_USER']
    db_password = os.environ['POSTGRES_PASSWORD']

    return psycopg.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
        autocommit=True
    )