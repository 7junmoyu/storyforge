import httpx

base = "http://127.0.0.1:8000/api"
with httpx.Client(base_url=base, timeout=20) as client:
    novels = client.get("/novels").json()
    worlds = client.get("/worlds").json()
    print("novels", len(novels), "worlds", len(worlds))
    if worlds:
        relations = client.get(f"/worlds/{worlds[0]['id']}/relations")
        print("relations", relations.status_code, list(relations.json()))
    if novels:
        novel = novels[0]
        detail = client.get(f"/novels/{novel['id']}").json()
        world_ids = [row["id"] for row in detail["worlds"]]
        kept = client.patch(f"/novels/{novel['id']}", json={"world_ids": world_ids})
        print("keep worlds", kept.status_code, len(kept.json()["worlds"]))
        chapter_id = detail["chapters"][0]["id"]
        created = client.post(f"/chapters/{chapter_id}/marks", json={"quote": "layout-check", "start": 1, "end": 2})
        print("mark", created.status_code)
        mark_id = created.json()["id"]
        listed = client.get(f"/chapters/{chapter_id}/marks").json()
        assert any(row["id"] == mark_id for row in listed)
        deleted = client.delete(f"/marks/{mark_id}")
        print("mark delete", deleted.status_code)
    if worlds:
        person = client.post("/characters", json={"name": "布局验收角色", "summary": ""})
        print("character", person.status_code)
        character_id = person.json()["id"]
        linked = client.post(f"/characters/{character_id}/worlds", json={"world_id": worlds[0]["id"], "note": "直接"})
        print("link", linked.status_code, linked.json()["note"])
        unlinked = client.delete(f"/characters/{character_id}/worlds/{worlds[0]['id']}")
        removed = client.delete(f"/characters/{character_id}")
        print("unlink", unlinked.status_code, "delete", removed.status_code)
print("ok")
