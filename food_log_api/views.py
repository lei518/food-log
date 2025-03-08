from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import datetime
from django.utils.timezone import make_aware, now, timedelta
from django.utils import timezone  # ✅ Import this to fix the error
from collections import Counter
from django.db.models import Q, Sum, Count
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import FoodLog, HydrationLog, FoodPreference
from .serializers import FoodLogSerializer, HydrationLogSerializer, FoodPreferenceSerializer

# Log Food Entry (Includes optional rating and review)

PROTEIN_RICH = {"chicken", "beef", "fish", "tofu", "eggs", "beans", "lentils"}
CARBS_RICH = {"rice", "pasta", "bread", "potatoes", "noodles", "cereal"}
FIBER_RICH = {"broccoli", "carrots", "spinach", "beans", "whole grains", "nuts"}

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Require authentication
def log_food(request):
    serializer = FoodLogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# List all logged food intake
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_food_logs(request):
    food_logs = FoodLog.objects.all()
    serializer = FoodLogSerializer(food_logs, many=True)
    return Response(serializer.data)

# Retrieve details of a specific logged food item
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_log_details(request, food_id):
    user = request.user
    food_log = get_object_or_404(FoodLog, id=food_id)  # ✅ Handles 404 if food_id doesn't exist
    preferences = FoodPreference.objects.filter(user=user).first()

    data = {
        "name": food_log.food_name,
        "ingredients": ["carrots", "broccoli", "mushrooms"],  # Example ingredients
        "calories": 350
    }

    # ✅ Ensure preferences and excluded_ingredients exist before checking
    excluded_ingredients = getattr(preferences, "excluded_ingredients", [])

    if excluded_ingredients:
        for ingredient in data["ingredients"]:
            if ingredient in excluded_ingredients:
                data["warning"] = f"This food contains an ingredient you want to avoid: {ingredient}"
                break  # Stop after finding one warning

    return Response(data)
# Edit an existing food intake log
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_food(request, food_id):
    try:
        food_log = FoodLog.objects.get(id=food_id)
    except FoodLog.DoesNotExist:
        return Response({"error": "Food log not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = FoodLogSerializer(food_log, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete a food intake log
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_food(request):
    log_id = request.GET.get('logId')
    if not log_id:
        return Response({"error": "logId parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        food_log = FoodLog.objects.get(id=log_id)
        food_log.delete()
        return Response({"message": "Food log deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    except FoodLog.DoesNotExist:
        return Response({"error": "Food log not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_food_preferences(request):
    user = request.user
    preferences, created = FoodPreference.objects.get_or_create(user=user)
    serializer = FoodPreferenceSerializer(preferences, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Preferences updated", "preferences": serializer.data}, status=200)

    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_food(request):
    query = request.GET.get('query', '')

    if query.lower() == "food":  # If user searches for "food", return everything
        results = FoodLog.objects.all().values('food_name', 'category', 'ingredients')
    else:
        results = FoodLog.objects.filter(
            Q(food_name__icontains=query) |
            Q(ingredients__icontains=query)
        ).values('food_name', 'category', 'ingredients')

    return Response(list(results))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_summary(request):
    user = request.user  # Ensure the summary is for the logged-in user
    date_str = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))  # Default to today
    date = make_aware(datetime.strptime(date_str, '%Y-%m-%d'))  # Convert to Django timezone-aware datetime

    # Get food logs for the selected date
    food_logs = FoodLog.objects.filter(timestamp__date=date.date())

    # Calculate total calories
    total_calories = food_logs.aggregate(Sum('calories'))['calories__sum'] or 0

    # Count food categories
    category_breakdown = {}
    for log in food_logs:
        category = log.category or "Uncategorized"
        category_breakdown[category] = category_breakdown.get(category, 0) + 1

    # Get hydration logs for the selected date
    total_water_intake = HydrationLog.objects.filter(timestamp__date=date.date()).aggregate(Sum('amount'))['amount__sum'] or 0

    # List food items logged
    food_items = [{"name": log.food_name, "calories": log.calories, "category": log.category} for log in food_logs]

    # Response Data
    summary = {
        "date": date_str,
        "total_calories": total_calories,
        "category_breakdown": category_breakdown,
        "total_water_intake_ml": total_water_intake,
        "food_items_logged": food_items,
    }

    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nutritional_insights(request):
    user = request.user
    one_week_ago = now() - timedelta(days=7)

    # Get all food logs from the last 7 days
    food_logs = FoodLog.objects.filter(timestamp__gte=one_week_ago)

    # Count ingredient categories
    protein_count = 0
    carb_count = 0
    fiber_count = 0

    for log in food_logs:
        if log.ingredients:  # Ensure ingredients field exists
            for ingredient in log.ingredients:
                ingredient = ingredient.lower()  # Normalize case
                if ingredient in PROTEIN_RICH:
                    protein_count += 1
                if ingredient in CARBS_RICH:
                    carb_count += 1
                if ingredient in FIBER_RICH:
                    fiber_count += 1

    # Generate nutritional insights
    suggestions = []
    if protein_count > carb_count and protein_count > fiber_count:
        suggestions.append("You've logged a lot of protein. Try adding more fiber-rich foods like vegetables or whole grains.")
    if carb_count > protein_count:
        suggestions.append("Consider increasing protein intake for better balance.")
    if fiber_count < protein_count and fiber_count < carb_count:
        suggestions.append("Your fiber intake seems low. Add more leafy greens, beans, and nuts.")

    return Response({
        "summary": {
            "Protein-Rich Meals": protein_count,
            "Carb-Rich Meals": carb_count,
            "Fiber-Rich Meals": fiber_count
        },
        "suggestions": suggestions or ["Your diet seems balanced!"]
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_log_count(request):
    date_from = request.GET.get('dateFrom')
    date_to = request.GET.get('dateTo')

    # Validate and parse dates
    if date_from:
        date_from = parse_date(date_from)
    if date_to:
        date_to = parse_date(date_to)

    # Filter logs within the specified date range
    logs = FoodLog.objects.all()
    if date_from and date_to:
        logs = logs.filter(timestamp__date__range=[date_from, date_to])
    elif date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    elif date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    # Count the total food log entries
    total_entries = logs.count()

    return Response({"totalEntries": total_entries})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_category(request):
    category = request.GET.get('category', None)

    if not category:
        return Response({"error": "Category is required."}, status=400)

    filtered_food = FoodLog.objects.filter(category__iexact=category).values(
        'id', 'food_name', 'serving_size', 'timestamp', 'category'
    )

    return Response(list(filtered_food))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_date(request):
    date_from = request.GET.get('dateFrom', None)
    date_to = request.GET.get('dateTo', None)

    if not date_from or not date_to:
        return Response({"error": "Both dateFrom and dateTo are required."}, status=400)

    try:
        date_from = make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
        date_to = make_aware(datetime.strptime(date_to, "%Y-%m-%d"))
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    filtered_food = FoodLog.objects.filter(timestamp__range=[date_from, date_to]).values(
        'id', 'food_name', 'serving_size', 'timestamp'
    )

    return Response(list(filtered_food))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_by_rating(request):
    min_rating = request.GET.get('minRating')

    if not min_rating:
        return Response({"error": "minRating is required."}, status=400)

    try:
        min_rating = int(min_rating)
        if min_rating < 1 or min_rating > 5:
            raise ValueError("Rating must be between 1 and 5.")
    except ValueError:
        return Response({"error": "minRating must be an integer between 1 and 5."}, status=400)

    filtered_food = FoodLog.objects.filter(
        rating__gte=min_rating
    ).values('id', 'food_name', 'serving_size', 'timestamp', 'rating', 'review')

    response_data = [
        {
            "logId": entry["id"],
            "foodName": entry["food_name"],
            "servingSize": entry["serving_size"],
            "timestamp": entry["timestamp"],
            "rating": entry["rating"],
            "notes": entry["review"]
        }
        for entry in filtered_food
    ]

    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_cooking_time(request):
    log_id = request.GET.get('logId')

    if not log_id:
        return Response({"error": "logId is required."}, status=400)

    try:
        food_log = FoodLog.objects.get(id=log_id)
        if food_log.cooking_time is None:
            return Response({"message": "Cooking time not available for this entry."})
        return Response({
            "logId": food_log.id,
            "foodName": food_log.food_name,
            "cookingTime": food_log.cooking_time
        })
    except FoodLog.DoesNotExist:
        return Response({"error": "Food log not found."}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_hydration(request):
    amount = request.data.get("amount")
    beverage_type = request.data.get("beverageType", "water").lower()
    timestamp = request.data.get("timestamp", timezone.now())

    # Validate amount
    if not amount or float(amount) <= 0:
        return Response({"error": "Invalid amount. Please enter a positive value."}, status=400)

    # Validate beverage type
    valid_beverages = dict(HydrationLog.BEVERAGE_CHOICES).keys()
    if beverage_type not in valid_beverages:
        return Response({"error": f"Invalid beverage type. Choose from {list(valid_beverages)}."}, status=400)

    # Log hydration entry (Removed user=request.user)
    hydration_log = HydrationLog.objects.create(
        amount=amount,
        beverage_type=beverage_type,
        timestamp=timestamp
    )

    return Response({
        "hydrationId": hydration_log.id,
        "amount": hydration_log.amount,
        "beverageType": hydration_log.beverage_type,
        "timestamp": hydration_log.timestamp,
        "message": f"Successfully logged {hydration_log.amount}ml of {hydration_log.beverage_type}!"
    })


@api_view(['PUT'])
def edit_hydration(request):
    hydration_id = request.data.get('hydrationId')
    amount = request.data.get('amount')
    beverage_type = request.data.get('beverageType')
    timestamp = request.data.get('timestamp')

    if not hydration_id:
        return Response({"error": "hydrationId is required."}, status=400)

    try:
        hydration_log = HydrationLog.objects.get(id=hydration_id)

        # Validate and update amount
        if amount is not None:
            if float(amount) <= 0:
                return Response({"error": "Invalid amount. Please enter a positive value."}, status=400)
            hydration_log.amount = amount

        # Validate and update beverage type
        if beverage_type:
            valid_beverages = dict(HydrationLog.BEVERAGE_CHOICES).keys()
            if beverage_type.lower() not in valid_beverages:
                return Response({"error": f"Invalid beverage type. Choose from {list(valid_beverages)}."}, status=400)
            hydration_log.beverage_type = beverage_type.lower()

        # Update timestamp if provided
        if timestamp:
            hydration_log.timestamp = timestamp

        hydration_log.save()

        return Response({
            "hydrationId": hydration_log.id,
            "amount": hydration_log.amount,
            "beverageType": hydration_log.beverage_type,
            "timestamp": hydration_log.timestamp,
            "message": "Hydration log successfully updated!"
        })

    except HydrationLog.DoesNotExist:
        return Response({"error": "Hydration log not found."}, status=404)
