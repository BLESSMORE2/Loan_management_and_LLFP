# Generated by Django 5.1 on 2024-10-30 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0003_alter_ldn_financial_instrument_unique_together_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ldn_financial_instrument",
            name="v_account_number",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name="ldn_financial_instrument",
            unique_together={("fic_mis_date", "v_account_number")},
        ),
    ]
