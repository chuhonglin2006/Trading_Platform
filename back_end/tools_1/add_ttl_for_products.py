""" 生成ttl """

import random


def make_products_ttl():
    """ 生成商品缓存ttl """
    random_ttl = random.randint(0,300)
    fixed_ttl = 1800
    return random_ttl + fixed_ttl


def make_null_ttl():
    """ 生成缓存空值的ttl """
    random_ttl = random.randint(0,30)
    fixed_ttl = 30
    return random_ttl + fixed_ttl




def make_state_ttl(state: str) -> int:
    """ 根据商品不同的状态生成不同的ttl """
    STATE_TTL = {
        "sold": 7 * 24 * 3600,
        "unapproved": 600,
        "off_sale": 60
    }
    return STATE_TTL[state] + random.randint(0, 60)