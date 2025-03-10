from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class FoodLog(models.Model):
    food_name = models.CharField(max_length=255)
    serving_size = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(blank=True, null=True)  # ⭐ Rating (1-5)
    review = models.TextField(blank=True, null=True)  # ⭐ Optional review
    category = models.CharField(max_length=50, blank=True, null=True)  # ⭐ Category (e.g., breakfast, lunch)
    cooking_time = models.IntegerField(blank=True, null=True)  # ⭐ Cooking time in minutes
    ingredients = models.JSONField(blank=True, null=True)  # ⭐ List of ingredients (JSON format)
    calories = models.IntegerField(null=True, blank=True)

class HydrationLog(models.Model):
    BEVERAGE_CHOICES = [
        ("water", "Water"),
        ("tea", "Tea"),
        ("coffee", "Coffee"),
        ("juice", "Juice"),
        ("milk", "Milk"),
        ("smoothie", "Smoothie"),
        ("soda", "Soda"),
        ("sports_drink", "Sports Drink"),
        ("other", "Other"),
    ]

    amount = models.PositiveIntegerField()  # In milliliters (ml)
    timestamp = models.DateTimeField(default=timezone.now)
    beverage_type = models.CharField(max_length=20, choices=BEVERAGE_CHOICES, default="water")  # New field

    def __str__(self):
        return f"{self.user.username} - {self.beverage_type} ({self.amount}ml)"

class FoodPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vegetarian = models.BooleanField(default=False)
    vegan = models.BooleanField(default=False)  # ✅ New field
    gluten_free = models.BooleanField(default=False)  # ✅ New field
    dairy_free = models.BooleanField(default=False)  # ✅ New field
    nut_free = models.BooleanField(default=False)
    calorie_target = models.IntegerField(null=True, blank=True)
    excluded_ingredients = models.JSONField(default=list)  # List of ingredients to avoid

    def __str__(self):
        return f"{self.user.username}'s Preferences"
