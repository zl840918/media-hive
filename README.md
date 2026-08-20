# Media-Hive 网盘影视资源索引引擎

类影巢(HDHive)的网盘影视资源站**核心引擎**：TMDB 元数据 + 网盘资源管理 + 开放解锁 API。

> ⚠️ 本仓库只包含**代码框架**，不含任何影视资源数据与分享链接。数据由部署者自行录入维护。

## 功能

- 🔍 **TMDB 集成**：搜索/详情自动录入（需 TMDB API Key）
- 📦 **网盘资源管理**：115 / 123 / 夸克 / 阿里云盘 / 百度网盘 分享链接 + 提取码 + 清晰度/格式/大小
- 🔑 **API Key 鉴权**：三级权限（guest / member / admin）+ 每日配额 + 过期时间 + 用量日志
- 🎬 **分级解锁**：guest 只能解锁低清晰度资源，member/admin 全量
- 🧹 **资源状态管理**：失效链接一键标记 expired
- 🐳 **Docker 一键部署**

## 快速开始

### Docker（推荐）

```bash
# 首次：在 .env 里配好 TMDB Key 和管理员 Key
echo "MH_TMDB_API_KEY=你的key" >> .env
echo "MH_BOOTSTRAP_ADMIN_KEY=你自己定的管理员Key" >> .env
docker compose up -d --build
```

服务地址 `http://localhost:8890`，接口文档 `http://localhost:8890/docs`。

> 管理员 Key 也可不设：留空则首次启动自动生成并打印在容器日志里。

### 本地开发

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
MH_BOOTSTRAP_ADMIN_KEY=dev-key uvicorn app.main:app --port 8890
pytest   # 跑测试
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MH_DATABASE_URL` | `sqlite:///./media_hive.db` | 数据库地址（Docker 里指向 /data） |
| `MH_TMDB_API_KEY` | 空 | TMDB API Key（[申请](https://www.themoviedb.org/settings/api)） |
| `MH_BOOTSTRAP_ADMIN_KEY` | 空 | 首次启动的管理员 Key，留空则自动生成 |
| `MH_GUEST_MAX_QUALITY` | `720P` | guest 可解锁的最高清晰度，空串=不限 |
| `MH_DEFAULT_DAILY_QUOTA` | `100` | 新 Key 默认每日配额 |

## API 概览

所有开放接口需请求头 `X-API-Key`。

### 开放 API `/api/open`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/ping` | 验证 Key 有效性 |
| GET | `/quota` | 查询配额与剩余 |
| GET | `/tmdb/search/{movie\|tv}?query=` | TMDB 搜索 |
| GET | `/tmdb/{movie\|tv}/{tmdb_id}` | TMDB 详情 |
| GET | `/resources/{movie\|tv}/{tmdb_id}` | 资源列表（**隐藏分享链接**） |
| POST | `/resources/{movie\|tv}/{tmdb_id}/unlock` | 解锁，返回完整分享链接 |

### 管理 API `/api/admin`（需 admin Key）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/movies/tmdb/{movie\|tv}/{tmdb_id}` | 从 TMDB 自动创建条目 |
| POST | `/movies/{id}/resources` | 录入网盘资源 |
| PATCH/DELETE | `/resources/{id}` | 更新/删除资源（标记失效） |
| POST/GET | `/keys` | 创建/查看 API Key |
| PATCH | `/keys/{id}` | 改等级/配额/过期 |
| GET | `/usage` | 解锁用量日志 |

### 快速试用

```bash
# 1. 创建影视条目（有 TMDB Key 时可直接 /api/admin/movies/tmdb/movie/{id}）
curl -X POST http://localhost:8890/api/admin/movies \
  -H "X-API-Key: 管理员Key" -H "Content-Type: application/json" \
  -d '{"tmdb_id":12345,"media_type":"movie","title":"Interstellar","year":2014}'

# 2. 录入资源
curl -X POST http://localhost:8890/api/admin/movies/1/resources \
  -H "X-API-Key: 管理员Key" -H "Content-Type: application/json" \
  -d '{"drive_type":"115","share_url":"https://115.com/s/xxx","access_code":"a1b2","quality":"4K"}'

# 3. 创建 guest Key 并解锁（guest 只能拿到 ≤720P 的链接）
curl -X POST http://localhost:8890/api/open/resources/movie/12345/unlock \
  -H "X-API-Key: 你的Key"
```

## 解锁与配额机制

- **guest**：可查资源列表（链接隐藏），解锁仅返回 ≤ `MH_GUEST_MAX_QUALITY` 的资源
- **member**：解锁全量资源
- **admin**：全量 + 管理接口
- 每个 Key 每日配额 `daily_quota` 次，跨天自动重置，超限返回 `429`

## 路线图

- [ ] 阶段一 ✅ 核心引擎（当前）：TMDB + 资源管理 + 解锁 API + Key 鉴权
- [ ] 阶段二：前端影视站（浏览/搜索/详情页）
- [ ] 阶段三：商业化（套餐 Key、订单、用量计费）
- [ ] 阶段四：自动化采集（Telegram/网盘链接抓取、去重、失效检测）
