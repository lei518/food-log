from django.urls import path
from . import views

urlpatterns = [
    path('log-food/', views.log_food, name='log-food'),
    path('list-food-logs/', views.list_food_logs, name='list-food-logs'),
    path('log-hydration/', views.log_hydration, name='log-hydration'),
    path('food-log-details/<int:food_id>/', views.food_log_details, name='food-log-details'),
    path('edit-food/<int:food_id>/', views.edit_food, name='edit-food'),
    path('remove-food/', views.remove_food, name='remove-food'),
    path('set-food-preferences/', views.set_food_preferences, name='set-food-preferences'),
    path('search-food/', views.search_food, name='search-food'),
    path('daily-summary/', views.daily_summary, name='daily-summary'),
    path('nutritional-insights/', views.nutritional_insights, name='nutritional-insights'),
    path('food-log-count/', views.food_log_count, name='food-log-count'),
    path('filter-food-category/', views.filter_food_category, name='filter-food-category'),
    path('filter-food-date/', views.filter_food_date, name='filter-food-date'),
    path('filter-food-by-rating/', views.filter_food_by_rating, name='filter-food-by-rating'),
    path('food-cooking-time/', views.food_cooking_time, name='food-cooking-time'),
    path('edit-hydration/', views.edit_hydration, name='edit-hydration'),

]
