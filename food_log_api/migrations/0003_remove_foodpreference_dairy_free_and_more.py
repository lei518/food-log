# Generated by Django 5.1.2 on 2025-03-02 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('food_log_api', '0002_foodlog_category_foodlog_cooking_time_foodlog_rating_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='foodpreference',
            name='dairy_free',
        ),
        migrations.RemoveField(
            model_name='foodpreference',
            name='gluten_free',
        ),
        migrations.AddField(
            model_name='foodpreference',
            name='calorie_target',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='foodpreference',
            name='excluded_ingredients',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='foodpreference',
            name='nut_free',
            field=models.BooleanField(default=False),
        ),
    ]
