"""Temporary world records, templates, and an image upload. Rows are deleted."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
png = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
world = client.post("/api/worlds", json={"name": "目录验收世界", "summary": ""}).json()
character = client.post("/api/characters", json={"name": "目录验收角色", "summary": ""}).json()
try:
    created = client.post(
        f"/api/worlds/{world['id']}/records",
        json={"kind": "place", "name": "旧码头", "summary": "涨潮时不能靠岸", "time_label": ""},
    ).json()
    listed = client.get(f"/api/worlds/{world['id']}/records?kind=place").json()
    assert listed[0]["name"] == "旧码头"
    assert client.post(f"/api/chapters/{created['id']}/move", json={"direction": "up"}).status_code == 404

    template = client.post("/api/templates", json={"name": "验收模板", "fields": ["身份", "年龄"]}).json()
    refused = client.post(f"/api/characters/{character['id']}/apply-template", json={"template_id": template["id"], "confirm": False})
    assert refused.status_code == 400
    applied = client.post(
        f"/api/characters/{character['id']}/apply-template",
        json={"template_id": template["id"], "confirm": True},
    ).json()
    assert applied["attributes"]["身份"] == ""
    client.patch(
        f"/api/characters/{character['id']}",
        json={"name": "目录验收角色", "summary": "", "attributes": {"身份": "领航员", "年龄": ""}},
    )
    again = client.post(
        f"/api/characters/{character['id']}/apply-template",
        json={"template_id": template["id"], "confirm": True},
    ).json()
    assert again["attributes"]["身份"] == "领航员"

    uploaded = client.post(
        "/api/assets",
        data={"owner_kind": "character", "owner_id": character["id"], "note": "参考"},
        files={"file": ("dot.png", png, "image/png")},
    ).json()
    assert uploaded["url"].startswith("/uploads/")
    assert client.get(uploaded["url"]).status_code == 200
    client.delete(f"/api/assets/{uploaded['id']}")
    print("catalog ok")
finally:
    client.delete(f"/api/worlds/{world['id']}")
    client.delete(f"/api/characters/{character['id']}")
    for row in client.get("/api/templates").json():
        if row["name"] == "验收模板":
            client.delete(f"/api/templates/{row['id']}")
