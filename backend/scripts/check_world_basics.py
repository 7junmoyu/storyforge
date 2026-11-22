"""Create temporary world, character, and novel, then delete them."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
world = client.post("/api/worlds", json={"name": "关联验收世界", "summary": "全局原文"}).json()
character = client.post("/api/characters", json={"name": "关联验收角色", "summary": "全局角色"}).json()
novel = client.post("/api/novels", json={"title": "关联验收小说", "world_ids": [world["id"]]}).json()

try:
    linked = client.post(
        f"/api/characters/{character['id']}/worlds",
        json={"world_id": world["id"], "note": "只在这本小说里认识", "scope": "novel", "source": "手动", "novel_id": novel["id"]},
    ).json()
    assert linked["scope"] == "novel" and linked["novel_title"] == "关联验收小说", linked

    saved = client.put(
        f"/api/worlds/{world['id']}/novels/{novel['id']}/setting",
        json={"supplement": "这本小说里的港口更冷"},
    ).json()
    assert saved["supplement"] == "这本小说里的港口更冷"
    again = client.get(f"/api/worlds/{world['id']}/novels/{novel['id']}/setting").json()
    assert again["supplement"] == "这本小说里的港口更冷"

    relations = client.get(f"/api/worlds/{world['id']}/relations").json()
    assert relations["summary"] == "全局原文"
    assert relations["characters"][0]["source"] == "手动"
    print("world character basics ok")
finally:
    client.delete(f"/api/characters/{character['id']}/worlds/{world['id']}")
    client.delete(f"/api/novels/{novel['id']}")
    client.delete(f"/api/worlds/{world['id']}")
    client.delete(f"/api/characters/{character['id']}")
