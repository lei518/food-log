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
@permission_classes([IsAuthenticated])
def log_food(request):
    # ✅ Get user preferences (skip user-related queries)
    try:
        preferences = FoodPreference.objects.get(user=request.user)
    except FoodPreference.DoesNotExist:
        preferences = None  # No preferences set

    # ✅ Extract food details from request
    food_name = request.data.get("food_name")
    category = request.data.get("category", "unknown")  # Default to 'unknown' if not provided
    calories = request.data.get("calories", 0)  # Default to 0
    ingredients = request.data.get("ingredients", [])  # Ensure it's a list
    serving_size = request.data.get("serving_size", "unknown")  # Default value
    cooking_time = request.data.get("cooking_time", 0)  # Default to 0
    rating = request.data.get("rating", None)  # Optional
    review = request.data.get("review", "")  # Default to empty string

    # ✅ Check for preference violations
    warnings = []

    if preferences:
        # 🚨 Vegetarian/Vegan Check
        meat_ingredients = ["chicken", "beef", "pork", "fish", "seafood", "lamb", "turkey"]
        if preferences.vegetarian and any(item.lower() in meat_ingredients for item in ingredients):
            warnings.append("This food contains meat, which is against your preferences.")
        if preferences.vegan and any(item.lower() in meat_ingredients + ["milk", "cheese", "egg", "butter", "yogurt"] for item in ingredients):
            warnings.append("This food contains animal products, which is against your vegan preference.")

        # 🚨 Nut-Free, Gluten-Free, Dairy-Free Check
        restricted_ingredients = {
            "nut_free": ["peanut", "almond", "cashew", "hazelnut"],
            "gluten_free": ["wheat", "barley", "rye", "pasta", "bread"],
            "dairy_free": ["milk", "cheese", "butter", "cream"]
        }

        for pref_key, restricted_items in restricted_ingredients.items():
            if getattr(preferences, pref_key) and any(item.lower() in restricted_items for item in ingredients):
                warnings.append(f"This food contains ingredients that violate your {pref_key.replace('_', '-')} preference.")

        # 🚨 Calorie Limit Check
        if preferences.calorie_target and calories > preferences.calorie_target:
            warnings.append(f"This food exceeds your calorie target of {preferences.calorie_target} kcal.")

    # ✅ Save the food log (with all fields)
    food_log = FoodLog.objects.create(
        food_name=food_name,
        category=category,
        calories=calories,
        ingredients=ingredients,
        serving_size=serving_size,
        cooking_time=cooking_time,
        rating=rating,
        review=review,
    )

    # ✅ Response with warnings (if any)
    response_data = {
        "id": food_log.id,
        "food_name": food_log.food_name,
        "category": food_log.category,
        "calories": food_log.calories,
        "ingredients": food_log.ingredients,
        "serving_size": food_log.serving_size,
        "cooking_time": food_log.cooking_time,
        "rating": food_log.rating,
        "review": food_log.review,
        "message": "Food logged successfully!",
    }

    if warnings:
        response_data["warnings"] = warnings  # Include warnings if there are any

    return Response(response_data, status=status.HTTP_201_CREATED)

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

    # ✅ Get all actual data from the FoodLog model
    data = {
        "id": food_log.id,
        "name": food_log.food_name,
        "serving_size": food_log.serving_size,
        "category": food_log.category,  # ✅ Breakfast, Lunch, or Dinner
        "cooking_time": food_log.cooking_time,  # ✅ Cooking time in minutes
        "rating": food_log.rating,  # ✅ Rating of the food
        "review": food_log.review,  # ✅ User review
        "ingredients": food_log.ingredients,  # ✅ Get actual ingredients
        "calories": food_log.calories,  # ✅ Get actual calorie count
        "timestamp": food_log.timestamp.strftime("%Y-%m-%d %I:%M %p")  # ✅ Formatted date
    }

    # ✅ Check if the food contains ingredients the user wants to avoid
    excluded_ingredients = getattr(preferences, "excluded_ingredients", [])

    if excluded_ingredients:
        for ingredient in data["ingredients"]:
            if ingredient in excluded_ingredients:
                data["warning"] = f"This food contains an ingredient you want to avoid: {ingredient}"
                break  # Stop after finding one warning

    return Response(data, status=status.HTTP_200_OK)

# Edit an existing food intake log
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_food(request, food_id):
    try:
        food_log = FoodLog.objects.get(id=food_id)
    except FoodLog.DoesNotExist:
        return Response({"error": "Food log not found"}, status=status.HTTP_404_NOT_FOUND)

    # 🚨 Step 1: Filter out invalid fields
    allowed_fields = {"food_name", "category", "calories", "ingredients", "serving_size", "cooking_time", "rating", "review"}
    invalid_fields = [field for field in request.data if field not in allowed_fields]

    if invalid_fields:
        return Response({"error": f"Invalid fields in request: {invalid_fields}"}, status=status.HTTP_400_BAD_REQUEST)

    # 🚀 Step 2: Validate and update food log
    serializer = FoodLogSerializer(food_log, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "id": food_log.id,
            "food_name": food_log.food_name,
            "category": food_log.category,
            "calories": food_log.calories,
            "ingredients": food_log.ingredients,
            "serving_size": food_log.serving_size,
            "cooking_time": food_log.cooking_time,
            "rating": food_log.rating,
            "review": food_log.review,
            "timestamp": food_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),
            "message": "Food log successfully updated!"
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete a food intake log
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_food(request, food_id):  # food_id comes from the URL
    try:
        food_log = FoodLog.objects.get(id=food_id)  # Remove user filter
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
        return Response({
            "message": "Preferences updated",
            "preferences": serializer.data  # ✅ No need to remove 'id' and 'user' since they're not included in serializer
        }, status=200)

    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_food_preferences(request):
    try:
        preferences = FoodPreference.objects.get(user=request.user)
        return Response({
            "dietary_preferences": {
                "vegetarian": preferences.vegetarian,
                "vegan": preferences.vegan,
                "gluten_free": preferences.gluten_free,
                "dairy_free": preferences.dairy_free,
                "nut_free": preferences.nut_free
            },
            "excluded_ingredients": preferences.excluded_ingredients,
            "calorie_target": preferences.calorie_target
        })
    except FoodPreference.DoesNotExist:
        return Response({"error": "No dietary preferences found."}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_food(request):
    user = request.user
    query = request.GET.get('query', '').strip().lower()
    preferences = FoodPreference.objects.filter(user=user).first()

    # ✅ If the user searches for "food", return all results
    if query == "food":
        food_logs = FoodLog.objects.all()
    else:
        food_logs = FoodLog.objects.filter(
            Q(food_name__icontains=query) | Q(ingredients__icontains=query)
        )

    results = []
    excluded_ingredients = getattr(preferences, "excluded_ingredients", [])

    for food in food_logs:
        food_data = {
            "food_name": food.food_name,
            "cooking_time": food.cooking_time,
            "ingredients": food.ingredients
        }

        # ✅ Check if food contains an excluded ingredient
        if excluded_ingredients:
            for ingredient in food.ingredients:
                if ingredient in excluded_ingredients:
                    food_data["warning"] = f"This food contains an ingredient you want to avoid: {ingredient}"
                    break  # Stop after finding one warning

        results.append(food_data)

    return Response(results, status=status.HTTP_200_OK)

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
    hydration_logs = HydrationLog.objects.filter(timestamp__date=date.date())
    total_hydration = hydration_logs.aggregate(Sum('amount'))['amount__sum'] or 0

    # Count total food and hydration logs
    total_food_logs = food_logs.count()
    total_hydration_logs = hydration_logs.count()

    # List food items logged
    food_items = [{"name": log.food_name, "calories": log.calories, "category": log.category} for log in food_logs]

    # ✅ Convert hydration logs to a list of dictionaries
    hydration_items = [{"beverage": log.beverage_type, "amount": log.amount} for log in hydration_logs]

    # Response Data
    summary = {
        "date": date_str,
        "total_calories": total_calories,
        "total_hydration": total_hydration,
        "total_food_logs": total_food_logs,  # ✅ Food log count
        "total_hydration_logs": total_hydration_logs,  # ✅ Hydration log count
        "food_items_logged": food_items,
        "hydration_items_logged": hydration_items,  # ✅ Fixed hydration logs
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
def filter_food_category(request):
    category = request.GET.get('category', None)

    if not category:
        return Response({"error": "Category is required."}, status=400)

    filtered_food = FoodLog.objects.filter(category__iexact=category).values(
        'id', 'food_name', 'category'
    )

    return Response(list(filtered_food))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_date(request):
    date_from = request.GET.get('dateFrom', None)
    date_to = request.GET.get('dateTo', None)
    single_date = request.GET.get('date', None)

    try:
        if single_date:
            date_from = date_to = make_aware(datetime.strptime(single_date, "%Y-%m-%d"))
        elif date_from and date_to:
            date_from = make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
            date_to = make_aware(datetime.strptime(date_to, "%Y-%m-%d"))
        else:
            return Response({"error": "Provide either 'date' OR both 'dateFrom' and 'dateTo'."}, status=400)
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    filtered_food = FoodLog.objects.filter(timestamp__date__range=[date_from, date_to])

    response_data = [
        {
            "id": food.id,
            "food_name": food.food_name,
            "timestamp": food.timestamp.strftime("%Y-%m-%d %I:%M %p")  # ✅ Fixed timestamp format
        }
        for food in filtered_food
    ]

    return Response(response_data)


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
    ).order_by('-rating').values('id', 'food_name', 'rating', 'review')  # Sort by highest rating first

    response_data = [
        {
            "id": entry["id"],
            "food_name": entry["food_name"],
            "rating": entry["rating"],
            "review": entry["review"]
        }
        for entry in filtered_food
    ]

    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_cooking_time(request):
    min_time = request.GET.get('minTime')
    max_time = request.GET.get('maxTime')

    # Ensure both minTime and maxTime are provided
    if not min_time or not max_time:
        return Response({"error": "Both minTime and maxTime are required."}, status=400)

    try:
        min_time = int(min_time)
        max_time = int(max_time)
        if min_time < 0 or max_time < 0:
            raise ValueError("Cooking time must be a positive integer.")
    except ValueError:
        return Response({"error": "minTime and maxTime must be valid positive integers."}, status=400)

    # Filter food logs based on cooking time range
    filtered_food = FoodLog.objects.filter(
        cooking_time__gte=min_time,
        cooking_time__lte=max_time
    ).values('id', 'food_name', 'cooking_time')

    return Response(list(filtered_food))

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

    # Log hydration entry
    hydration_log = HydrationLog.objects.create(
        amount=amount,
        beverage_type=beverage_type,
        timestamp=timestamp
    )

    return Response({
        "id": hydration_log.id,  # ✅ Changed from hydrationId to id
        "amount": hydration_log.amount,
        "beverage": hydration_log.beverage_type,  # ✅ Changed from beverageType to beverage
        "timestamp": hydration_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),  # ✅ Fixed timestamp format
        "message": f"Successfully logged {hydration_log.amount}ml of {hydration_log.beverage_type}!"
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_hydration(request, hydration_id):
    try:
        hydration_log = HydrationLog.objects.get(id=hydration_id)
    except HydrationLog.DoesNotExist:
        return Response({"error": "Hydration log not found."}, status=404)

    # 🚨 Step 1: Validate allowed fields
    allowed_fields = {"amount", "beverage", "timestamp"}
    invalid_fields = [field for field in request.data if field not in allowed_fields]

    if invalid_fields:
        return Response({"error": f"Invalid fields in request: {invalid_fields}"}, status=400)

    # 🚀 Step 2: Get the updated values
    amount = request.data.get('amount')
    beverage = request.data.get('beverage')
    timestamp = request.data.get('timestamp')

    # ✅ Validate and update amount
    if amount is not None:
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({"error": "Invalid amount. Please enter a positive value."}, status=400)
            hydration_log.amount = amount
        except ValueError:
            return Response({"error": "Amount must be a number."}, status=400)

    # ✅ Validate and update beverage type
    if beverage:
        valid_beverages = dict(HydrationLog.BEVERAGE_CHOICES).keys()
        if beverage.lower() not in valid_beverages:
            return Response({"error": f"Invalid beverage type. Choose from {list(valid_beverages)}."}, status=400)
        hydration_log.beverage_type = beverage.lower()

    # ✅ Validate and update timestamp
    if timestamp:
        try:
            hydration_log.timestamp = timezone.datetime.fromisoformat(timestamp)
        except ValueError:
            return Response({"error": "Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."}, status=400)

    # ✅ Save updates
    hydration_log.save()

    return Response({
        "id": hydration_log.id,
        "amount": hydration_log.amount,
        "beverage": hydration_log.beverage_type,
        "timestamp": hydration_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),
        "message": "Hydration log successfully updated!"
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_hydration_logs(request):
    hydration_logs = HydrationLog.objects.all().values(
        'id', 'amount', 'beverage_type', 'timestamp'
    )

    # 🛑 If no hydration logs exist, return an error
    if not hydration_logs:
        return Response({"error": "No hydration logs found."}, status=404)

    response_data = [
        {
            "id": log["id"],
            "amount": log["amount"],
            "beverage": log["beverage_type"],
            "timestamp": log["timestamp"].strftime("%Y-%m-%d %I:%M %p")
        }
        for log in hydration_logs
    ]

    return Response(response_data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_hydration(request, hydration_id):  # ✅ Accept hydration_id from the URL
    try:
        hydration_log = HydrationLog.objects.get(id=hydration_id)
        hydration_log.delete()
        return Response({"message": f"Hydration log has been removed successfully!"}, status=200)
    except HydrationLog.DoesNotExist:
        return Response({"error": "Hydration log not found."}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_hydration_logs(request):
    try:
        # Delete all hydration logs
        HydrationLog.objects.all().delete()

        # Reset the primary key sequence (depends on database type)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='food_log_api_hydrationlog';")  # SQLite
            # cursor.execute("ALTER SEQUENCE food_log_api_hydrationlog_id_seq RESTART WITH 1;")  # PostgreSQL

        return Response({"message": "All hydration logs have been cleared and ID reset!"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


from django.db import connection

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_food_logs(request):
    try:
        # Delete all food logs
        FoodLog.objects.all().delete()

        # Reset the primary key sequence (depends on database type)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='food_log_api_foodlog';")  # SQLite
            # cursor.execute("ALTER SEQUENCE food_log_api_foodlog_id_seq RESTART WITH 1;")  # PostgreSQL

        return Response({"message": "All food logs have been cleared and ID reset!"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

