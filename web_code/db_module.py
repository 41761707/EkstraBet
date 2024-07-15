import mysql.connector
import pandas as pd
import numpy as np
import sys

def db_connect():
    # Połączenie z bazą danych MySQL
    conn = mysql.connector.connect(
        host="localhost",
        user="guestuser",
        password="guest",
        database="ekstrabet"
    )
    return conn