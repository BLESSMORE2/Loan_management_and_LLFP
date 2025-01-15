# Generated by Django 5.1 on 2025-01-15 07:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0030_alter_fct_reporting_lines_options_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ldn_financial_instrument",
            options={
                "permissions": [
                    ("can_load_data", "Can load data"),
                    ("can_view_edit_data", "Can view data"),
                ]
            },
        ),
    ]
