# api/genai_service.py
import json
import re
from typing import List, Optional, Dict, Any

import google.generativeai as genai
from django.conf import settings

MODEL_NAME = "gemini-2.0-flash"

GOOGLE_API_KEY = settings.GOOGLE_API_KEY
USE_STUB = False

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    USE_STUB = True
    print("[GenAI] WARNING: GOOGLE_API_KEY is not set. Using stub generator.")


def generate_recipe(
    ingredients: List[str],
    cooking_method: Optional[str] = None,
    cuisine: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trả về dict recipe:
    {
      title, description, ingredients[list[str]], steps[list[str]],
      cooking_method, cuisine,
      nutrition: {calories, protein, fat, carbs}
    }
    """

    ingredients = [str(i).strip() for i in (ingredients or []) if str(i).strip()]

    if not ingredients:
        ingredients = ["nguyên liệu"]

    if USE_STUB:
        return _stub_recipe(ingredients, cooking_method, cuisine)

    system_prompt = (
        "Bạn là một đầu bếp chuyên nghiệp. "
        "Hãy tạo công thức món ăn ở dạng JSON với cấu trúc:\n"
        "{\n"
        '  "title": string,\n'
        '  "description": string,\n'
        '  "ingredients": [string, ...],\n'
        '  "steps": [string, ...],\n'
        '  "cooking_method": string,\n'
        '  "cuisine": string,\n'
        '  "nutrition": {\n'
        '    "calories": string,\n'
        '    "protein": string,\n'
        '    "fat": string,\n'
        '    "carbs": string\n'
        "  }\n"
        "}\n"
        "Chỉ trả về JSON, không giải thích thêm."
    )

    user_payload = {
        "ingredients": ingredients,
        "cooking_method": cooking_method,
        "cuisine": cuisine,
    }

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        resp = model.generate_content(
            [
                system_prompt,
                f"Đây là input của người dùng (JSON):\n{json.dumps(user_payload, ensure_ascii=False)}",
            ]
        )

        text = resp.text or ""
        data = _extract_json(text)
        return _normalize_recipe_dict(data, ingredients, cooking_method, cuisine)

    except Exception as e:
        print("[GenAI] ERROR:", e)
        return _stub_recipe(ingredients, cooking_method, cuisine)


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Lấy JSON đầu tiên trong response (nếu có code block markdown).
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def _normalize_recipe_dict(
    data: Dict[str, Any],
    ingredients_fallback: List[str],
    cooking_method: Optional[str],
    cuisine: Optional[str],
) -> Dict[str, Any]:
    # Title
    title = str(data.get("title") or f"Món ăn từ {', '.join(ingredients_fallback)}")

    # Description
    description = str(data.get("description") or "")

    # Ingredients
    ing = data.get("ingredients") or ingredients_fallback
    if isinstance(ing, str):
        ing_list = [x.strip() for x in ing.split("\n") if x.strip()]
    else:
        ing_list = [str(x).strip() for x in ing if str(x).strip()]

    # Steps
    st = data.get("steps") or []
    if isinstance(st, str):
        steps_list = [x.strip() for x in st.split("\n") if x.strip()]
    else:
        steps_list = [str(x).strip() for x in st if str(x).strip()]

    # Cooking method & cuisine
    cm = data.get("cooking_method") or cooking_method or ""
    cz = data.get("cuisine") or cuisine or ""

    # Nutrition
    raw_nut = data.get("nutrition") or {}
    nutrition = {
        "calories": str(raw_nut.get("calories", "")),
        "protein": str(raw_nut.get("protein", "")),
        "fat": str(raw_nut.get("fat", "")),
        "carbs": str(raw_nut.get("carbs", "")),
    }

    return {
        "title": title,
        "description": description,
        "ingredients": ing_list,
        "steps": steps_list,
        "cooking_method": cm,
        "cuisine": cz,
        "nutrition": nutrition,
    }


def _stub_recipe(
    ingredients: List[str],
    cooking_method: Optional[str],
    cuisine: Optional[str],
) -> Dict[str, Any]:
    title = f"Món ăn từ {', '.join(ingredients)}"
    description = (
        f"Món ăn đơn giản sử dụng nguyên liệu: {', '.join(ingredients)}. "
        "Phù hợp cho bữa ăn hằng ngày."
    )
    steps = [
        "Chuẩn bị và sơ chế tất cả nguyên liệu.",
        "Ướp gia vị cho phù hợp khẩu vị.",
        f"Nấu theo phương pháp: {cooking_method or 'tùy ý'}.",
        "Trình bày và thưởng thức khi còn nóng.",
    ]
    nutrition = {
        "calories": "250 kcal (ước lượng)",
        "protein": "10 g",
        "fat": "8 g",
        "carbs": "30 g",
    }
    return {
        "title": title,
        "description": description,
        "ingredients": ingredients,
        "steps": steps,
        "cooking_method": cooking_method or "",
        "cuisine": cuisine or "",
        "nutrition": nutrition,
    }
