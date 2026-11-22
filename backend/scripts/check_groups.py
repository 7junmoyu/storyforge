"""Create a temporary group, move one novel in, then put it back."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
novels = client.get("/api/novels?include_archived=true").json()
novel = novels[0]
previous = novel.get("group_id")
group = client.post("/api/novels/groups", json={"name": "界面验收"}).json()
try:
    moved = client.patch(f"/api/novels/{novel['id']}", json={"group_id": group["id"]}).json()
    assert moved["group_id"] == group["id"] and moved["grouped_at"]
    print("group assign ok")
finally:
    client.patch(f"/api/novels/{novel['id']}", json={"group_id": previous})
    client.delete(f"/api/novels/groups/{group['id']}")
    restored = client.get(f"/api/novels/{novel['id']}").json()
    assert restored["group_id"] == previous
    print("group restored")
