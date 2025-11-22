# api/genai_service.py
import os
import json
import re
from typing import List, Optional, Dict, Any

import google.generativeai as genai

# Lấy API key từ env do Render cung cấp
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    # Lỗi rõ ràng, dễ debug trên log Render
    raise RuntimeError("GOOGLE_API_KEY is not set. Please add it to Render Environment.")

genai.configure(api_key=GOOGLE_API_KEY)


def build_prompt(
    ingredients: List[str],
    cooking_method: Optional[str] = None,
    cuisine: Optional[str] = None,
) -> str:
    ing_text = ", ".join(ingredients)

    method_text = f"Ưu tiên cách nấu: {cooking_method}. " if cooking_method else ""
    cuisine_text = f"Ưu tiên món ăn thuộc ẩm thực: {cuisine}. " if cuisine else ""

    prompt = f"""
Bạn là một đầu bếp chuyên nghiệp. Hãy tạo một món ăn từ các nguyên liệu sau: {ing_text}.

{method_text}{cuisine_text}

BẮT BUỘC phải có ĐẦY ĐỦ các phần sau:

1) TÊN MÓN ĂN
2) MÔ TẢ NGẮN
3) NGUYÊN LIỆU (danh sách, mỗi phần tử là một chuỗi)
4) CÁC BƯỚC NẤU ĂN (danh sách, mỗi phần tử là một bước)
5) THÔNG TIN DINH DƯỠNG CƠ BẢN

Trả về JSON với cấu trúc:
{{
  "title": "Tên món (có thể kèm tiếng Anh)",
  "description": "Mô tả ngắn về món ăn",
  "ingredients": [
    "nguyên liệu 1 - số lượng",
    "nguyên liệu 2 - số lượng"
  ],
  "steps": [
    "Bước 1 ...",
    "Bước 2 ..."
  ],
  "cooking_method": "Kiểu nấu chính (chiên/xào/nướng/hấp/luộc/...)",
  "cuisine": "Tên vùng miền / quốc gia (nếu có)",
  "nutrition": {{
    "calories": "ước lượng kcal mỗi khẩu phần (dạng chuỗi)",
    "protein": "ước lượng protein",
    "fat": "ước lượng chất béo",
    "carbs": "ước lượng carb"
  }}
}}

Chỉ trả về JSON hợp lệ, không thêm chữ giải thích bên ngoài.
    """
    return prompt.strip()


def _to_list(field: Any) -> List[str]:
    """
    Chuẩn hoá field về list[str] để FE luôn xài được.
    - Nếu là list -> lọc & cast về str.
    - Nếu là string -> tách theo xuống dòng / dấu đầu dòng / số thứ tự.
    """
    if isinstance(field, list):
        return [str(x).strip() for x in field if str(x).strip()]

    if isinstance(field, str):
        parts = re.split(r"\r?\n|·|•|-|\u2022|\d+\.", field)
        return [p.strip() for p in parts if p.strip()]

    return []


def generate_recipe(
    ingredients: List[str],
    cooking_method: Optional[str] = None,
    cuisine: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gọi Gemini để sinh công thức món ăn.
    Đảm bảo output luôn có:
    - title: str
    - ingredients: list[str]
    - steps: list[str]
    - cooking_method: Optional[str]
    - cuisine: Optional[str]
    - nutrition: dict với calories/protein/carbs/fat là str
    """
    prompt = build_prompt(ingredients, cooking_method, cuisine)

    # Model ổn định
    model = genai.GenerativeModel("gemini-2.0-flash")

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        print("GENAI CALL ERROR:", repr(e))
        raise

    text = (getattr(response, "text", "") or "").strip()
    print("GENAI RAW TEXT:", text[:500])

    # Parse JSON thô
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Không parse được JSON từ GenAI response")
        data = json.loads(text[start : end + 1])

    # --- Chuẩn hoá bắt buộc ---

    # 1) Title / description
    data["title"] = str(data.get("title", "Món ăn từ SmartChef")).strip()
    if not data["title"]:
        data["title"] = "Món ăn từ SmartChef"

    if "description" in data:
        desc = str(data.get("description", "")).strip()
        data["description"] = desc or None
    else:
        data["description"] = None

    # 2) Ingredients & steps -> luôn là list[str]
    data["ingredients"] = _to_list(data.get("ingredients"))
    data["steps"] = _to_list(data.get("steps"))

    # 3) Cooking method & cuisine
    if cooking_method and not data.get("cooking_method"):
        data["cooking_method"] = cooking_method
    else:
        cm = str(data.get("cooking_method", "")).strip()
        data["cooking_method"] = cm or None

    if cuisine and not data.get("cuisine"):
        data["cuisine"] = cuisine
    else:
        cz = str(data.get("cuisine", "")).strip()
        data["cuisine"] = cz or None

    # 4) Nutrition: luôn có đủ 4 field ở dạng string
    raw_nut = data.get("nutrition") or {}
    data["nutrition"] = {
        "calories": str(raw_nut.get("calories", "") or "—"),
        "protein": str(raw_nut.get("protein", "") or "—"),
        "fat": str(raw_nut.get("fat", "") or "—"),
        "carbs": str(raw_nut.get("carbs", "") or "—"),
    }

    return data
