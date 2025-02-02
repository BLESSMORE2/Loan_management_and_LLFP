# Generated by Django 5.1 on 2024-11-09 12:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0012_alter_fct_reporting_lines_n_pd_term_structure_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fct_reporting_lines",
            name="n_pd_term_structure_name",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="IFRS9.fsi_product_segment",
            ),
        ),
    ]
