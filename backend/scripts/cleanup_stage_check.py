from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
titles = {"阶段验收", "另一本关联", "阶段验收 副本", "导入来的"}
novels = client.get("/api/novels", params={"include_archived": "true"}).json()
for novel in novels:
    if novel["title"] in titles:
        result = client.delete(f"/api/novels/{novel['id']}")
        print(novel["title"], result.status_code)
for character in client.get("/api/characters").json():
    if character["name"] == "验收角色":
        result = client.delete(f"/api/characters/{character['id']}")
        print(character["name"], result.status_code)
