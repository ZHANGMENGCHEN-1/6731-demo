"""按来源分类的数据接口；不计算分析指标，不在导入时连接 OpenD。"""

from .client import FutuClient, SubscriptionError

__all__ = ["FutuClient", "SubscriptionError"]
