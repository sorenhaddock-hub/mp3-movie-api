from pathlib import Path

import pandas as pd
import pytest

from src import MovieStorage
import main


def test_movies_persist(client, test_storage, uploaded_movies):
    # A brand-new storage object reading the same database file
    other = MovieStorage(test_storage.db_path)

    df = other.get()
    assert other.count_movies() == 20
    assert len(df) == 20
    assert list(df.columns) == ["title", "release_year", "rating", "genre"]

    original = pd.read_csv(Path("fixtures") / "sample_movies.csv")
    assert list(df["title"]) == list(original["title"])

    db_ids = [row["id"] for row in other.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]

    assert db_ids == list(range(1, 21))
    assert api_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    # 1. First retrievals are cached
    response_100 = client.get("/movies", params={"limit": 100})
    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies", params={"limit": 1})
    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()

    # 2. Repeat returns the same response
    repeat = client.get("/movies", params={"limit": 100})
    assert repeat.status_code == 200
    assert repeat.json() == response_100.json()

    # 3. Processing changes the data and clears the cache
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 0
    assert body["cleaning_report"]["rows_before"] == 20
    assert body["cleaning_report"]["rows_after"] == 16
    assert body["cleaning_report"]["rows_removed"] == 4

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    # 4. Fresh retrieval shows the processed data and is cached again
    after = client.get("/movies", params={"limit": 100})
    assert after.status_code == 200
    after_body = after.json()
    assert after_body["total_rows"] == 16

    titles = [row["title"] for row in after_body["data"]]
    assert titles == [f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"]

    ids = [row["id"] for row in after_body["data"]]
    assert ids == list(range(1, 17))

    assert main.cache.get(100) == after_body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # 1. Populate the cache
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    # 2. Make any database read fail the test
    def fail_if_called(*args, **kwargs):
        pytest.fail("Database was accessed on a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    # 3. Same request must be served from the cache
    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()