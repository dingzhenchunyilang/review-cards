# 知识卡片复习工具

本地单机运行的知识卡片背诵 / 自测工具。每张卡片由「题目 + 答案」组成，归属一个分类。
本期范围：卡片管理、分类管理、按分类浏览、关键字搜索、随机复习。

界面视觉与交互沿用原型 `知识卡片原型.html`（双面 3D 翻卡、侧边导航、深浅色主题、响应式）。

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2.x · SQLite |
| 前端 | React 18 · Vite 5 · TypeScript |
| 数据 | 单个 SQLite 文件 `data/flashcards.db`（直接复制即备份） |

---

## 目录结构

```
review-cards/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口、CORS、路由挂载
│   │   ├── database.py        # engine / session / init_db
│   │   ├── models.py          # categories、cards 表
│   │   ├── schemas.py         # Pydantic 请求/响应模型
│   │   ├── routers/           # categories.py / cards.py / review.py
│   │   └── services/          # 业务逻辑（categories.py / cards.py）
│   ├── tests/                 # pytest 测试
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   └── src/
│       ├── api/               # client.ts / types.ts
│       ├── components/        # Toast / Modal / Markdown
│       ├── pages/             # ReviewPage / CardsPage / CategoriesPage / CardForm
│       ├── App.tsx            # 外壳与导航
│       ├── utils.ts           # Markdown 渲染、分类色相
│       └── styles.css         # 原型样式
├── data/                      # SQLite 数据文件（运行时生成）
└── README.md
```

---

## 启动步骤

### 1. 后端

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 启动（默认 8000）
uvicorn app.main:app --reload
```

首次启动会自动建表并创建默认分类「未分类」（固定 id = 1）。

- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

> **如果 8000 端口已被占用**，换一个端口，例如 `uvicorn app.main:app --reload --port 8123`，
> 然后按下面第 3 步把前端指过去。

> **顺带一提**：如果 `frontend/dist/` 已经构建过，后端启动时会把前端也一起托管，
> 所以直接打开 <http://127.0.0.1:8000> 就能用，不必开 Vite。
> 开发时仍然建议用 5173（有热更新）；但要注意 dist 可能是旧的，
> 看到「页面没更新」先想想是不是这个原因。

### 2. 前端

```bash
cd frontend
npm install        # 首次
npm run dev
```

浏览器打开 <http://localhost:5173>。

### 3. 后端端口不是 8000 时

前端通过 Vite 代理访问 `/api`，默认指向 `127.0.0.1:8000`。若后端换端口，启动前端时指定即可：

```bash
# Windows PowerShell
$env:BACKEND_PORT=8123; npm run dev

# Git Bash / macOS / Linux
BACKEND_PORT=8123 npm run dev
```

### 4. 可选：导入示例卡片

```bash
cd backend
.venv\Scripts\python -m app.seed      # Windows
# python -m app.seed                  # macOS / Linux
```

会插入 Redis / MySQL / Java 并发 三个分类和 6 张示例卡片。脚本是幂等的，重复执行不会重复插入。

---

## 运行测试

```bash
cd backend
.venv\Scripts\python -m pytest        # Windows
# python -m pytest                    # macOS / Linux
```

测试使用内存数据库，不会碰到 `data/flashcards.db`。

---

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/categories` | 分类列表（含每个分类的卡片数） |
| POST | `/api/categories` | 新增分类 |
| PUT | `/api/categories/{id}` | 重命名分类 |
| DELETE | `/api/categories/{id}` | 删除分类（卡片转入未分类） |
| GET | `/api/cards?category_id=&keyword=&page=&page_size=` | 卡片列表（分页） |
| POST | `/api/cards` | 新增卡片 |
| GET | `/api/cards/{id}` | 卡片详情 |
| PUT | `/api/cards/{id}` | 编辑卡片（字段可部分更新） |
| DELETE | `/api/cards/{id}` | 删除卡片 |
| POST | `/api/cards/restore` | 撤销删除：按快照重新插入卡片，保留原 id 与复习次数 |
| GET | `/api/review/random?category_id=` | 随机返回一张卡片，无卡片返回 `null` |
| POST | `/api/cards/{id}/reviewed` | 复习计数 +1 |

---

## 业务规则

- 启动时若不存在「未分类」自动创建，**id 固定为 1**；该分类不允许重命名、不允许删除。
- 删除分类时，其下卡片自动转入「未分类」，**卡片不丢失**。
- 题目与答案去除首尾空白后不能为空（返回 422）。
- 分类名唯一，重名返回 400。
- 卡片 `category_id` 指向不存在的分类返回 404。
- 复习随机抽取时，无可用卡片返回 `null`（HTTP 200），不报错。
- 关键字搜索匹配**题目**，SQLite `LIKE` 对 ASCII 大小写不敏感。
- **删除卡片是一击即删**（无二次确认），底部弹出提示条并提供「撤销」。
  撤销会原样还原卡片，保留原 id 和复习次数（靠 `POST /api/cards/restore`）。
- 删除分类**有二次确认**（因为会影响其下卡片），确认后卡片转入「未分类」，不可撤销。

---

## 快捷键（复习页）

| 按键 | 作用 |
| --- | --- |
| `空格` | 翻面 / 显示答案 |
| `→` 或 `Enter` | 下一张 |
| `E` | 编辑当前卡片 |

卡片编辑弹窗内 `Ctrl/Cmd + Enter` 保存。

---

## 备份数据

直接复制整个 `data/` 目录即可。恢复时覆盖回去再重启后端。

---

## 部署到服务器

见 [DEPLOY.md](./DEPLOY.md)。要点：

- 生产环境下 `backend/app/main.py` 会**直接托管 `frontend/dist`**，所以一个进程一个端口就够了
  （同源，不需要 CORS、不需要反代规则）。`frontend/dist` 不存在时自动跳过，本地开发行为不变。
- 推荐 `docker compose up -d --build`，Caddy 自动处理 HTTPS。
- 公网暴露前**务必**在 `.env` 里设置 `APP_USER` / `APP_PASSWORD` —— 不设就是谁都能访问。
  这是全站唯一一道锁（项目本身没有用户体系）。

---

## 后续迭代（未实现）

八股文批量导入 · 自动分类 · 模拟面试 · 基于遗忘曲线的间隔复习。
