"""6个月计时器"""
from datetime import datetime
from calendar import monthrange



def get_six_months_ago(dt: datetime) -> datetime:
    """
    获取某个时间点之前的6个月时间
    """
    year = dt.year
    month = dt.month - 6

    if month <= 0:
        year -= 1
        month += 12
    day = min(
        dt.day,
        monthrange(year, month)[1]
    )

    return dt.replace(
        year=year,
        month=month,
        day=day
    )
