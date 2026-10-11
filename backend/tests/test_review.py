"""T5 — random review + review counter tests."""
from app.database import DEFAULT_CATEGORY_ID


def test_random_returns_none_when_empty(client):
    r = client.get("/api/review/random")
    assert r.status_code == 200
    assert r.json() is None


def test_random_returns_a_card(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.get("/api/review/random")
    assert r.status_code == 200
    assert r.json()["id"] == card_id


def test_random_filtered_by_category(client, cards_url, categories_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    client.post(cards_url, json={"question": "other", "answer": "A"})
    target = client.post(
        cards_url, json={"question": "redis q", "answer": "A", "category_id": cid}
    ).json()["id"]

    for _ in range(5):
        r = client.get("/api/review/random", params={"category_id": cid})
        assert r.json()["id"] == target


def test_random_empty_category_returns_none(client, cards_url, categories_url):
    cid = client.post(categories_url, json={"name": "Empty"}).json()["id"]
    client.post(cards_url, json={"question": "Q", "answer": "A"})
    r = client.get("/api/review/random", params={"category_id": cid})
    assert r.status_code == 200
    assert r.json() is None


def test_random_unknown_category_404(client):
    r = client.get("/api/review/random", params={"category_id": 9999})
    assert r.status_code == 404


def test_review_increments_counter(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]

    r = client.post(f"{cards_url}/{card_id}/reviewed")
    assert r.status_code == 200
    assert r.json()["review_count"] == 1

    r = client.post(f"{cards_url}/{card_id}/reviewed")
    assert r.json()["review_count"] == 2


def test_review_missing_card_404(client, cards_url):
    assert client.post(f"{cards_url}/9999/reviewed").status_code == 404


def test_review_counts_survive_category_deletion(client, cards_url, categories_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    card_id = client.post(
        cards_url, json={"question": "Q", "answer": "A", "category_id": cid}
    ).json()["id"]
    client.post(f"{cards_url}/{card_id}/reviewed")

    client.delete(f"{categories_url}/{cid}")
    card = client.get(f"{cards_url}/{card_id}").json()
    assert card["category_id"] == DEFAULT_CATEGORY_ID
    assert card["review_count"] == 1
