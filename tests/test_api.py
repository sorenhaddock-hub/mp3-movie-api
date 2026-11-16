def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 20
    assert body["columns"] == 4
    assert body["column_names"] == ["title", "release_year", "rating", "genre"]


def test_get_movies_with_limit(client, uploaded):
    response = client.get("/movies", params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["total_rows"] == 20
    assert [row["id"] for row in body["data"]] == [1, 2]


def test_search_movies(client, uploaded):
    response = client.get(
        "/movies/search",
        params={"columns": ["title", "rating"], "min_rating": 8.5, "limit": 2},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    for row in rows:
        assert set(row.keys()) == {"id", "title", "rating"}
        assert row["rating"] >= 8.5
    # Sorted highest rating first
    assert rows[0]["rating"] >= rows[1]["rating"]


def test_upload_replaces_collection(client, sample_csv_bytes):
    for _ in range(2):
        response = client.post(
            "/upload",
            files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
        )
        assert response.status_code == 200

    response = client.get("/movies")
    assert response.json()["total_rows"] == 20


def test_search_unsupported_column(client, uploaded):
    response = client.get("/movies/search", params={"columns": ["director"]})
    assert response.status_code == 400


def test_process_movies(client, uploaded, processing_body):
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    report = response.json()["cleaning_report"]

    response = client.get("/movies")
    assert response.json()["total_rows"] == report["rows_after"]