# Generated by Django 5.1.2 on 2025-03-02 15:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('food_log_api', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='foodlog',
            name='category',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='foodlog',
            name='cooking_time',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='foodlog',
            name='rating',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='foodlog',
            name='review',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='FoodPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vegetarian', models.BooleanField(default=False)),
                ('gluten_free', models.BooleanField(default=False)),
                ('dairy_free', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(
            name='Rating',
        ),
    ]
