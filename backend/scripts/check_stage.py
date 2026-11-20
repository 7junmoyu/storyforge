"""Check stage 1 character links and stage 2 volume export without touching the user's novel."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def main() -> None:
    created: list[str] = []
    characters: list[str] = []
    try:
        _run(created, characters)
    finally:
        for novel_id in created:
            client.delete(f"/api/novels/{novel_id}")
        for character_id in characters:
            client.delete(f"/api/characters/{character_id}")


def _run(created: list[str], characters: list[str]) -> None:
    character = client.post("/api/characters", json={"name": "验收角色", "summary": "全局档案"})
    assert character.status_code == 201, character.text
    character_id = character.json()["id"]
    characters.append(character_id)
    novel = client.post(
        "/api/novels",
        json={
            "title": "阶段验收",
            "summary": "",
            "genre": "",
            "status": "draft",
            "target_words": 0,
            "tags": "雨,港",
            "world_id": None,
            "character_ids": [character_id],
        },
    )
    assert novel.status_code == 201, novel.text
    novel_id = novel.json()["id"]
    created.append(novel_id)
    assert novel.json()["characters"][0]["name"] == "验收角色"
    other = client.post(
        "/api/novels",
        json={"title": "另一本关联", "summary": "", "genre": "", "status": "draft", "target_words": 0, "character_ids": [character_id]},
    )
    assert other.status_code == 201, other.text
    created.append(other.json()["id"])
    blocked = client.delete(f"/api/characters/{character_id}")
    assert blocked.status_code == 409, blocked.text
    cleared = client.patch(f"/api/novels/{other.json()['id']}", json={"character_ids": []})
    assert cleared.status_code == 200 and cleared.json()["characters"] == []
    volume = client.post(f"/api/novels/{novel_id}/volumes", json={"title": "第一卷"})
    assert volume.status_code == 201, volume.text
    chapter_id = novel.json()["chapters"][0]["id"]
    assigned = client.patch(f"/api/chapters/{chapter_id}", json={"volume_id": volume.json()["id"], "content": "<p>城门在雨里关上了。</p>"})
    assert assigned.status_code == 200 and assigned.json()["volume_id"] == volume.json()["id"]
    exported = client.get(f"/api/novels/{novel_id}/export.txt")
    assert exported.status_code == 200 and "城门在雨里关上了" in exported.text
    docx = client.get(f"/api/novels/{novel_id}/export.docx")
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    pdf = client.get(f"/api/novels/{novel_id}/export.pdf")
    assert pdf.status_code in {200, 503}, pdf.text
    if pdf.status_code == 200:
        assert pdf.content.startswith(b"%PDF")
    else:
        print("pdf", pdf.json())
    copied = client.post(f"/api/novels/{novel_id}/duplicate")
    assert copied.status_code == 201 and copied.json()["title"].endswith("副本")
    created.append(copied.json()["id"])
    imported = client.post(
        "/api/novels/import",
        json={"title": "导入来的", "summary": "基础数据", "chapters": [{"title": "序", "content": "<p>一句。</p>"}]},
    )
    assert imported.status_code == 201 and imported.json()["chapter_count"] == 1
    created.append(imported.json()["id"])
    archived = client.patch(f"/api/novels/{novel_id}", json={"archived": True})
    assert archived.status_code == 200
    visible = client.get("/api/novels")
    assert all(row["id"] != novel_id for row in visible.json())
    hidden = client.get("/api/novels?include_archived=true")
    assert any(row["id"] == novel_id for row in hidden.json())
    print("ok")


if __name__ == "__main__":
    main()
