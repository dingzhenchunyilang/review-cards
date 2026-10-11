"""T3 — category CRUD tests."""
from app.database import DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME


def test_default_category_exists(client, categories_url):
    r = client.get(categories_url)
    assert r.status_code == 200
    cats = r.json()
    assert cats[0]["id"] == DEFAULT_CATEGORY_ID
    assert cats[0]["name"] == DEFAULT_CATEGORY_NAME
    assert cats[0]["card_count"] == 0


def test_create_category(client, categories_url):
    r = client.post(categories_url, json={"name": "Redis"})
    assert r.status_code == 201
    assert r.json()["name"] == "Redis"
    assert r.json()["id"] != DEFAULT_CATEGORY_ID


def test_create_category_trims_whitespace(client, categories_url):
    r = client.post(categories_url, json={"name": "  MySQL  "})
    assert r.status_code == 201
    assert r.json()["name"] == "MySQL"


def test_create_duplicate_category_rejected(client, categories_url):
    client.post(categories_url, json={"name": "Redis"})
    r = client.post(categories_url, json={"name": "Redis"})
    assert r.status_code == 400
    assert "已存在" in r.json()["detail"]


def test_create_duplicate_default_name_rejected(client, categories_url):
    r = client.post(categories_url, json={"name": DEFAULT_CATEGORY_NAME})
    assert r.status_code == 400


def test_create_empty_category_rejected(client, categories_url):
    r = client.post(categories_url, json={"name": "   "})
    assert r.status_code == 422


def test_rename_category(client, categories_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    r = client.put(f"{categories_url}/{cid}", json={"name": "Redis 缓存"})
    assert r.status_code == 200
    assert r.json()["name"] == "Redis 缓存"


def test_rename_to_existing_name_rejected(client, categories_url):
    client.post(categories_url, json={"name": "Redis"})
    cid = client.post(categories_url, json={"name": "MySQL"}).json()["id"]
    r = client.put(f"{categories_url}/{cid}", json={"name": "Redis"})
    assert r.status_code == 400


def test_rename_keeps_card_count(client, categories_url, cards_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    client.post(cards_url, json={"question": "Q1", "answer": "A1", "category_id": cid})
    client.post(cards_url, json={"question": "Q2", "answer": "A2", "category_id": cid})

    r = client.put(f"{categories_url}/{cid}", json={"name": "Redis 缓存"})
    assert r.status_code == 200
    assert r.json()["card_count"] == 2


def test_rename_default_category_rejected(client, categories_url):
    r = client.put(
        f"{categories_url}/{DEFAULT_CATEGORY_ID}", json={"name": "乱七八糟"}
    )
    assert r.status_code == 400


def test_rename_missing_category_404(client, categories_url):
    r = client.put(f"{categories_url}/9999", json={"name": "X"})
    assert r.status_code == 404


def test_delete_category_moves_cards_to_default(client, categories_url, cards_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    client.post(cards_url, json={"question": "Q1", "answer": "A1", "category_id": cid})

    r = client.delete(f"{categories_url}/{cid}")
    assert r.status_code == 204

    cats = client.get(categories_url).json()
    assert all(c["id"] != cid for c in cats)

    cards = client.get(cards_url).json()["items"]
    assert len(cards) == 1
    assert cards[0]["category_id"] == DEFAULT_CATEGORY_ID


def test_delete_category_updates_counts(client, categories_url, cards_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    client.post(cards_url, json={"question": "Q1", "answer": "A1", "category_id": cid})
    client.post(cards_url, json={"question": "Q2", "answer": "A2", "category_id": cid})

    cats = {c["id"]: c for c in client.get(categories_url).json()}
    assert cats[cid]["card_count"] == 2
    assert cats[DEFAULT_CATEGORY_ID]["card_count"] == 0

    client.delete(f"{categories_url}/{cid}")
    cats = {c["id"]: c for c in client.get(categories_url).json()}
    assert cats[DEFAULT_CATEGORY_ID]["card_count"] == 2


def test_delete_default_category_rejected(client, categories_url):
    r = client.delete(f"{categories_url}/{DEFAULT_CATEGORY_ID}")
    assert r.status_code == 400


def test_delete_missing_category_404(client, categories_url):
    assert client.delete(f"{categories_url}/9999").status_code == 404
