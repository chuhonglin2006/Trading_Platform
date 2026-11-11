"""商品接口"""
from decimal import Decimal
from typing import Any

from crud_1.produces import (
    change_my_product,
    delete_my_product,
    favorite_produce,
    get_my_favorite,
    get_my_product_info,
    get_my_products,
    get_others_products,
    get_product_info_from_cache,
    get_products_category,
    get_products_list_cache,
    mark_as_sold,
    publish_produce,
    search_product_from_cache,
    unfavorite_produce,
)
from crud_1.users import get_optional_user_info, get_user_info
from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from modles_1.user import User
from schemas_1.products import ProductUpdate
from tools_1.client_ip import get_client_ip
from tools_1.ip_region import get_ip_province
from tools_1.limit import ip_rate_limit

products = APIRouter()


"""获取商品列表接口"""
@products.get("/api/products",dependencies=[Depends(ip_rate_limit("products_list", 120, 60))])
async def get_products(page: int = Query(1, ge=1, le=100),
page_size: int = Query(20, ge=1, le=100),redis=Depends(get_redis)) -> Any | None:
    result = await get_products_list_cache(redis,page = page,page_size = page_size)
    return result

"""搜索商品接口"""
@products.get("/api/products/search")
async def search_products(request:Request,product_name:str = Query(...),
viewer:User | None = Depends(get_optional_user_info),
redis = Depends(get_redis)) -> dict[str, int | str | list[Any]] | None | Any:
    ip = get_client_ip(request)
    who = f"u:{viewer["id"]}" if viewer else f"ip{ip}"
    result = await search_product_from_cache(redis,product_name,who)
    return result

"""获取商品分类接口"""
@products.get("/api/products/categories",dependencies=[Depends(ip_rate_limit("products_categories", 60, 60))])
async def produces_categories(redis=Depends(get_redis)) -> dict[str, Any]:
    result = await get_products_category(redis)
    return result

"""获取商品详细信息接口"""
@products.get("/api/products/{product_id}",dependencies=[Depends(ip_rate_limit("products_detail", 120, 60))])
async def get_produce(request:Request,product_id:int,current_user = Depends(get_optional_user_info),redis = Depends(get_redis)) -> dict[str, Any]:
    client_ip = get_client_ip(request)
    if client_ip == "unknown":
        client_ip = None
    result = await get_product_info_from_cache(
        redis=redis,
        product_id=product_id,
        viewer_id=current_user["id"] if current_user else None,
        client_ip=client_ip
    )
    return result

"""获取本人商品详细信息接口"""
@products.get("/api/my/products/{product_id}")
async def get_my_produce(product_id:int,current_user = Depends(get_user_info),redis = Depends(get_redis)) -> Any | None:
    result = await get_my_product_info(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id
    )
    return result

"""发布商品接口"""
@products.post("/api/products")
async def publish_product(request:Request,product_name:str = Form(...),price:Decimal = Form(...),
original_price:Decimal | None = Form(None),description:str = Form(...),category_id:int = Form(...),
campus:str = Form(...),images: list[UploadFile] = File(...),current_user=Depends(get_user_info),redis = Depends(get_redis)
) -> dict[str,Any]:
    publish_province = await get_ip_province(
        redis,
        get_client_ip(request)
    )
    result = await publish_produce(
        redis=redis,
        user_id=current_user["id"],
        produce_name=product_name,
        price=price,
        original_price=original_price,
        description=description,
        category_id=category_id,
        campus=campus,
        publish_province=publish_province,
        images=images,
    )
    return result

"""获取我的商品接口"""
@products.get("/api/my")
async def my_products(current_user = Depends(get_user_info),page:int = Query(1,ge=1),
page_size:int = Query(20,ge=1,le=100),redis = Depends(get_redis)) -> Any | None:
    result = await get_my_products(
        redis=redis,
        user_id=current_user["id"],
        page=page,page_size=page_size)
    return result

"""收藏商品接口"""
@products.post("/api/favorite/{product_id}")
async def favorite_item(product_id:int,current_user = Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str, Any]:
    await favorite_produce(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id
    )
    return {"code":200,
            "message":"收藏成功"}

"""取消收藏商品接口"""
@products.delete("/api/favorite/{product_id}")
async def delete_favorite_product(product_id:int,current_user = Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str,Any]:
    await unfavorite_produce(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id
    )
    return {
        "code":200,
        "message":"取消收藏成功"
    }

"""获取我的收藏接口"""
@products.get("/api/favorite")
async def get_favorites_list(current_user = Depends(get_user_info),redis = Depends(get_redis)) -> dict[str,Any]:
    result = await get_my_favorite(redis,current_user["id"])
    return {
        "code":200,
        "message":"获取收藏成功",
        "data":result
    }

"""获取他人商品接口"""
@products.get("/api/users/{other_user_id}/products",dependencies=[Depends(ip_rate_limit("others_products", 60, 60))])
async def get_other_user_products(other_user_id: int,page: int = Query(1, ge=1, le=20),
page_size: int = Query(20, ge=1, le=50),redis=Depends(get_redis)) -> Any | None:
    result = await get_others_products(
        redis=redis,
        other_user_id=other_user_id,
        page=page,
        page_size=page_size
    )
    return result

"""删除商品接口"""
@products.delete("/api/products/{product_id}")
async def delete_product_api(product_id: int,current_user=Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str,Any]:
    result = await delete_my_product(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id)
    return result

"""修改商品接口"""
@products.patch("/api/products/{product_id}")
async def change_product_info(product_id: int,data:ProductUpdate,current_user=Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str,Any]:
        result = await change_my_product(
                redis=redis,
                user_id=current_user["id"],
                product_id=product_id,
                **data.model_dump(exclude_unset=True)
            )
        return result

"""标记商品售出接口"""
@products.patch("/api/products/{product_id}/sold")
async def mark_product_as_sold(product_id:int,current_user = Depends(get_user_info),
redis = Depends(get_redis)) -> dict[str,Any]:
    result = await mark_as_sold(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id
    )
    return result



























