from django.urls import path
from . import views

urlpatterns = [
    path('log-food/', views.log_food, name='log-food'),
    path('list-food-logs/', views.list_food_logs, name='list-food-logs'),
    path('log-hydration/', views.log_hydration, name='log-hydration'),
    path('food-log-details/<int:user_food_id>/', views.food_log_details, name='food-log-details'),
    path('edit-food/<int:user_food_id>/', views.edit_food, name='edit-food'),
    path('remove-food/<int:user_food_id>/', views.remove_food, name='remove-food'),
    path('set-food-preferences/', views.set_food_preferences, name='set-food-preferences'),
    path('list-food-preferences/', views.list_food_preferences, name='list-food-preferences'),
    path('search-food/', views.search_food, name='search-food'),
    path('daily-summary/', views.daily_summary, name='daily-summary'),
    path('nutritional-insights/', views.nutritional_insights, name='nutritional-insights'),
    path('filter-food-category/', views.filter_food_category, name='filter-food-category'),
    path('filter-food-date/', views.filter_food_date, name='filter-food-date'),
    path('filter-food-by-rating/', views.filter_food_by_rating, name='filter-food-by-rating'),
    path('food-cooking-time/', views.food_cooking_time, name='food-cooking-time'),
    path('edit-hydration/<int:user_hydration_id>/', views.edit_hydration, name='edit-hydration'),
    path('list-hydration-logs/', views.list_hydration_logs, name='list-hydration-logs'),
    path('clear-hydration-logs/', views.clear_hydration_logs, name='clear-hydration-logs'),
    path('clear-food-logs/', views.clear_food_logs, name='clear-food-logs'),
    path('remove-hydration/<int:user_hydration_id>/', views.remove_hydration, name='remove-hydration'),
    path('register/', views.register_user, name='register_user'),

]
