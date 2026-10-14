# 06731 CCASS 真实持仓 Demo

在项目目录的 PowerShell 中运行（如已有虚拟环境，先激活）：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python fetch_ccass.py 06731 2026-09-29 2026-10-13
python -m streamlit run app.py
```

无需调用 `streamlit.exe`。页面仅从本地 CSV 读取，不发出网络请求。

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
