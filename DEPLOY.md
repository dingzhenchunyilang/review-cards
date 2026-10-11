# 部署到服务器

## 它是怎么跑的

这个应用原本是「Vite dev server + uvicorn」两个进程。现在 `backend/app/main.py` 会在启动时
检查 `frontend/dist/`，如果存在就**由 FastAPI 自己托管前端**：

```
浏览器 ──HTTPS──> Caddy ──> uvicorn (8000)
                              ├── /api/*  → FastAPI 路由
                              └── 其它路径 → frontend/dist（SPA，含前端路由回退）
```

好处：**同源**，所以不需要配 CORS、不需要 nginx 反代规则、一个进程一个端口。
`frontend/dist` 不存在时（本地开发 / 跑测试）自动跳过托管，行为和以前完全一样。

**数据**：只有一个文件 `data/flashcards.db`。**备份 = 复制它。**

---

## 方案 A：Docker Compose（推荐）

前提：服务器装了 Docker + Compose 插件，并且有公网 IP。

```bash
# 1) 拿到代码
git clone <你的仓库地址> /opt/flashcards && cd /opt/flashcards

# 2) 配置
cp .env.example .env
vi .env        # 填 APP_DOMAIN / APP_USER / APP_PASSWORD

# 3) 起
docker compose up -d --build
```

打开 `https://你的域名` 即可。Caddy 会自动申请证书（首次约需几十秒）。

`.env` 里三项：

| 变量 | 说明 |
|---|---|
| `APP_DOMAIN` | 你的域名，必须已解析到这台服务器，且 80/443 开放 |
| `APP_USER` | 登录用户名 |
| `APP_PASSWORD` | 登录密码，**建议长一点**（这是全站唯一的一道锁） |

> `APP_USER` 和 `APP_PASSWORD` 两个都填才会开启登录。**留空 = 谁都能访问。**

### 把你现在的卡片带过去

`data/` 在 `.dockerignore` 里，**不会打进镜像** —— 服务器起来是个空库，你本地的卡片
不会自动跟过去。想带就手动传一次：

```bash
# 本地项目根目录
mkdir -p data                       # 已经有就不用
scp data/flashcards.db 你的服务器:/opt/flashcards/data/flashcards.db

# 服务器
mkdir -p /opt/flashcards/data       # 必须存在，否则 scp 会失败
docker compose up -d --build
```

不想带旧数据也行，直接在服务器上灌一份示例数据：

```bash
docker compose exec app python -m app.seed
```

> `data/` 不存在时 Docker 会自动建一个 root 属主的空目录，应用能正常跑；
> 只是那样你自己 scp 就没地方放了，所以先建好。

### 为什么多了个登录

计划书里写的是「不做登录」——那是针对本地单机。公网可达之后不加锁，
任何人拿到链接就能看和改你的卡片。所以加了一层最简的 HTTP Basic Auth：
浏览器会弹原生登录框，没有额外页面，也不影响本地开发（不设环境变量就不启用）。

### 没有域名怎么办

Let's Encrypt 不给裸 IP 签证书。三选一：

1. **买个便宜域名**（最省心，几十块一年），解析到服务器 IP 即可。
2. **自签证书**：把 `deploy/Caddyfile` 里的 `# tls internal` 取消注释，
   然后把 `APP_DOMAIN` 填成服务器 IP。浏览器会提示证书不受信任，需要手动点继续。
3. **Cloudflare Tunnel / Tailscale**（推荐给「只有 IP」的情况）：
   不用开放任何端口，也不用证书，直接把这台机器接进私有网络。
   这时可以去掉 compose 里的 `caddy` 服务，只跑 `app`。

---

## 方案 B：不用 Docker（venv + systemd）

适合不想装 Docker 的服务器。

```bash
sudo apt update && sudo apt install -y python3-venv caddy
sudo useradd -r -s /usr/sbin/nologin flashcards

git clone <你的仓库地址> /opt/flashcards && cd /opt/flashcards

# 1) 构建前端（需要 Node；也可以在本机 build 好，只把 frontend/dist 传上来）
cd frontend && npm ci && npm run build && cd ..

# 2) 后端依赖
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..

# 3) 环境变量
cp .env.example .env && vi .env      # 至少填 APP_USER / APP_PASSWORD

# 4) 先手动试跑，确认能起来
cd backend && APP_USER=ethan APP_PASSWORD=xxx .venv/bin/uvicorn app.main:app --port 8000
# 浏览器开 http://服务器IP:8000 看看，Ctrl-C 退出

# 5) 交给 systemd
sudo cp deploy/flashcards.service /etc/systemd/system/
sudo chown -R flashcards:flashcards /opt/flashcards
sudo systemctl daemon-reload
sudo systemctl enable --now flashcards
sudo systemctl status flashcards
```

然后配 Caddy。

⚠️ **不要直接 `cp deploy/Caddyfile`**。那份是给 compose 用的，里面的 `{$APP_DOMAIN}`
是 Docker Compose 注入的环境变量；systemd 跑的 Caddy 没有这个变量，会解析成空值导致启动失败。
直接写一份独立的（把域名和反代地址都写死）：

```bash
sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
cards.example.com {
	encode zstd gzip
	header {
		X-Content-Type-Options nosniff
		X-Frame-Options DENY
		Referrer-Policy no-referrer
	}
	reverse_proxy 127.0.0.1:8000
}
EOF

sudo systemctl reload caddy     # 或 restart
```

两处和 compose 版不同：域名写死（不用 `{$APP_DOMAIN}`），反代目标写 `127.0.0.1:8000`
（不是容器名 `app:8000`）。没有域名想用自签证书，就在块里加一行 `tls internal`。

`deploy/flashcards.service` 里已经做了基本加固（`ProtectSystem` / `ProtectHome` /
`NoNewPrivileges`），并假定代码放在 `/opt/flashcards`。换目录要同步改
`WorkingDirectory`、`EnvironmentFile`、`ExecStart` 三处。

---

## 日常维护

### 备份

数据库就一个文件，但**别直接 `cp`** —— 如果正好撞上一次写操作，可能拿到损坏或过期的副本。
用 SQLite 自带的备份接口最稳（可以在服务运行中执行）：

```bash
# Docker
docker compose exec app python -c "
import sqlite3
src = sqlite3.connect('/app/data/flashcards.db')
dst = sqlite3.connect('/tmp/backup.db')
src.backup(dst)
"
docker compose cp app:/tmp/backup.db ./flashcards-$(date +%F).db

# systemd（用项目自带的 python，不必额外装 sqlite3 CLI）
/opt/flashcards/backend/.venv/bin/python -c "
import sqlite3
src = sqlite3.connect('/opt/flashcards/data/flashcards.db')
dst = sqlite3.connect('/tmp/backup.db')
src.backup(dst)
" && mv /tmp/backup.db ~/backup/flashcards-$(date +%F).db
```

恢复：把文件放回 `data/flashcards.db`（Docker 的话就是宿主机上的 `./data/`），然后重启服务。

### 更新代码

```bash
git pull
docker compose up -d --build        # Docker：会自动重新构建前端
sudo systemctl restart flashcards   # systemd：前端有改动要先 cd frontend && npm run build
```

### 可选加固

容器内进程目前以 root 运行（配合 bind mount 最省事，不会有权限踩坑）。
如果你想把权限收紧，在 `Dockerfile` 里加一个非 root 用户，并在 compose 里写
`user: "10001:10001"` —— 代价是必须先在宿主机执行 `sudo chown -R 10001:10001 ./data`，
否则应用会因写不了数据库而报错。

### 排错

```bash
docker compose logs -f app          # 应用日志
docker compose logs -f caddy        # 证书 / 反代问题看这里
curl -i http://127.0.0.1:8000/api/health   # 容器内健康检查（不鉴权）
```

- **打开是 502**：Caddy 连不上 app。先确认 `app` 容器是 running，再看它的日志。
- **登录框反复弹**：`APP_USER` / `APP_PASSWORD` 没设或设错了。注意 `.env` 改完要
  `docker compose up -d` 才会重新读取。
- **证书申请失败**：域名没解析到本机、或 80/443 没放开。Caddy 需要 80 端口做 ACME 校验。
- **卡片数据不见了**：检查 `./data` 是否真的挂进了容器（`docker compose exec app ls -l /app/data`）。
- **systemd 下起不来**：检查 `/opt/flashcards/.env` 的写法。`EnvironmentFile` 对含空格、
  `#`、引号的密码很敏感 —— 建议用长一点的纯字母数字密码，别加引号。
- **`npm audit` 报 esbuild / vite 漏洞**：那是 Vite **开发服务器**的问题（GHSA-67mh-4wv8-2f99，
  第三方网站可以向 dev server 发请求）。生产镜像只跑 `npm run build` 产出静态文件，
  不起 dev server，所以部署环境不受影响。修复要升到 vite 8（破坏性变更），不值得为此动。

---

## 本地开发不受影响

```bash
# 后端（不带 APP_USER/APP_PASSWORD → 无鉴权）
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8123

# 前端
cd frontend && BACKEND_PORT=8123 npm run dev
```

开发时前端由 Vite 托管、`/api` 走代理，`main.py` 的 SPA 托管分支虽然会注册，
但请求都先被 Vite 接走了，不会互相干扰。
