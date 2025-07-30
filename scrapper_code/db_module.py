import mysql.connector

def db_connect():
    # Połączenie z bazą danych MySQL
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="radikey",
        database="ekstrabet"
    )
    return conn