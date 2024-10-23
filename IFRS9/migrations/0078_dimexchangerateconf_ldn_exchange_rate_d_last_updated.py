# Generated by Django 5.1 on 2024-10-23 13:12

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0077_currencycode_reportingcurrency"),
    ]

    operations = [
        migrations.CreateModel(
            name="DimExchangeRateConf",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("EXCHANGE_RATE_API_KEY", models.CharField(max_length=255)),
                ("use_on_exchange_rates", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "dim_exchange_rate_conf",
            },
        ),
        migrations.AddField(
            model_name="ldn_exchange_rate",
            name="d_last_updated",
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
