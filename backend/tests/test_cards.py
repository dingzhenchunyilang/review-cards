"""T4 — card CRUD tests."""
from app.database import DEFAULT_CATEGORY_ID


def make_category(client, categories_url, name="Redis"):
    return client.post(categories_url, json={"name": name}).json()["id"]


def test_create_card_default_category(client, cards_url):
    r = client.post(cards_url, json={"question": "Q1", "answer": "A1"})
    assert r.status_code == 201
    body = r.json()
    assert body["category_id"] == DEFAULT_CATEGORY_ID
    assert body["review_count"] == 0


def test_create_card_with_category(client, cards_url, categories_url):
    cid = make_category(client, categories_url)
    r = client.post(cards_url, json={"question": "Q", "answer": "A", "category_id": cid})
    assert r.status_code == 201
    assert r.json()["category_id"] == cid


def test_create_card_trims_text(client, cards_url):
    r = client.post(cards_url, json={"question": "  Q  ", "answer": "  A  "})
    assert r.json()["question"] == "Q"
    assert r.json()["answer"] == "A"


def test_create_card_missing_category_rejected(client, cards_url):
    r = client.post(cards_url, json={"question": "Q", "answer": "A", "category_id": 9999})
    assert r.status_code == 404


def test_create_card_empty_question_rejected(client, cards_url):
    r = client.post(cards_url, json={"question": "   ", "answer": "A"})
    assert r.status_code == 422


def test_create_card_empty_answer_rejected(client, cards_url):
    r = client.post(cards_url, json={"question": "Q", "answer": "   "})
    assert r.status_code == 422


def test_get_card_detail(client, cards_url):
    cid = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.get(f"{cards_url}/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid


def test_get_missing_card_404(client, cards_url):
    assert client.get(f"{cards_url}/9999").status_code == 404


def test_update_card(client, cards_url, categories_url):
    cid = make_category(client, categories_url)
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.put(
        f"{cards_url}/{card_id}",
        json={"question": "Q2", "answer": "A2", "category_id": cid},
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["question"], body["answer"], body["category_id"]) == ("Q2", "A2", cid)


def test_update_card_partial(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.put(f"{cards_url}/{card_id}", json={"question": "Q2"})
    assert r.status_code == 200
    assert r.json()["answer"] == "A"


def test_update_card_empty_answer_rejected(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.put(f"{cards_url}/{card_id}", json={"answer": "  "})
    assert r.status_code == 422


def test_update_card_missing_category_rejected(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    r = client.put(f"{cards_url}/{card_id}", json={"category_id": 9999})
    assert r.status_code == 404


def test_delete_card(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    assert client.delete(f"{cards_url}/{card_id}").status_code == 204
    assert client.get(f"{cards_url}/{card_id}").status_code == 404


def test_delete_missing_card_404(client, cards_url):
    assert client.delete(f"{cards_url}/9999").status_code == 404


def test_restore_recreates_deleted_card(client, cards_url):
    card = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()
    client.delete(f"{cards_url}/{card['id']}")

    r = client.post(
        f"{cards_url}/restore",
        json={
            "id": card["id"],
            "question": card["question"],
            "answer": card["answer"],
            "category_id": card["category_id"],
            "review_count": card["review_count"],
        },
    )
    assert r.status_code == 201
    restored = r.json()
    assert restored["id"] == card["id"]  # original id (and list position) preserved
    assert restored["question"] == "Q"


def test_restore_preserves_review_count(client, cards_url):
    card_id = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()["id"]
    client.post(f"{cards_url}/{card_id}/reviewed")
    client.post(f"{cards_url}/{card_id}/reviewed")
    client.delete(f"{cards_url}/{card_id}")

    r = client.post(
        f"{cards_url}/restore",
        json={"id": card_id, "question": "Q", "answer": "A", "review_count": 2},
    )
    assert r.status_code == 201
    assert r.json()["review_count"] == 2


def test_restore_without_id_still_works(client, cards_url):
    card = client.post(cards_url, json={"question": "Q", "answer": "A"}).json()
    client.delete(f"{cards_url}/{card['id']}")

    r = client.post(f"{cards_url}/restore", json={"question": "Q", "answer": "A"})
    assert r.status_code == 201
    # SQLite may reuse a freed rowid, so only assert the card is readable again.
    assert client.get(f"{cards_url}/{r.json()['id']}").status_code == 200


def test_restore_falls_back_when_category_gone(client, cards_url, categories_url):
    cid = client.post(categories_url, json={"name": "Redis"}).json()["id"]
    card = client.post(
        cards_url, json={"question": "Q", "answer": "A", "category_id": cid}
    ).json()
    client.delete(f"{cards_url}/{card['id']}")
    client.delete(f"{categories_url}/{cid}")

    r = client.post(
        f"{cards_url}/restore",
        json={"question": "Q", "answer": "A", "category_id": cid},
    )
    assert r.status_code == 201
    assert r.json()["category_id"] == DEFAULT_CATEGORY_ID


def test_restore_empty_text_rejected(client, cards_url):
    r = client.post(f"{cards_url}/restore", json={"question": "  ", "answer": "A"})
    assert r.status_code == 422


def test_list_cards_filter_by_category(client, cards_url, categories_url):
    cid = make_category(client, categories_url)
    client.post(cards_url, json={"question": "Q1", "answer": "A1"})
    client.post(cards_url, json={"question": "Q2", "answer": "A2", "category_id": cid})

    data = client.get(cards_url, params={"category_id": cid}).json()
    assert data["total"] == 1
    assert data["items"][0]["question"] == "Q2"


def test_list_cards_filter_by_unknown_category_404(client, cards_url):
    assert client.get(cards_url, params={"category_id": 9999}).status_code == 404


def test_list_cards_search_keyword(client, cards_url):
    client.post(cards_url, json={"question": "Redis 持久化", "answer": "A"})
    client.post(cards_url, json={"question": "MySQL 索引", "answer": "A"})

    # SQLite LIKE is case-insensitive for ASCII, so lowercase matches.
    assert client.get(cards_url, params={"keyword": "redis"}).json()["total"] == 1
    assert client.get(cards_url, params={"keyword": "Redis"}).json()["total"] == 1
    assert client.get(cards_url, params={"keyword": "持久化"}).json()["total"] == 1
    assert client.get(cards_url, params={"keyword": "不存在"}).json()["total"] == 0


def test_list_cards_search_matches_question_not_answer(client, cards_url):
    client.post(cards_url, json={"question": "Q", "answer": "答案里有索引二字"})
    assert client.get(cards_url, params={"keyword": "索引"}).json()["total"] == 0


def test_list_cards_pagination(client, cards_url):
    for i in range(5):
        client.post(cards_url, json={"question": f"Q{i}", "answer": "A"})

    data = client.get(cards_url, params={"page": 1, "page_size": 2}).json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1 and data["page_size"] == 2

    page3 = client.get(cards_url, params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 1
