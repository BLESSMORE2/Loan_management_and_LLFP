# Generated by Django 5.1 on 2024-11-19 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0016_alter_ldn_customer_rating_detail_unique_together_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ldn_customer_rating_detail",
            name="fic_mis_date",
            field=models.DateField(null=True),
        ),
    ]
