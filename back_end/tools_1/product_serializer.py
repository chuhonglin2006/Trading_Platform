""" 将商品信息转为公共的字典信息 """
from fastapi.encoders import jsonable_encoder

from tools_1.uload_image_to_server import normalize_image_url


def build_product_detail(product) -> dict:
    """ 商品公共数据 详情缓存和预热共用 """
    return jsonable_encoder({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "original_price": product.original_price,
        "description": product.description,
        "status": product.status,
        "campus": product.campus,
        "publish_province": product.publish_province,
        "view_count": product.view_count,
        "created_at": product.created_at,
        "images": [normalize_image_url(i.image_url) for i in product.images],
        "category": {
            "id": product.category.id,
            "key": product.category.key,
            "name": product.category.name,
        } if product.category else None,
        "seller": {
            "id": product.seller.id,
            "username": product.seller.username,
        } if product.seller else None,
    })
