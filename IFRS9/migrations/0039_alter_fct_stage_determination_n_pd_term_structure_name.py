# Generated by Django 5.1 on 2024-09-27 07:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "IFRS9",
            "0038_remove_ldn_customer_rating_detail_v_credit_reason_code_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="fct_stage_determination",
            name="n_pd_term_structure_name",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="IFRS9.fsi_product_segment",
            ),
        ),
    ]
