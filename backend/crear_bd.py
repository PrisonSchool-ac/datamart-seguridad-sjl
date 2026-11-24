import pyodbc

conexion = pyodbc.connect(
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;Trusted_Connection=yes;",
    autocommit=True,
)
conexion.execute(
    "IF DB_ID('DataMartSeguridad') IS NULL CREATE DATABASE DataMartSeguridad"
)
print("Base de datos lista")
