# Supabase 开发演示接入

架构：本机 OpenD → `sync_supabase.py` → Supabase → Streamlit Community Cloud。
数据库存数据，不负责运行 OpenD。本机关闭后，网页保留上次同步数据。

## 1. 建表（一次）

Supabase 控制台 → SQL Editor → New query，粘贴 `supabase/schema.sql` 全文并 Run。
当前仅有项目 API Key，程序不能通过 Data API 执行建表 SQL。
该脚本只创建 `market_data_snapshots`，不开放匿名读取，不包含真实密钥。

## 2. 本机连接配置

项目根目录 `.env`（Windows 下 `.ENV` 也可）：

```dotenv
DATA_BACKEND=local
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SECRET_KEY=YOUR_SERVER_SIDE_SECRET_KEY
FUTU_OPEND_HOST=127.0.0.1
FUTU_OPEND_PORT=11111
```

保留已有的 LLM 配置。不要把 `.env`、`.ENV`、Secrets 提交到 Git。

在 F:\code 的 PowerShell 运行：

```powershell
# 先检查表及连接（不打印密钥）
.\.venv\Scripts\python.exe sync_supabase.py --check

# 第一次：上传已有 CCASS、最新行情及最近30个交易日券商历史
.\.venv\Scripts\python.exe sync_supabase.py --once

# 持续采集：终端保持运行，每60秒同步；Ctrl+C 停止
.\.venv\Scripts\python.exe sync_supabase.py --interval 60 --update-ccass
```

OpenD 必须在本机启动并登录。`--update-ccass` 复用已有增量抓取逻辑，
每15分钟最多检查一次；沿用校验及串行间隔，不覆盖已有 CSV。
不启用该参数时，只上传本地已存在的 CCASS 快照。

可选：`--ccass-only --once` 不连接 OpenD；`--history-days 0` 不补历史券商数据。
已有历史记录会跳过；新交易日会补前一日的历史接口记录。

## 3. Community Cloud 配置

提交并推送代码后，打开 App settings → Secrets，追加：

```toml
DATA_BACKEND = "supabase"
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SECRET_KEY = "YOUR_SERVER_SIDE_SECRET_KEY"
```

保留原有 LLM Secrets。也可参考 `supabase/secrets.example.toml`。
重新部署后，主看板、历史券商查询、逐笔榜单、CCASS 分析均从云端读取。
云端不自动抓取，不连接 127.0.0.1:11111；刷新按钮只是重读云端快照。

这是开发演示的服务端配置：Secret key 权限较高，只能放在本机环境文件或
Streamlit 服务端 Secrets，不得放入网页 JavaScript、截图、日志或 Git。
代码层的 read_only 限制不等于数据库只读凭据。面向更多人使用前应建立专用
只读认证及 RLS；程序预留 SUPABASE_READ_KEY 和 SUPABASE_READ_ACCESS_TOKEN，
但不能仅换成 publishable key 就读取本表（默认 RLS 不允许匿名读取）。

## 保存范围及时间

- 快照、分时、券商实时榜、最近1000笔样本：每个源数据日期覆盖更新，保留每日最后一次采集结果。
- 逐笔不是全天历史流水；网页仍只显示最近样本排名。
- 券商历史：按实时基准日、港股交易日历和 days_before 换算交易日期保存，历史记录优先于当时的盘中累计榜；原始 data_time_str 是更新时间，不用于推断历史所属日期。
- CCASS：按快照日期保存完整原始字段，仅上传缺失日期。
- fetched_at 是采集时间，行情/券商原始字段内的时间是数据更新时间，历史交易日期另存为 record_date，并保留基准日与偏移量元数据。
- 不伪造日期、不把采集时间当作交易日，不用其他日期静默替代未同步的数据。
- 行情读缓存最多30秒，CCASS 批量快照缓存最多5分钟（目录仍按30秒更新，新日期不在批量缓存时单独读取）。最近同步超过3分钟时提示旧数据；非交易时段旧报价是正常现象。
- 免费额度需自行观察；分时和逐笔每日快照会累积，当前不自动删除历史数据。

如遇 HTTP 404：确认已执行 SQL、表在 public schema 且 Data API 已启用。
401/403：核对项目 URL/密钥及权限；不要在聊天或错误报告里粘贴密钥。
本机和 Community Cloud 都须能访问 Supabase 的 HTTPS 地址。
