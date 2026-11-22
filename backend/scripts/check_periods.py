import httpx

base = "http://127.0.0.1:8000/api"
with httpx.Client(base_url=base, timeout=20) as client:
    novel = client.get("/novels").json()[0]
    person = client.post("/characters", json={"name": "时期验收", "summary": "全局介绍"})
    assert person.status_code == 201, person.text
    character_id = person.json()["id"]
    try:
        linked = client.patch(f"/novels/{novel['id']}", json={"character_ids": [row["id"] for row in novel["characters"]] + [character_id]})
        assert linked.status_code == 200, linked.text
        period = client.post(f"/characters/{character_id}/periods", json={"name": "少年", "time_range": "出发前", "attributes": {"身份": "学徒"}})
        assert period.status_code == 201, period.text
        refused = client.post(f"/characters/{character_id}/versions/{novel['id']}/from-global", json={"confirm": False})
        assert refused.status_code == 400, refused.text
        created = client.post(f"/characters/{character_id}/versions/{novel['id']}/from-period", json={"confirm": True, "period_id": period.json()["id"]})
        assert created.status_code == 200, created.text
        assert created.json()["attributes"]["身份"] == "学徒"
        renamed = client.patch(f"/characters/{character_id}", json={"name": "时期验收改名", "summary": "新的全局介绍"})
        assert renamed.status_code == 200
        kept = client.get(f"/characters/{character_id}/versions").json()
        mine = next(row for row in kept if row["novel_id"] == novel["id"])
        assert mine["name"] == "时期验收", mine
        assert mine["summary"] != "新的全局介绍"
        other = client.post("/novels", json={"title": "时期验收另一本", "summary": "", "genre": "", "status": "draft", "target_words": 0, "character_ids": [character_id]})
        assert other.status_code == 201, other.text
        other_id = other.json()["id"]
        second = client.post(f"/characters/{character_id}/versions/{other_id}/from-global", json={"confirm": True})
        assert second.status_code == 200
        edited = client.put(
            f"/characters/{character_id}/versions/{novel['id']}",
            json={"name": "只改第一本", "summary": "第一本专属", "attributes": {"身份": "旅人"}, "period_id": period.json()["id"]},
        )
        assert edited.status_code == 200, edited.text
        again = client.get(f"/characters/{character_id}/versions").json()
        first = next(row for row in again if row["novel_id"] == novel["id"])
        second_row = next(row for row in again if row["novel_id"] == other_id)
        assert first["name"] == "只改第一本"
        assert second_row["name"] == "时期验收改名"
        print("period version isolation ok")
        client.delete(f"/novels/{other_id}")
    finally:
        client.patch(f"/novels/{novel['id']}", json={"character_ids": [row["id"] for row in novel["characters"]]})
        client.delete(f"/characters/{character_id}")
        print("cleaned", client.get("/characters").json())
