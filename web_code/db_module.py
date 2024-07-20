import mysql.connector
import pandas as pd
import numpy as np
import sys
import os

def db_connect():
    # Połączenie z bazą danych MySQL
    conn = mysql.connector.connect(
        host="localhost",
        user="guestuser",
        password="guest",
        database="ekstrabet"
    )
    '''conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            database=os.getenv('MYSQL_DATABASE'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD')
    )'''
    return conn