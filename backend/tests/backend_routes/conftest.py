"""Pytest configuration and shared fixtures for the Defog backend tests.

This module provides the core test infrastructure including:
1. Database setup and cleanup for integration tests
2. Authentication fixtures (e.g., admin_token)
3. Shared configuration constants (e.g., database credentials, API endpoints)
4. Automatic cleanup of test data after test sessions

The fixtures and utilities in this file are automatically discovered and used by pytest,
making them available to all test files in the test suite without explicit imports.
This centralization helps maintain consistency across tests and reduces code duplication.
"""

import os
import random
import sys
import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_models import Project

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Configuration
BASE_URL = "http://localhost:1235"  # Backend server port

# Database credentials of the docker postgres container
DOCKER_DB_CREDS = {
    "user": os.environ.get("DEFOG_DBUSER", "postgres"),
    "password": os.environ.get("DEFOG_DBPASSWORD", "postgres"),
    "host": os.environ.get("DEFOG_DBHOST", "agents-postgres"),
    "port": os.environ.get("DEFOG_DBPORT", "5432"),
    "database": os.environ.get("DEFOG_DATABASE", "postgres"),
}

# Test database configuration
TEST_DB = {
    "db_name": "test_db",
    "db_type": "postgres",
    "db_creds": {
        "host": "agents-postgres",
        "port": 5432,
        "database": "test_db",
        "user": "postgres",
        "password": "postgres",
    },
}

USERNAME = "admin"
PASSWORD = "admin"


def setup_test_database():
    """Setup test database locally with the required schema.
    This only handles local database creation and schema setup.
    The registration of database credentials is tested separately.
    """
    # Setup the test database in user's local Postgres
    local_db_creds = {
        "user": "postgres",
        "password": "postgres",
        "host": "agents-postgres",
        "port": "5432",
        "database": "postgres",
    }

    # Connect to local postgres to create test_db
    local_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/{local_db_creds['database']}"
    local_engine = create_engine(local_uri)

    with local_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # Disconnect users from test_db if it exists
        conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'test_db'
                AND pid <> pg_backend_pid();
                """
            )
        )

        # Drop and recreate test_db
        conn.execute(text("DROP DATABASE IF EXISTS test_db;"))
        conn.execute(text("CREATE DATABASE test_db;"))

    # Connect to test_db and setup schema
    test_db_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/test_db"
    test_engine = create_engine(test_db_uri)

    # Read and execute the SQL setup file
    sql_file_path = os.path.join(os.path.dirname(__file__), "test_db.sql")
    with open(sql_file_path, "r") as f:
        sql_setup = f.read()

    with test_engine.begin() as conn:
        conn.execute(text(sql_setup))


def setup_test_db_name():
    """Setup test database name in Project table using SQLAlchemy ORM."""
    
    # Connect to the database where Project table exists
    docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
    engine = create_engine(docker_uri)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Check if db_name already exists
        existing_db = session.query(Project).filter_by(db_name=TEST_DB["db_name"]).first()

        if not existing_db:
            # Create new Project entry
            new_db_cred = Project(**TEST_DB)
            session.add(new_db_cred)
            session.commit()

def setup_test_db_metadata():
    """Sets up basic metadata for the test db by directly inserting into the metadata table"""
    # Connect to the database where metadata table exists
    docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
    engine = create_engine(docker_uri)
    
    # First, delete any existing metadata for the test DB
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM metadata WHERE db_name = '{TEST_DB['db_name']}'"))
    
    # Define metadata for the three tables in test_db.sql: customers, ticket_types, and ticket_sales
    metadata_entries = [
        # customers table
        {"db_name": TEST_DB["db_name"], "table_name": "customers", "column_name": "id", "data_type": "integer", "column_description": "Unique identifier for customer"},
        {"db_name": TEST_DB["db_name"], "table_name": "customers", "column_name": "name", "data_type": "varchar", "column_description": "Customer's full name"},
        {"db_name": TEST_DB["db_name"], "table_name": "customers", "column_name": "email", "data_type": "varchar", "column_description": "Customer's email address"},
        {"db_name": TEST_DB["db_name"], "table_name": "customers", "column_name": "created_at", "data_type": "timestamp", "column_description": "When the customer was added to the system"},
        
        # ticket_types table
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_types", "column_name": "id", "data_type": "integer", "column_description": "Unique identifier for ticket type"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_types", "column_name": "name", "data_type": "varchar", "column_description": "Name of ticket type. Can be Standard, VIP or Student"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_types", "column_name": "description", "data_type": "text", "column_description": "Description of the ticket type and its benefits"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_types", "column_name": "price", "data_type": "numeric", "column_description": "Price of the ticket in dollars"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_types", "column_name": "created_at", "data_type": "timestamp", "column_description": "When the ticket type was added to the system"},
        
        # ticket_sales table
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "id", "data_type": "integer", "column_description": "Unique identifier for ticket sale"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "customer_id", "data_type": "integer", "column_description": "Reference to the customer who purchased the ticket"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "ticket_type_id", "data_type": "integer", "column_description": "Reference to the type of ticket purchased"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "purchase_date", "data_type": "timestamp", "column_description": "When the ticket was purchased"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "valid_until", "data_type": "timestamp", "column_description": "Expiration date of the ticket"},
        {"db_name": TEST_DB["db_name"], "table_name": "ticket_sales", "column_name": "status", "data_type": "varchar", "column_description": "Current status of the ticket (active, used, expired)"}
    ]
    
    # Insert metadata entries
    with engine.begin() as conn:
        for entry in metadata_entries:
            conn.execute(
                text("""
                    INSERT INTO metadata (db_name, table_name, column_name, data_type, column_description)
                    VALUES (:db_name, :table_name, :column_name, :data_type, :column_description)
                """),
                entry
            )


def create_pdf_and_get_base_64(page_texts: list[str]):
    import os
    import tempfile
    import pymupdf
    import base64
    import random

    pdf_name = f"test_pdf_{random.randint(1, 1000)}.pdf"

    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, pdf_name)

    try:
        # create a pdf
        doc = pymupdf.Document()
        for page_text in page_texts:
            page = doc._newPage()
            page.insert_text([100, 100], page_text)

        doc.save(temp_file_path)
        doc.close()

        # read the pdf and get the base64
        with open(temp_file_path, "rb") as f:
            pdf_content = f.read()
            encoded_content = base64.b64encode(pdf_content).decode('utf-8')

            return pdf_name, temp_file_path, encoded_content
    except Exception as e:
        raise e


def cleanup_test_database(db_name):
    """
    Clean up a test database and its related metadata.
    
    This function:
    1. Removes database entries from metadata tables
    2. Drops the actual database
    
    Args:
        db_name: Name of the database to clean up
    """
    try:
        print(f"\n--- Running cleanup for database: {db_name} ---")
        
        # 1. Connect to postgres to clean up metadata entries
        docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
        docker_engine = create_engine(docker_uri)

        with docker_engine.begin() as conn:
            # Delete from metadata tables
            tables_with_db_name = [
                "metadata", "table_info", "instructions", "golden_queries",
                "analyses", "oracle_guidelines", "project"
            ]
            
            for table in tables_with_db_name:
                conn.execute(text(f"DELETE FROM {table} WHERE db_name = :db_name"), {"db_name": db_name})
            
            # Delete from oracle_reports where db_name is in a JSON column
            conn.execute(text("DELETE FROM oracle_reports WHERE db_name = :db_name"), {"db_name": db_name})
            
        print(f"--- Cleanup completed for database: {db_name} ---")
        
    except Exception as e:
        print(f"Warning: Failed to clean up test database {db_name}: {str(e)}")


@pytest.fixture
def admin_token():
    """Get admin token for authentication reusable across all the integration API tests as a fixture"""
    response = requests.post(
        f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """
    Cleanup fixture that runs once per session.
    After all tests finish, it removes everything related to the test_db from the database.
    """
    setup_test_database()
    setup_test_db_name()
    setup_test_db_metadata()

    yield

    # --- Cleanup code runs here, *after* all tests have completed ---
    print("\n--- Running cleanup for test_db ---")
    try:
        db_name = TEST_DB["db_name"]

        # 1. Get admin token for verification
        response = requests.post(
            f"{BASE_URL}/login", json={"username": USERNAME, "password": PASSWORD}
        )
        if response.status_code != 200:
            print("Failed to get admin token for cleanup verification.")
            return
        admin_token = response.json()["token"]

        # 2. Clean up all tables in the docker postgres container
        # Use the global DOCKER_DB_CREDS
        docker_uri = f"postgresql://{DOCKER_DB_CREDS['user']}:{DOCKER_DB_CREDS['password']}@{DOCKER_DB_CREDS['host']}:{DOCKER_DB_CREDS['port']}/{DOCKER_DB_CREDS['database']}"
        docker_engine = create_engine(docker_uri)

        with docker_engine.begin() as conn:
            # Delete from all tables where db_name is a column
            tables_with_db_name = [
                "metadata", "table_info", "instructions", "golden_queries",
                "analyses", "oracle_guidelines", 
                "project" 
            ]
            
            for table in tables_with_db_name:
                conn.execute(text(f"DELETE FROM {table} WHERE db_name = :db_name"), {"db_name": db_name})

            # Delete from oracle_reports where db_name is in a JSON column
            conn.execute(text("DELETE FROM oracle_reports WHERE db_name = :db_name"), {"db_name": db_name})

            # Delete any users created during tests
            conn.execute(text("DELETE FROM users WHERE username != :admin_user"), {"admin_user": USERNAME})

            # Delete all custom tools
            conn.execute(text("DELETE FROM custom_tools;"))

        # 3. Verify db_creds are deleted by calling get_tables_db_creds
        response = requests.post(
            f"{BASE_URL}/integration/get_tables_db_creds",
            json={"token": admin_token, "db_name": db_name},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 200 and not response.json().get("error"):
            print("Warning: Database credentials still exist after cleanup!")

        # 4. Drop the test database
        # Setup connection to postgres database
        local_db_creds = {
            "user": "postgres",
            "password": "postgres",
            "host": "agents-postgres",
            "port": "5432",
            "database": "postgres",
        }
        local_uri = f"postgresql://{local_db_creds['user']}:{local_db_creds['password']}@{local_db_creds['host']}:{local_db_creds['port']}/{local_db_creds['database']}"
        local_engine = create_engine(local_uri)

        with local_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'test_db'
                    AND pid <> pg_backend_pid();
                    """
                )
            )
            conn.execute(text("DROP DATABASE IF EXISTS test_db;"))

        print("--- Test cleanup completed successfully ---")

    except Exception as e:
        print(f"Cleanup failed with error: {str(e)}")