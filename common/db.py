"""Thin Azure SQL connection helper. Modules own their SQL."""

import os

import pyodbc


def get_connection() -> pyodbc.Connection:
    """Connect to Azure SQL.

    SQL_CONNECTION_STRING wins when set (local dev / SQL auth). Otherwise the
    connection string is built from SQL_SERVER + SQL_DATABASE using
    ActiveDirectoryDefault, which resolves managed identity in Azure and
    az-login / VS Code credentials locally.
    """
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if not conn_str:
        server = os.environ["SQL_SERVER"]
        database = os.environ["SQL_DATABASE"]
        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server=tcp:{server},1433;Database={database};"
            "Encrypt=yes;TrustServerCertificate=no;"
            "Authentication=ActiveDirectoryDefault;"
        )
    return pyodbc.connect(conn_str, autocommit=False)
