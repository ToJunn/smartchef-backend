import os
import json
import google.generativeai as genai

# Lấy API key từ env do Render cung cấp
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    # Lỗi rõ ràng, dễ debug trên log Render
    raise RuntimeError("GOOGLE_API_KEY is not set. Please add it to Render Environment.")

genai.configure(api_key=GOOGLE_API_KEY)


def build_prompt(ingredients, cooking_method=None, cuisine=None):
    ing_text = ", ".join(ingredients)

    method_text = f"Ưu tiên cách nấu: {cooking_method}. " if cooking_method else ""
    cuisine_text = f"Ưu tiên món ăn thuộc ẩm thực: {cuisine}. " if cuisine else ""

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
  "cooking_method": "Kiểu nấu chính (chiên/xào/nướng/hấp/luộc/...)",
  "tips": "Một vài mẹo nhỏ hoặc gợi ý trình bày"
}}

Chỉ trả về JSON, không thêm giải thích bên ngoài.
    """
    return prompt.strip()


def generate_recipe(ingredients, cooking_method=None, cuisine=None):
    prompt = build_prompt(ingredients, cooking_method, cuisine)

    # Dùng model ổn định để test
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        # Log chi tiết ra console để xem trên Render logs
        print("GENAI CALL ERROR:", repr(e))
        raise

    text = (response.text or "").strip()
    print("GENAI RAW TEXT:", text[:500])  # log 500 ký tự đầu

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start : end + 1]
            return json.loads(json_str)

        # Nếu tới đây vẫn fail → raise lỗi rõ ràng
        raise ValueError("Không parse được JSON từ GenAI response")
