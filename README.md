# StoryForge

Demo Sprint 1：工作台、小说、共享世界、章节编辑、自动保存、版本恢复，以及需要确认后才写入正文的 AI 建议。

## 启动

1. 启动 Docker Desktop。
2. 在项目根目录启动数据库：

```powershell
docker compose up -d
```

3. 后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload
```

4. 前端，另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 。

没有配置 `AI_API_KEY` 时，写作建议使用本地示例文本，确认流程相同。要接模型，在项目根目录创建 `.env`，填写兼容 OpenAI 的地址、密钥和模型名。

数据库使用本机 Docker 里的 PostgreSQL 16。先执行 `docker compose up -d`，再在 `backend` 里执行 `alembic upgrade head`。原先的 SQLite 文件留在 `backend/storyforge.db`，迁入 PostgreSQL 前会复制到 `backend/backups/`。需要重放这份数据时，在项目根目录执行：

```powershell
.\backend\.venv\Scripts\python backend\scripts\migrate_sqlite_to_postgres.py
```
