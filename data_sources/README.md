# 原始数据接口

供后续页面调用的薄封装，不计算分析指标，不合并 CCASS 和券商数据。
不包含公司资料、财报、卖空、交易下单接口。默认不落盘，不在导入时连接网络。

```python
from data_sources import FutuClient
from data_sources import market, orderbook, brokers, capital, shareholders, ccass
from futu import RET_OK

with FutuClient() as client:
    ret, data = brokers.get_top_ten_buy_sell_brokers(client, "HK.06731", days_before=0)
    if ret != RET_OK:
        raise RuntimeError(data)
    print(data.to_string(index=False))

    ret, tables = shareholders.get_shareholders_overview(client, "HK.06731")
    # tables 原样保留 main_holder / holder_type / holding_period 子表

    ret, bids, asks = orderbook.get_broker_queue(client, "HK.06731")
    ret, frame, next_key = market.request_history_kline(
        client, "HK.06731", start="2026-10-19", end="2026-10-20", max_count=100
    )
    # 分页由调用方显式决定；下一页传 page_req_key=next_key，直至 None。

frame = ccass.get_ccass("06731", "2026-10-13")
# CCASS 复用既有 fetch_day：保留 data/raw HTML；None 表示该日期无数据。
```

| 模块 | 函数 |
|---|---|
| market | get_market_snapshot、get_stock_quote、request_history_kline、get_rt_data、get_rt_ticker |
| orderbook | get_order_book、get_broker_queue |
| brokers | get_top_ten_buy_sell_brokers |
| capital | get_capital_flow、get_capital_distribution |
| shareholders | get_shareholders_overview |
| ccass | get_ccass |

## 返回与错误

- 富途接口原样返回 SDK tuple；不要把错误 payload 当作 DataFrame。
- 通常为 `(ret, data)`；经纪队列和历史 K 线为上述三元组。
- `ret == RET_OK` 且数据为空是无数据；`ret != RET_OK` 是调用失败。
- 必要订阅失败抛 `SubscriptionError`，属性 `ret` / `data` 保留原错误。
- 字段名、单位、类型、数据时间保持来源口径；不按抓取时间补写数据日期。
- 不自动重试、不补零、不自动跨页拉取；历史券商参数仍是交易日偏移，不接受日期转换。

## 连接与调用

`FutuClient` 支持 host/port，默认读取 FUTU_OPEND_HOST/FUTU_OPEND_PORT，
否则使用 127.0.0.1:11111。页面应在一次取数操作中复用同一连接，并在结束时 close。
不要全局缓存共享裸 OpenD 连接。实时接口自动完成必要订阅，不注册脚本推送。
连接关闭后，订阅释放时间由 OpenD 的最短订阅时间等规则决定。

默认每实例每方法 30 秒最多 10 次；其他进程/连接的请求不在该限制内，
服务端实际限频、订阅及历史 K 线额度仍有效。批量 CCASS 查询由调用方串行执行并留出间隔，
不要在页面 rerun 时重复抓取历史数据。

SDK 在项目 .venv 中：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_data_sources.py -v
```

富途字段参考：https://openapi.futunn.com/futu-api-doc/quote/overview.html
