"""商品状态转换规则 纯函数 不访问数据库

商品由两个字段共同描述：
    status         on_sale / off_sale / sold
    review_status  pending / approved / rejected

各种情况 不新增枚举值，也不改表结构

    状态                              status     review_status   是否有进行中的订单
    --------------------------------  ---------  --------------  ------------------
    待审核（新发布 / 修改后重新提交）   on_sale    pending                 否
    在售                              on_sale    approved             否
    被订单占用（预订中）               off_sale   approved               是（pending）
    被驳回 / 管理员强制下架            off_sale   rejected               — 强制下架时会取消待完成订单）
    已售出                            sold       approved              —

关键规则：
    - 被驳回 / 强制下架的商品（rejected）不会因为取消订单而自动重新上架
    - 卖家修改被驳回的商品 = 重新提交审核，状态回到「待审核」
    - 审核通过时，没有进行中订单的商品会自动变回在售
"""


def status_after_order_cancelled(review_status: str) -> str:
    """订单取消后，商品应该处于什么状态。"""
    return "off_sale" if review_status == "rejected" else "on_sale"


def status_after_resubmit(current_status: str, previous_review_status: str) -> str:
    """
    卖家修改商品后重新提交审核，商品的上下架状态应该是什么。
    只有「被驳回」的商品会回到在售（等待审核，对外仍不可见）。
    """
    if current_status == "off_sale" and previous_review_status == "rejected":
        return "on_sale"
    return current_status


def status_after_approval(current_status: str, has_active_order: bool) -> str:
    """
    审核通过后，商品应该处于什么状态。
    被订单占用的商品保持下架，等订单结束后再决定；其余的重新上架。
    """
    if current_status == "off_sale" and not has_active_order:
        return "on_sale"
    return current_status