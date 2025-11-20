from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, me_view, RecipeViewSet, favorite_view ,generate_recipe_view

router = DefaultRouter()
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    # Auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", me_view, name="me"),

    # GenAI generate recipe
    path("recipes/generate/", generate_recipe_view, name="recipe-generate"),

    # Recipes & Favorites
    path("", include(router.urls)), 
    path("favorites/", favorite_view, name="favorites"),

]
