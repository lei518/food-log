from rest_framework import serializers
from .models import FoodLog, HydrationLog, FoodPreference

class FoodLogSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = FoodLog
        fields = [
            "user_food_id",
            "user",
            "timestamp",
            "food_name",
            "serving_size",
            "rating",
            "review",
            "category",
            "cooking_time",
            "ingredients",
            "calories",
        ]

    def get_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %I:%M %p")


class HydrationLogSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = HydrationLog
        fields = '__all__'

    def get_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %I:%M %p")

class FoodPreferenceSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = FoodPreference
        fields = ['user', 'vegetarian', 'vegan', 'gluten_free', 'dairy_free', 'nut_free', 'calorie_target', 'excluded_ingredients']
