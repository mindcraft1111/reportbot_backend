import logging
import pandas as pd
from langchain_core.tools import tool


# 제품 정보 조회
def load_product_metadata(product_ids: list) -> str:
    from api.models.reviews import Products
    products = Products.objects.filter(id__in=product_ids)
    df = pd.DataFrame(list[products.values])
    return "\n".join([f"[제품 정보]: {row.to_dict()}" for _, row in df.iterrows()])


@tool(description="MySQL 데이터베이스에서 제품 정보를 조회합니다.")
def get_products_info(product1: str, product2: str)->dict:
    # MySQL에서 product 정보 로드
    try:
        products_data = load_product_metadata([product1, product2])

        return {
            "success": True,
            "data": products_data
        }

    except Exception as e:
        logging.error(f"Error getting product info: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }
