from django.urls import path
from index import views
from . import views

urlpatterns = [
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

    path('api/recipes/<str:ing_name>/', views.recipes_from_spoonacular, name='recipes_from_spoonacular'),
    path("api/local_recipes/", views.local_recipes, name="local_recipes"),

    path("api/voice/delete/", views.voice_delete_ingredient, name="voice_delete_ingredient"),
    path("api/daily_recs/", views.api_daily_recs, name="api_daily_recs"),
    

]
