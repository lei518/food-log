from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils.dateparse import parse_date
from datetime import datetime
from django.utils.timezone import make_aware, now, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from collections import Counter
from django.db.models import Q, Sum, Count
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import FoodLog, HydrationLog, FoodPreference
from .serializers import FoodLogSerializer, HydrationLogSerializer, FoodPreferenceSerializer

PROTEIN_RICH = {
    "chicken", "beef", "fish", "tofu", "eggs", "beans", "lentils", "turkey",
    "pork", "shrimp", "salmon", "tuna", "cottage cheese", "Greek yogurt",
    "cheese", "milk", "quinoa", "seitan", "edamame", "chickpeas", "almonds",
    "walnuts", "peanut butter", "pumpkin seeds", "sunflower seeds"
}
CARBS_RICH = {
    "rice", "pasta", "bread", "potatoes", "noodles", "cereal", "oats",
    "corn", "quinoa", "tortilla", "sweet potatoes", "bagels", "croissants",
    "crackers", "granola", "pancakes", "waffles", "muffins", "barley",
    "couscous", "pretzels", "popcorn"
}
FIBER_RICH = {
    "broccoli", "carrots", "spinach", "beans", "whole grains", "nuts",
    "kale", "brussels sprouts", "avocado", "chia seeds", "flaxseeds",
    "raspberries", "blackberries", "pears", "apples", "oranges",
    "bananas", "oatmeal", "lentils", "peas", "quinoa", "beets",
    "sweet potatoes", "almonds", "cashews", "walnuts"
}

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "User already exists"}, status=400)

    user = User.objects.create(username=username, password=make_password(password))

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    return Response({
        "message": "Registration successful",
        "access_token": access_token,
        "refresh_token": str(refresh)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_food(request):
    try:
        preferences = FoodPreference.objects.get(user=request.user)
    except FoodPreference.DoesNotExist:
        preferences = None

    required_fields = ["food_name", "category", "calories", "ingredients", "serving_size", "cooking_time", "rating", "review"]
    for field in required_fields:
        if not request.data.get(field):
            return Response({"error": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        food_data = {
            "user": request.user,
            "food_name": request.data.get("food_name"),
            "category": request.data.get("category"),
            "calories": int(request.data.get("calories")),
            "ingredients": request.data.get("ingredients"),
            "serving_size": request.data.get("serving_size"),
            "cooking_time": int(request.data.get("cooking_time")),
            "rating": int(request.data.get("rating")) if request.data.get("rating") else None,
            "review": request.data.get("review"),
        }
    except ValueError:
        return Response({"error": "Invalid data type for numeric fields (calories, cooking_time, rating)."}, status=status.HTTP_400_BAD_REQUEST)

    warnings = []

    if preferences:
        restricted_ingredients = {
            "vegetarian": [
                "chicken", "beef", "pork", "fish", "seafood", "lamb", "turkey", "duck",
                "bacon", "sausage", "ham", "gelatin", "anchovies", "oyster sauce"
            ],

            "vegan": [
                "chicken", "beef", "pork", "fish", "seafood", "lamb", "turkey", "duck",
                "milk", "cheese", "egg", "butter", "yogurt", "cream", "honey", "whey",
                "casein", "lard", "gelatin", "mayonnaise"
            ],

            "nut_free": [
                "peanut", "almond", "cashew", "hazelnut", "walnut", "pecan", "pistachio",
                "macadamia", "brazil nut", "chestnut", "nut butter", "praline", "marzipan"
            ],

            "gluten_free": [
                "wheat", "barley", "rye", "pasta", "bread", "flour tortillas", "crackers",
                "croissants", "beer", "couscous", "semolina", "farro", "bulgur",
                "wheat-based soy sauce"
            ],

            "dairy_free": [
                "milk", "cheese", "butter", "cream", "yogurt", "ice cream", "whey",
                "casein", "ghee", "sour cream", "condensed milk", "buttermilk",
                "milk chocolate"
            ]
        }

        for pref, restricted_items in restricted_ingredients.items():
            if getattr(preferences, pref, False) and any(item.lower() in restricted_items for item in food_data["ingredients"]):
                warnings.append(f"This food contains ingredients that violate your {pref.replace('_', '-')} preference.")

        if preferences.excluded_ingredients:
            excluded_items = [item.lower() for item in preferences.excluded_ingredients]
            found_exclusions = [item for item in food_data["ingredients"] if item.lower() in excluded_items]

            if found_exclusions:
                warnings.append(f"This food contains ingredients you want to avoid: {', '.join(found_exclusions)}.")

        if preferences.calorie_target and food_data["calories"] > preferences.calorie_target:
            warnings.append(f"This food exceeds your calorie target of {preferences.calorie_target} kcal.")

    try:
        food_log = FoodLog.objects.create(**food_data)
    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response_data = {
        "user_food_id": food_log.user_food_id,
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
        response_data["warnings"] = warnings

    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_food_logs(request):
    try:
        food_logs = FoodLog.objects.filter(user=request.user)
        if not food_logs.exists():
            return Response({"message": "No food logs found. Start logging your food intake!"}, status=status.HTTP_200_OK)

        serializer = FoodLogSerializer(food_logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_log_details(request, user_food_id):
    try:
        food_log = get_object_or_404(FoodLog, user_food_id=user_food_id, user=request.user)
        preferences = FoodPreference.objects.filter(user=request.user).first()

        data = {
            "user_food_id": food_log.user_food_id,
            "food_name": food_log.food_name,
            "serving_size": food_log.serving_size,
            "category": food_log.category,
            "cooking_time": food_log.cooking_time,
            "rating": food_log.rating,
            "review": food_log.review,
            "ingredients": food_log.ingredients,
            "calories": food_log.calories,
            "timestamp": food_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),
        }

        if preferences:
            excluded_ingredients = getattr(preferences, "excluded_ingredients", [])
            for ingredient in data["ingredients"]:
                if ingredient in excluded_ingredients:
                    data["warning"] = f"This food contains an ingredient you want to avoid: {ingredient}"
                    break

        return Response(data, status=status.HTTP_200_OK)

    except Http404:
        return Response({"error": "Food log not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_food(request, user_food_id):
    try:
        food_log = get_object_or_404(FoodLog, user_food_id=user_food_id, user=request.user)

        allowed_fields = {"food_name", "category", "calories", "ingredients", "serving_size", "cooking_time", "rating", "review"}
        invalid_fields = [field for field in request.data if field not in allowed_fields]

        if invalid_fields:
            return Response({"error": f"Invalid fields in request: {invalid_fields}"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FoodLogSerializer(food_log, data=request.data, partial=True)

        if serializer.is_valid():
            updated_food = serializer.validated_data
            serializer.save()

            try:
                preferences = FoodPreference.objects.get(user=request.user)
            except FoodPreference.DoesNotExist:
                preferences = None

            warnings = []

            if preferences:
                restricted_ingredients = {
                    "vegetarian": [
                        "chicken", "beef", "pork", "fish", "seafood", "lamb", "turkey", "duck",
                        "bacon", "sausage", "ham", "gelatin", "anchovies", "oyster sauce"
                    ],

                    "vegan": [
                        "chicken", "beef", "pork", "fish", "seafood", "lamb", "turkey", "duck",
                        "milk", "cheese", "egg", "butter", "yogurt", "cream", "honey", "whey",
                        "casein", "lard", "gelatin", "mayonnaise"
                    ],

                    "nut_free": [
                        "peanut", "almond", "cashew", "hazelnut", "walnut", "pecan", "pistachio",
                        "macadamia", "brazil nut", "chestnut", "nut butter", "praline", "marzipan"
                    ],

                    "gluten_free": [
                        "wheat", "barley", "rye", "pasta", "bread", "flour tortillas", "crackers",
                        "croissants", "beer", "couscous", "semolina", "farro", "bulgur",
                        "wheat-based soy sauce"
                    ],

                    "dairy_free": [
                        "milk", "cheese", "butter", "cream", "yogurt", "ice cream", "whey",
                        "casein", "ghee", "sour cream", "condensed milk", "buttermilk",
                        "milk chocolate"
                    ]
                }

                updated_ingredients = updated_food.get("ingredients", food_log.ingredients)
                for pref, restricted_items in restricted_ingredients.items():
                    if getattr(preferences, pref, False) and any(item.lower() in restricted_items for item in updated_ingredients):
                        warnings.append(f"This food contains ingredients that violate your {pref.replace('_', '-')} preference.")

                found_exclusions = [item for item in updated_ingredients if
                item.lower() in [e.lower() for e in preferences.excluded_ingredients]]
                if found_exclusions:
                    warnings.append(f"This food contains ingredients you want to avoid: {', '.join(found_exclusions)}.")

                updated_calories = updated_food.get("calories", food_log.calories)  # Get updated or existing calories
                if preferences.calorie_target and updated_calories > preferences.calorie_target:
                    warnings.append(f"This food exceeds your calorie target of {preferences.calorie_target} kcal.")

            response_data = {
                "user_food_id": food_log.user_food_id,
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
            }

            if warnings:
                response_data["warnings"] = warnings

            return Response(response_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Http404:
        return Response({"error": "Food log not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_food(request, user_food_id):
    try:
        food_log = get_object_or_404(FoodLog, user_food_id=user_food_id, user=request.user)
        food_log.delete()
        return Response({"message": "Food log deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    except Http404:
        return Response({"error": "Food log not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_food_preferences(request):
    try:
        user = request.user
        preferences, created = FoodPreference.objects.get_or_create(user=user)
        serializer = FoodPreferenceSerializer(preferences, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Preferences updated successfully.",
                "preferences": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({"error": "Invalid data provided.", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_food_preferences(request):
    try:
        preferences = FoodPreference.objects.get(user=request.user)

        return Response({
            "message": "User dietary preferences retrieved successfully.",
            "dietary_preferences": {
                "vegetarian": preferences.vegetarian,
                "vegan": preferences.vegan,
                "nut_free": preferences.nut_free,
                "gluten_free": preferences.gluten_free,
                "dairy_free": preferences.dairy_free,
            },
            "excluded_ingredients": preferences.excluded_ingredients or [],
            "calorie_target": preferences.calorie_target if preferences.calorie_target else "No target set"
        }, status=status.HTTP_200_OK)

    except FoodPreference.DoesNotExist:
        return Response({
            "message": "No dietary preferences found. Please set your preferences first.",
            "dietary_preferences": None,
            "excluded_ingredients": [],
            "calorie_target": "No target set"
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_food(request):
    try:
        user = request.user
        query = request.GET.get('query', '').strip().lower()
        preferences = FoodPreference.objects.filter(user=user).first()

        if not query:
            return Response({"error": "Please provide a search query."}, status=status.HTTP_400_BAD_REQUEST)

        if query == "food":
            food_logs = FoodLog.objects.filter(user=user)
        else:
            food_logs = FoodLog.objects.filter(
                Q(food_name__icontains=query) | Q(ingredients__icontains=query),
                user=user
            )

        if not food_logs.exists():
            return Response({"message": "No matching food logs found."}, status=status.HTTP_404_NOT_FOUND)

        results = []
        excluded_ingredients = getattr(preferences, "excluded_ingredients", [])

        for food in food_logs:
            food_data = {
                "food_name": food.food_name,
                "serving_size": food.serving_size,
                "category": food.category,
                "cooking_time": food.cooking_time,
                "rating": food.rating,
                "review": food.review,
                "ingredients": food.ingredients,
                "calories": food.calories,
            }

            if excluded_ingredients:
                for ingredient in food.ingredients:
                    if ingredient in excluded_ingredients:
                        food_data["warning"] = f"This food contains an ingredient you want to avoid: {ingredient}"
                        break

            results.append(food_data)

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_summary(request):
    try:
        user = request.user
        date_str = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))

        try:
            date = make_aware(datetime.strptime(date_str, '%Y-%m-%d'))
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        food_logs = FoodLog.objects.filter(user=user, timestamp__date=date.date())
        total_calories = food_logs.aggregate(Sum('calories'))['calories__sum'] or 0

        category_breakdown = {}
        for log in food_logs:
            category = log.category or "Uncategorized"
            category_breakdown[category] = category_breakdown.get(category, 0) + 1

        hydration_logs = HydrationLog.objects.filter(user=user, timestamp__date=date.date())
        total_hydration = hydration_logs.aggregate(Sum('amount'))['amount__sum'] or 0
        total_food_logs = food_logs.count()
        total_hydration_logs = hydration_logs.count()
        food_items = [{"name": log.food_name, "calories": log.calories, "category": log.category} for log in food_logs]
        hydration_items = [{"beverage": log.beverage_type, "amount": log.amount} for log in hydration_logs]

        if total_food_logs == 0 and total_hydration_logs == 0:
            return Response({"message": "No food or hydration logs found for this date."}, status=status.HTTP_200_OK)

        summary = {
            "date": date_str,
            "total_calories": total_calories,
            "total_hydration": total_hydration,
            "total_food_logs": total_food_logs,
            "total_hydration_logs": total_hydration_logs,
            "food_items_logged": food_items,
            "hydration_items_logged": hydration_items,
        }

        return Response(summary, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nutritional_insights(request):
    try:
        user = request.user
        one_week_ago = now() - timedelta(days=7)
        food_logs = FoodLog.objects.filter(user=user, timestamp__gte=one_week_ago)

        if not food_logs.exists():
            return Response({"message": "No food logs found in the past week."}, status=status.HTTP_404_NOT_FOUND)

        protein_count = 0
        carb_count = 0
        fiber_count = 0

        for log in food_logs:
            if log.ingredients:
                for ingredient in log.ingredients:
                    ingredient = ingredient.lower()
                    if ingredient in PROTEIN_RICH:
                        protein_count += 1
                    if ingredient in CARBS_RICH:
                        carb_count += 1
                    if ingredient in FIBER_RICH:
                        fiber_count += 1

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
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_category(request):
    try:
        category = request.GET.get('category', '').strip()

        if not category:
            return Response({"error": "Category is required."}, status=status.HTTP_400_BAD_REQUEST)

        filtered_food = FoodLog.objects.filter(
            user=request.user,
            category__iexact=category
        ).values('user_food_id', 'food_name', 'category')

        if not filtered_food.exists():
            return Response({"message": f"No food logs found for category: {category}"}, status=status.HTTP_404_NOT_FOUND)

        return Response(list(filtered_food), status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

            if date_from > date_to:
                return Response({"error": "'dateFrom' cannot be later than 'dateTo'."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"error": "Provide either 'date' OR both 'dateFrom' and 'dateTo'."},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST
        )

    filtered_food = FoodLog.objects.filter(user=request.user, timestamp__date__range=[date_from, date_to])

    if not filtered_food.exists():
        return Response(
            {"message": f"No food logs found for the given date range ({date_from.date()} - {date_to.date()})."},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = [
        {
            "user_food_id": food.user_food_id,
            "food_name": food.food_name,
            "timestamp": food.timestamp.strftime("%Y-%m-%d %I:%M %p")
        }
        for food in filtered_food
    ]

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def filter_food_by_rating(request):
    min_rating = request.GET.get('min_rating')

    if not min_rating:
        return Response({"error": "min_rating is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        min_rating = int(min_rating)
        if not (1 <= min_rating <= 5):
            return Response({"error": "min_rating must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return Response({"error": "min_rating must be a valid integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

    filtered_food = FoodLog.objects.filter(user=request.user, rating__gte=min_rating).order_by('-rating')

    if not filtered_food.exists():
        return Response(
            {"message": f"No food logs found with a rating of {min_rating} or higher."},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = [
        {
            "user_food_id": food.user_food_id,
            "food_name": food.food_name,
            "rating": food.rating,
            "review": food.review
        }
        for food in filtered_food
    ]

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_cooking_time(request):
    min_time = request.GET.get('min_time')
    max_time = request.GET.get('max_time')

    if min_time is None or max_time is None:
        return Response({"error": "Both min_time and max_time are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        min_time = int(min_time)
        max_time = int(max_time)
        if min_time < 0 or max_time < 0:
            return Response({"error": "Cooking time must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)
        if min_time > max_time:
            return Response({"error": "min_time cannot be greater than max_time."}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return Response({"error": "min_time and max_time must be valid positive integers."}, status=status.HTTP_400_BAD_REQUEST)

    filtered_food = FoodLog.objects.filter(
        user=request.user, cooking_time__gte=min_time, cooking_time__lte=max_time
    ).order_by('cooking_time')

    if not filtered_food.exists():
        return Response(
            {"message": f"No food logs found with a cooking time between {min_time} and {max_time} minutes."},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = [
        {
            "user_food_id": food.user_food_id,
            "food_name": food.food_name,
            "cooking_time": food.cooking_time
        }
        for food in filtered_food
    ]

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_hydration(request):
    try:
        amount = request.data.get("amount")
        beverage_type = request.data.get("beverage_type", "").strip()
        timestamp = request.data.get("timestamp", timezone.now())

        if not amount:
            return Response({"error": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
            if amount <= 0:
                return Response({"error": "Invalid amount. Please enter a positive value."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

        if not beverage_type:
            return Response({"error": "Beverage type cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        last_log = HydrationLog.objects.filter(user=request.user).order_by('-user_hydration_id').first()
        user_hydration_id = (last_log.user_hydration_id + 1) if last_log else 1
        hydration_log = HydrationLog.objects.create(
            user=request.user,
            user_hydration_id=user_hydration_id,
            amount=amount,
            beverage_type=beverage_type,
            timestamp=timestamp
        )

        return Response({
            "user_hydration_id": hydration_log.user_hydration_id,
            "user": request.user.username,
            "amount": hydration_log.amount,
            "beverage": hydration_log.beverage_type,
            "timestamp": hydration_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),
            "message": f"Successfully logged {hydration_log.amount}ml of {hydration_log.beverage_type}!"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_hydration(request, user_hydration_id):

    hydration_log = get_object_or_404(HydrationLog, user_hydration_id=user_hydration_id, user=request.user)
    allowed_fields = {"amount", "beverage_type", "timestamp"}
    invalid_fields = [field for field in request.data if field not in allowed_fields]

    if invalid_fields:
        return Response(
            {"error": f"Invalid fields in request: {invalid_fields}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    amount = request.data.get('amount')
    beverage_type = request.data.get('beverage_type')
    timestamp = request.data.get('timestamp')

    if amount is not None:
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({"error": "Invalid amount. Please enter a positive value."}, status=status.HTTP_400_BAD_REQUEST)
            hydration_log.amount = amount
        except ValueError:
            return Response({"error": "Amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

    if beverage_type:
        hydration_log.beverage_type = beverage_type.strip()

    if timestamp:
        try:
            hydration_log.timestamp = timezone.datetime.fromisoformat(timestamp)
        except ValueError:
            return Response(
                {"error": "Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."},
                status=status.HTTP_400_BAD_REQUEST
            )

    hydration_log.save()

    return Response({
        "user_hydration_id": hydration_log.user_hydration_id,
        "amount": hydration_log.amount,
        "beverage": hydration_log.beverage_type,
        "timestamp": hydration_log.timestamp.strftime("%Y-%m-%d %I:%M %p"),
        "message": "Hydration log successfully updated!"
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_hydration(request, user_hydration_id):
    try:
        hydration_log = get_object_or_404(HydrationLog, user_hydration_id=user_hydration_id, user=request.user)
        hydration_log.delete()

        return Response(
            {"message": "Hydration log has been removed successfully!"},
            status=status.HTTP_204_NO_CONTENT
        )

    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred while deleting the hydration log. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_hydration_logs(request):
    try:
        hydration_logs = HydrationLog.objects.filter(user=request.user)
        if not hydration_logs.exists():
            return Response(
                {"message": "No hydration logs found. Start logging your hydration intake!"},
                status=status.HTTP_200_OK
            )

        response_data = [
            {
                "user_hydration_id": log.user_hydration_id,
                "amount": log.amount,
                "beverage": log.beverage_type,
                "timestamp": log.timestamp.strftime("%Y-%m-%d %I:%M %p")
            }
            for log in hydration_logs
        ]

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred while retrieving hydration logs. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_hydration_logs(request):
    try:
        deleted_count, _ = HydrationLog.objects.filter(user=request.user).delete()

        if deleted_count == 0:
            return Response(
                {"message": "No hydration logs found to clear. You're all set!"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"message": f"Successfully cleared {deleted_count} hydration log(s)!"},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred while clearing hydration logs. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_food_logs(request):
    try:
        deleted_count, _ = FoodLog.objects.filter(user=request.user).delete()

        if deleted_count == 0:
            return Response(
                {"message": "No food logs found to clear. You're all set!"},
                status=status.HTTP_200_OK
            )

        return Response(
            {"message": f"Successfully cleared {deleted_count} food log(s)!"},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred while clearing food logs. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )