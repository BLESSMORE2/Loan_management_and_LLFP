# Generated by Django 5.1 on 2024-09-30 21:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "IFRS9",
            "0055_remove_fsi_financial_cash_flow_cal_n_cash_flow_fwd_pv_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="fsi_financial_cash_flow_cal",
            name="n_per_period_loss_rate",
        ),
    ]
