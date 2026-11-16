from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from src.database import initialize_database


@pytest.fixture
def client(tmp_path):
    # Point the app's storage at a fresh temporary database for each test
    main.storage.db_path = str(tmp_path / "test_movies.db")
    initialize_database(main.storage.db_path)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def sample_csv_bytes():
    filepath = Path("fixtures") / "sample_movies.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": ["title", "rating"],
            "numeric_columns": ["rating"]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {"enabled": True, "axis": "rows"},
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }