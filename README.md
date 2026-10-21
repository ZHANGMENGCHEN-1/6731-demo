# 06731 CCASS 真实持仓 Demo

在项目目录的 PowerShell 中运行（如已有虚拟环境，先激活）：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python fetch_ccass.py 06731 2026-09-29 2026-10-13
python -m streamlit run app.py
```

无需调用 `streamlit.exe`。页面仅从本地 CSV 读取，不发出网络请求。

## 每日增量更新

外部定时器每天执行一次，无需启动 Streamlit：

```powershell
F:\code\.venv\Scripts\python.exe F:\code\fetch_latest.py
```

Windows 任务计划程序中，程序填 `F:\code\.venv\Scripts\python.exe`，参数填 `F:\code\fetch_latest.py`，起始目录填 `F:\code`。此项目未自动创建系统定时任务。

入口读取 HKEX 实际查询表单中的默认最新持仓日期，从本地最新日期的下一日依次查询；无本地真实数据时从上市日开始。复用 `fetch_ccass.fetch_day` 的表单、解析和验证逻辑，串行执行，每日查询后等待 2.5 秒。周末/未发布快照正常跳过；已是最新时正常退出。不会修补本地最新日期之前的历史缺口，该需求仍可使用原手动抓取命令。

CSV 完整写入临时文件后原子发布，不覆盖已有文件；网站或网络异常停止并返回非零退出码，保留之前成功保存的数据。日志同时输出终端和 `logs/fetch_latest.log`，时间采用 UTC+8，日志自动轮转。看板下次刷新或交互时自动扫描新 CSV；已经打开且没有交互的网页不会主动轮询。定时器与看板必须使用同一份持久化 data 目录，远程部署需另行保证数据同步。

## AI 分析助手框架

默认打开「06731 持仓监控看板」，AI 分析助手保留为侧边栏第二入口。
看板包含最新与上市以来的变化、Top 5 / Top 10、近期持续趋势、单机构历史曲线、自定义日期对比及查册校验占位区域。
最新交易日栏目使用最近两个已有周一至周五快照，未接入完整交易所日历；最新数据日期仍按全部本地真实文件统计。
聊天支持推荐问题、手动输入、session 内历史记录和清空对话。切换页面或 rerun 不清空聊天；刷新浏览器或开启新 session 不保证保留。

- `agent.py`：整理上下文、识别候选工具、执行真实 Python 分析、构造未来 LLM 消息，返回明确占位回复。
- config.py：使用 python-dotenv 自动加载项目根目录 .env，读取 LLM_API_KEY、LLM_PROVIDER 和 LLM_MODEL；系统环境变量优先。未配置 Key 时保持占位回复，默认使用 zhipu / glm-5.3。可参考 .env.example 配置，真实 Key 不写入 Python 文件。
- 勾选「开发模式：显示 Agent Debug」可查看候选工具、参数、日期范围、真实结果和错误；这些不是模型回答。
- 无明确日期时，「最近」使用最新两个已有快照，否则使用全部已有日期。明确给出的日期缺少快照时报告错误，不替换为其他日期。当前规则不解析历史消息的省略指代。
- `analysis.py` 新增七个工具接口：`compare_dates`、`get_top_increases`、`get_top_decreases`、`get_participant_history`、`get_persistent_increases`、`get_persistent_decreases`、`get_dataset_info`。
- 「持续」采用近期趋势口径：最近最多 6 个已有工作日快照、至少 3 个区间同向变化、同向变化量占总绝对变化量至少 70%，且窗口净变化同向。允许不变或小幅反向变化，至少需要 4 个工作日快照。页面列出窗口和统计数，不代表每日交易。

已接入智谱 Chat Completions，地址为 `https://open.bigmodel.cn/api/paas/v4/chat/completions`。配置 Key 后，提交问题会调用模型并消耗额度；普通页面加载和 Dashboard 不调用模型。请求使用 Bearer 鉴权、`stream=true`、`thinking.type=enabled`、`reasoning_effort=low`。SSE 正文到达后立即逐段展示，完成后保存到聊天记录；不展示模型内部推理字段。若响应中断，以明确错误替换未完成正文。当前仍由本地规则选择工具，模型负责基于工具结果解读，并非模型自主选择工具。

超时、HTTP 错误、流中错误和不完整回答会显示安全错误提示；不打印 Key、请求头或原始错误响应，不自动重试。工具执行失败时不调用模型。全部持仓计算仍由 Python 完成。

`python -m unittest discover -s tests -p test_llm.py -v` 运行本地离线 HTTP 模拟测试，不发送真实请求、不使用真实额度。测试文件统一放在 `tests/`，仅本地保留，不纳入 Git。未验证账户 Key、模型权限及线上返回。`config.py` 和 `.streamlit/secrets.toml` 已加入忽略列表；已被 Git 跟踪的文件不会因新增忽略规则而自动取消跟踪。

## 已回填结果

真实来源：https://www3.hkexnews.hk/sdw/search/searchsdw.aspx

共 12 个真实日期：2026-09-29、09-30、10-02、10-03、10-05、10-06、10-07、10-08、10-09、10-10、10-12、10-13。

10-01、10-04、10-11 返回前一日快照，未错标另存。周六 10-03、10-10 返回对应日期，予以保留。

2026-10-13 共 107 个 Participant，明细股数合计 359,717,170，与网页一致。用户提供的七条记录，其机构名称、股数、占比均匹配。

- `data/ccass_YYYY-MM-DD.csv`：真实持仓；占比为原网页百分数，例如 83.80。
- `data/raw/hkex_YYYY-MM-DD.html`：每次查询原始返回，用于复核和排查。
- `data/fetch_report.json`：逐日抓取结果。
- `data/validation_2026-10-13.json`：七条人工参考记录的本地验收结果。
- 旧 `sample_ccass_*.csv` 为模拟数据，页面与分析扫描不会读取它们。

## 口径和限制

按 Participant ID 全外连接；只出现于一个快照的机构，另一日股数和占比按 0 处理。占比变化单位为百分点，不对网页占比重新归一化。真实快照不要求合计占比为 100%。

抓取器使用实际表单隐藏字段和查询按钮回传参数，串行运行，每日查询后等待 2.5 秒。遇到 HTTP 错误、验证码、访问拒绝、未知提示、异常结构或汇总校验不符时停止，不使用模拟数据替代。失败响应保留在 raw 目录；已成功保存的快照保留。

CCASS Participant 持仓反映的是券商、托管机构等参与者层面的结算后持仓，不等于最终实益拥有人，也不代表实时成交方向。本页面仅用于观察不同日期之间的持仓位置变化。
