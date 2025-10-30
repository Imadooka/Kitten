from django.urls import path
from . import views

urlpatterns = [
    path('api/howto/', views.api_howto, name='api_howto'),
    path('api/recipes/', views.api_recipes, name='api_recipes'),

    path("api/daily_local_recs/", views.api_daily_recs_local, name="api_daily_recs_local"),

    path('', views.index, name='index'),
    path('delete/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('add/', views.add_ingredient, name='add_ingredient'),  
    path('voice-add/', views.voice_add_ingredient, name='voice_add_ingredient'),

    path('suggest/', views.suggest, name='suggest'),
    path('api/recipe-suggest/', views.api_recipe_suggest, name='api_recipe_suggest'),
    path('voice-delete/', views.voice_delete_ingredient, name='voice_delete_ingredient'),

    path('delete/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('decrement/<int:ingredient_id>/', views.decrement_ingredient, name='decrement_ingredient'),  # -1
    path('increment/<int:ingredient_id>/', views.increment_ingredient, name='increment_ingredient'),  # +1

    #path('api/recipes/<str:ing_name>/', views.recipes_from_spoonacular, name='recipes_from_spoonacular'),
    path("api/local_recipes/", views.local_recipes, name="local_recipes"),
    path("api/lots/", views.api_lot_probe, name="api_lot_probe"),
    

    path("api/voice/delete/", views.voice_delete_ingredient, name="voice_delete_ingredient"),
    path("api/daily_recs/", views.api_daily_recs, name="api_daily_recs"),
    path("api/recipes/<str:ing_name>/", views.recipes_by_ingredient, name="recipes_by_ingredient"),
    path("api/ingredient/<int:ingredient_id>/adjust/", views.adjust_ingredient, name="adjust_ingredient"),

    path("api/howto_all/", views.api_howto_all, name="api_howto_all"),
   

]
