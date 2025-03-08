from rest_framework import serializers
from .models import FoodLog, HydrationLog, FoodPreference

class FoodLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodLog
        fields = '__all__'

class HydrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HydrationLog
        fields = '__all__'

class FoodPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodPreference
        fields = '__all__'