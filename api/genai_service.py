import google.generativeai as genai
from django.conf import settings
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Cấu hình API key
genai.configure(api_key=GOOGLE_API_KEY)

def build_prompt(ingredients, cooking_method=None, cuisine=None):
    """
    Tạo prompt tiếng Việt, có thể chọn cách nấu + vùng miền / quốc gia.
    """
    ing_text = ", ".join(ingredients)

    method_text = (
        f"Ưu tiên cách nấu: {cooking_method}. "
        if cooking_method
        else ""
    )
    cuisine_text = (
        f"Ưu tiên món ăn thuộc ẩm thực: {cuisine}. "
        if cuisine
        else ""
    )

    prompt = f"""
Bạn là một đầu bếp chuyên nghiệp. Hãy tạo một món ăn từ các nguyên liệu sau: {ing_text}.

{method_text}{cuisine_text}

Yêu cầu:
- Tên món ăn (tiếng Việt, có thể ghi thêm tên tiếng Anh nếu hợp lý).
- Thông tin ngắn gọn về món ăn (nguồn gốc, kiểu món).
- Danh sách nguyên liệu chi tiết (có định lượng ước lượng).
- Các bước nấu ăn rõ ràng, đánh số bước.
- Gợi ý cách trình bày món ăn và ăn kèm.

Hãy trả kết quả ở dạng JSON với cấu trúc:
{{
  "title": "Tên món",
  "description": "Mô tả ngắn",
  "ingredients": [
    "nguyên liệu 1 - số lượng",
    "nguyên liệu 2 - số lượng"
  ],
  "steps": [
    "Bước 1 ...",
    "Bước 2 ..."
  ],
  "cuisine": "Tên vùng miền / quốc gia (nếu có)",
  "cooking_method": "Kiểu nấu chính (chiên/xào/nướng/hấp/luộc/...",
  "tips": "Một vài mẹo nhỏ hoặc gợi ý trình bày"
}}

Chỉ trả về JSON, không thêm giải thích bên ngoài.
    """
    return prompt


def generate_recipe_from_genai(ingredients, cooking_method=None, cuisine=None):
    """
    Gọi Gemini để tạo recipe và parse về dạng dict Python.
    """
    prompt = build_prompt(ingredients, cooking_method, cuisine)

    model = genai.GenerativeModel("gemini-2.0-flash")  # hoặc model khác bạn dùng
    response = model.generate_content(prompt)

    text = response.text.strip()

    # Thử parse JSON
    import json

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Trường hợp model trả thêm text ngoài JSON → cố gắng cắt phần JSON
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start : end + 1]
            data = json.loads(json_str)
        else:
            raise ValueError("Không parse được JSON từ GenAI response")

    return data
