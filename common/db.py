"""Thin Azure SQL connection helper. Modules own their SQL."""

import os
import struct

import pyodbc

# https://learn.microsoft.com/sql/connect/odbc/using-azure-active-directory :
# the token is passed as this pre-connect attribute, not a connection-string
# keyword. ODBC's own `Authentication=ActiveDirectoryDefault` doesn't exist
# (that mode is Microsoft.Data.SqlClient/.NET-only); fetching the token via
# azure-identity is what actually gets managed-identity/az-login/VS Code
# credential resolution in Python.
_SQL_COPT_SS_ACCESS_TOKEN = 1256
_SQL_SCOPE = "https://database.windows.net/.default"


def _access_token_struct() -> bytes:
    from azure.identity import DefaultAzureCredential  # deferred: not needed for SQL_CONNECTION_STRING path

    token = DefaultAzureCredential().get_token(_SQL_SCOPE).token
    token_bytes = token.encode("utf-16-le")
    return struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)


def get_connection() -> pyodbc.Connection:
    """Connect to Azure SQL.

    SQL_CONNECTION_STRING wins when set (local dev / SQL auth). Otherwise the
    connection string is built from SQL_SERVER + SQL_DATABASE and an Entra
    access token is fetched via DefaultAzureCredential, which resolves managed
    identity in Azure and az-login / VS Code credentials locally.
    """
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if conn_str:
        return pyodbc.connect(conn_str, autocommit=False)

    server = os.environ["SQL_SERVER"]
    database = os.environ["SQL_DATABASE"]
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{server},1433;Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(
        conn_str,
        autocommit=False,
        attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: _access_token_struct()},
    )
