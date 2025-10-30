from django.urls import path
from . import views

urlpatterns = [
    # UI
    path("", views.index, name="index"),
    path("suggest/", views.suggest, name="suggest"),

    # Ingredient CRUD
    path("add/", views.add_ingredient, name="add_ingredient"),
    path("delete/<int:pk>/", views.delete_ingredient, name="delete_ingredient"),
    path("increment/<int:pk>/", views.increment_ingredient, name="increment_ingredient"),
    path("decrement/<int:pk>/", views.decrement_ingredient, name="decrement_ingredient"),
    path("api/ingredient/<int:pk>/adjust/", views.adjust_ingredient, name="adjust_ingredient"),

    # Voice
    path("voice-add/", views.voice_add_ingredient, name="voice_add_ingredient"),
    path("voice-delete/", views.voice_delete_ingredient, name="voice_delete_ingredient"),
    # ถ้าอยากมีเส้นทางใต้ /api/ ด้วย ให้ตั้งชื่อไม่ซ้ำ
    path("api/voice/delete/", views.voice_delete_ingredient, name="api_voice_delete_ingredient"),

    # Recipes / Howto
    path("api/recipe-suggest/", views.api_recipe_suggest, name="api_recipe_suggest"),
    path("api/local_recipes/", views.local_recipes, name="local_recipes"),
    path("api/recipes/", views.api_recipes, name="api_recipes"),
    path("api/recipes/<str:ing_name>/", views.recipes_by_ingredient, name="recipes_by_ingredient"),
    path("api/howto/", views.api_howto, name="api_howto"),
    path("api/howto_all/", views.api_howto_all, name="api_howto_all"),

    # Misc APIs
    path("api/daily_recs/", views.api_daily_recs, name="api_daily_recs"),
    path("api/daily_local_recs/", views.api_daily_recs_local, name="api_daily_recs_local"),
    path("api/lots/", views.api_lot_probe, name="api_lot_probe"),

]
