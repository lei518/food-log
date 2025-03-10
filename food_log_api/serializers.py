from rest_framework import serializers
from .models import FoodLog, HydrationLog, FoodPreference


class FoodLogSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = FoodLog
        fields = '__all__'

    def get_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %I:%M %p")

class HydrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HydrationLog
        fields = '__all__'

    def get_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %I:%M %p")

class FoodPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodPreference
        fields = ['vegetarian', 'vegan', 'gluten_free', 'dairy_free', 'nut_free', 'calorie_target', 'excluded_ingredients']
