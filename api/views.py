# api/views.py

from django.shortcuts import render

from rest_framework import (
    generics,
    permissions,
    viewsets,
    status,
    serializers,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, inline_serializer

from .models import Recipe, FavoriteRecipe
from .serializers import (
    RegisterSerializer,
    RecipeSerializer,
    FavoriteSerializer,
    GenerateRecipeInputSerializer,
)
from .genai_service import generate_recipe


# ==========================
#  ĐĂNG KÝ TÀI KHOẢN
# ==========================
class RegisterView(generics.CreateAPIView):
    """
    Đăng ký tài khoản mới.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register",
        description="Tạo mới một tài khoản người dùng.",
        request=RegisterSerializer,
        responses=RegisterSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ==========================
#  LẤY THÔNG TIN USER HIỆN TẠI
# ==========================
@extend_schema(
    methods=["GET"],
    tags=["Auth"],
    summary="Get current user info",
    responses=inline_serializer(
        name="MeResponse",
        fields={
            "id": serializers.IntegerField(),
            "username": serializers.CharField(),
            "email": serializers.EmailField(),
        },
    ),
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """
    Trả về thông tin user đang đăng nhập.
    """
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


# ==========================
#  RECIPE CRUD
# ==========================
class RecipeViewSet(viewsets.ModelViewSet):
    """
    CRUD cho Recipe.
    - Ai cũng xem được (GET).
    - Chỉ user đã đăng nhập mới tạo / sửa / xoá.
    """
    queryset = Recipe.objects.all().order_by("-created_at")
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @extend_schema(
        tags=["Recipes"],
        summary="List recipes",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Recipes"],
        summary="Create recipe",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Recipes"],
        summary="Retrieve recipe",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Recipes"],
        summary="Update recipe",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Recipes"],
        summary="Partial update recipe",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Recipes"],
        summary="Delete recipe",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# ==========================
#  FAVORITE RECIPES
# ==========================
@extend_schema(
    methods=["GET"],
    tags=["Favorites"],
    summary="List favorite recipes",
    responses=FavoriteSerializer(many=True),
)
@extend_schema(
    methods=["POST"],
    tags=["Favorites"],
    summary="Add recipe to favorites",
    request=FavoriteSerializer,
    responses=FavoriteSerializer,
)
@extend_schema(
    methods=["DELETE"],
    tags=["Favorites"],
    summary="Remove recipe from favorites",
    request=inline_serializer(
        name="FavoriteDeleteRequest",
        fields={
            "recipe_id": serializers.IntegerField(),
        },
    ),
    responses=None,
)
@api_view(["GET", "POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def favorite_view(request):
    """
    GET    → danh sách món yêu thích của user
    POST   → thêm 1 recipe vào favorites
    DELETE → xoá 1 recipe khỏi favorites
    """
    user = request.user

    # GET: list
    if request.method == "GET":
        qs = FavoriteRecipe.objects.filter(user=user).select_related("recipe")
        serializer = FavoriteSerializer(qs, many=True)
        return Response(serializer.data)

    # POST: add
    if request.method == "POST":
        serializer = FavoriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.validated_data["recipe"]
        fav, created = FavoriteRecipe.objects.get_or_create(user=user, recipe=recipe)
        return Response(FavoriteSerializer(fav).data, status=status.HTTP_201_CREATED)

    # DELETE: remove
    if request.method == "DELETE":
        recipe_id = request.data.get("recipe_id")
        if recipe_id is None:
            return Response(
                {"detail": "recipe_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        FavoriteRecipe.objects.filter(user=user, recipe_id=recipe_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==========================
#  GENAI: GENERATE RECIPE
# ==========================
@extend_schema(
    methods=["POST"],
    tags=["AI Recipes"],
    summary="Generate recipe with Gemini",
    description=(
        "Sinh công thức món ăn từ danh sách nguyên liệu, "
        "sau đó lưu thành Recipe (is_ai_generated=True)."
    ),
    request=GenerateRecipeInputSerializer,
    responses=inline_serializer(
        name="GenerateRecipeResponse",
        fields={
            "success": serializers.BooleanField(),
            "data": RecipeSerializer(),
            "raw": serializers.JSONField(),
        },
    ),
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])  # đổi thành AllowAny nếu muốn public, IsAuthenticated
def generate_recipe_view(request):
    """
    Body mẫu:
    {
      "ingredients": ["trứng", "cà chua", "hành lá"],
      "cooking_method": "chiên",
      "cuisine": "Việt Nam"
    }
    """
    # Validate input
    serializer = GenerateRecipeInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    ingredients = serializer.validated_data["ingredients"]
    cooking_method = serializer.validated_data.get("cooking_method") or None
    cuisine = serializer.validated_data.get("cuisine") or None

    # Gọi Gemini
    try:
        gen_data = generate_recipe(
            ingredients,
            cooking_method=cooking_method,
            cuisine=cuisine,
        )
    except Exception as e:
        # Có thể log thêm ở đây nếu cần
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Map dữ liệu GenAI sang model Recipe
    title = gen_data.get("title", "Món ăn gợi ý")
    description = gen_data.get("description", "")
    ingredients_text = "\n".join(gen_data.get("ingredients", []))
    steps_list = gen_data.get("steps", [])
    steps_text = "\n".join(steps_list)

    recipe = Recipe.objects.create(
        title=title,
        description=description,
        ingredients_text=ingredients_text,
        steps=steps_text,
        image_url="",  # sau này có thể thêm ảnh GenAI
        is_ai_generated=True,
        author=request.user,
    )

    recipe_data = RecipeSerializer(recipe).data

    return Response(
        {
            "success": True,
            "data": recipe_data,
            "raw": gen_data,
        },
        status=status.HTTP_201_CREATED,
    )
