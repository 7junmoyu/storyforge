"""Exercise outline, foreshadow, and the imported PostgreSQL data."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def main() -> None:
    novels = client.get("/api/novels")
    assert novels.status_code == 200, novels.text
    rows = novels.json()
    assert rows, "导入后的小说不见了"
    print("novels", [(row["title"], row["chapter_count"]) for row in rows])
    worlds = client.get("/api/worlds").json()
    print("worlds", [(row["name"], row["novel_count"]) for row in worlds])

    created = client.post("/api/novels", json={"title": "大纲验收", "summary": "临时", "genre": "", "status": "draft", "target_words": 0, "world_id": worlds[0]["id"]})
    assert created.status_code == 201, created.text
    novel_id = created.json()["id"]
    world_before = next(row["novel_count"] for row in client.get("/api/worlds").json() if row["id"] == worlds[0]["id"])

    root = client.post(f"/api/novels/{novel_id}/outline", json={"title": "开端", "content": "城门关上。"})
    assert root.status_code == 201, root.text
    child = client.post(f"/api/novels/{novel_id}/outline", json={"title": "误认", "parent_id": root.json()["id"], "content": "认错了人。"})
    assert child.status_code == 201, child.text
    sibling = client.post(f"/api/novels/{novel_id}/outline", json={"title": "收束", "content": "选择公开。"})
    assert sibling.status_code == 201, sibling.text
    moved = client.post(f"/api/outline-nodes/{sibling.json()['id']}/move", json={"direction": "up"})
    assert moved.status_code == 200, moved.text
    listed = client.get(f"/api/novels/{novel_id}/outline").json()
    assert len(listed) == 3
    chapter = client.post(f"/api/outline-nodes/{root.json()['id']}/to-chapter")
    assert chapter.status_code == 201, chapter.text
    again = client.post(f"/api/outline-nodes/{root.json()['id']}/to-chapter")
    assert again.status_code == 409
    draft = client.post(f"/api/novels/{novel_id}/outline/draft", json={"instruction": "雨夜"})
    assert draft.status_code == 200 and draft.json()["nodes"]
    assert len(client.get(f"/api/novels/{novel_id}/outline").json()) == 3

    planted = client.post(f"/api/novels/{novel_id}/foreshadows", json={
        "name": "未说完的名字",
        "content": "有人听见了。",
        "kind": "人物",
        "importance": "high",
        "status": "planted",
        "outline_node_id": child.json()["id"],
        "plant_chapter_id": chapter.json()["chapter_id"],
    })
    assert planted.status_code == 201, planted.text
    filtered = client.get(f"/api/novels/{novel_id}/foreshadows", params={"status": "planted", "importance": "high"})
    assert len(filtered.json()) == 1
    inbox = client.get("/api/inbox/foreshadows")
    assert any(item["id"] == planted.json()["id"] for item in inbox.json())
    suggestion = client.post(f"/api/novels/{novel_id}/foreshadows/draft", json={"instruction": ""})
    assert suggestion.status_code == 200
    assert len(client.get(f"/api/novels/{novel_id}/foreshadows").json()) == 1

    other = client.post("/api/novels", json={"title": "另一本", "summary": "", "genre": "", "status": "draft", "target_words": 0, "world_id": None}).json()
    assert client.get(f"/api/novels/{other['id']}/outline").json() == []
    assert client.get(f"/api/novels/{other['id']}/foreshadows").json() == []

    deleted = client.delete(f"/api/novels/{novel_id}")
    assert deleted.status_code == 204
    client.delete(f"/api/novels/{other['id']}")
    world_after = next(row["novel_count"] for row in client.get("/api/worlds").json() if row["id"] == worlds[0]["id"])
    assert world_after == world_before - 1
    assert client.get("/api/novels").json()
    print("ok")


if __name__ == "__main__":
    main()
