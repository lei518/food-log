from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class FoodLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_food_id = models.PositiveIntegerField(editable=False, null=True)
    food_name = models.CharField(max_length=255)
    serving_size = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(blank=True, null=True)
    review = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    cooking_time = models.IntegerField(blank=True, null=True)
    ingredients = models.JSONField(blank=True, null=True)
    calories = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.user_food_id:
            last_log = FoodLog.objects.filter(user=self.user).order_by('-user_food_id').first()
            self.user_food_id = (last_log.user_food_id + 1) if last_log else 1
        super().save(*args, **kwargs)

class HydrationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_hydration_id = models.PositiveIntegerField(editable=False, null=True)
    amount = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    beverage_type = models.CharField(max_length=50)

    BEVERAGE_CHOICES = [
        "water", "tea", "coffee", "juice", "milk", "smoothie",
        "soda", "sports drink", "other"
    ]

    def save(self, *args, **kwargs):
        if not self.user_hydration_id:
            last_log = HydrationLog.objects.filter(user=self.user).order_by('-user_hydration_id').first()
            self.user_hydration_id = (last_log.user_hydration_id + 1) if last_log else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.beverage_type} ({self.amount}ml)"


class FoodPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vegetarian = models.BooleanField(default=False)
    vegan = models.BooleanField(default=False)
    gluten_free = models.BooleanField(default=False)
    dairy_free = models.BooleanField(default=False)
    nut_free = models.BooleanField(default=False)
    calorie_target = models.IntegerField(null=True, blank=True)
    excluded_ingredients = models.JSONField(default=list)

    def __str__(self):
        return f"{self.user.username}'s Preferences"
