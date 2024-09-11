# Generated by Django 5.1 on 2024-09-10 20:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0022_fsi_product_segment_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fsi_product_segment",
            name="v_prod_desc",
            field=models.TextField(max_length=255),
        ),
        migrations.AlterField(
            model_name="fsi_product_segment",
            name="v_prod_segment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="IFRS9.ldn_bank_product_info",
            ),
        ),
        migrations.AlterField(
            model_name="fsi_product_segment",
            name="v_prod_type",
            field=models.CharField(max_length=255),
        ),
    ]
