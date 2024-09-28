# Generated by Django 5.1 on 2024-09-28 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0050_alter_fct_stage_determination_n_delq_band_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="fsi_expected_cashflow",
            name="management_fee_added",
            field=models.DecimalField(decimal_places=2, default=1188, max_digits=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="fct_stage_determination",
            name="n_accrual_basis_code",
            field=models.CharField(blank=True, max_length=7, null=True),
        ),
        migrations.CreateModel(
            name="fsi_Financial_Cash_Flow_Cal",
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
                ("n_run_skey", models.BigIntegerField(default=1, null=True)),
                ("v_account_number", models.CharField(max_length=20)),
                ("d_cash_flow_date", models.DateField()),
                ("fic_mis_date", models.DateField()),
                (
                    "n_principal_run_off",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_interest_run_off",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                ("n_cash_flow_bucket_id", models.IntegerField(null=True)),
                (
                    "n_cash_flow_amount",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_cumulative_loss_rate",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_expected_cash_flow_rate",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_discount_rate",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_discount_factor",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_expected_cash_flow",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_effective_interest_rate",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_lgd_percent",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_expected_cash_flow_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_exposure_at_default",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_forward_expected_loss",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_forward_expected_loss_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                ("n_interest_rate_cd", models.BigIntegerField(null=True)),
                ("v_ccy_code", models.CharField(max_length=3, null=True)),
                (
                    "n_cash_shortfall",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_per_period_loss_rate",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_cash_shortfall_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_per_period_loss_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_cash_flow_fwd_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_forward_exposure_amt",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_per_period_impaired_prob",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_cumulative_impaired_prob",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_12m_per_period_pd",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_12m_cumulative_pd",
                    models.DecimalField(decimal_places=11, max_digits=15, null=True),
                ),
                (
                    "n_12m_exp_cash_flow",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_12m_exp_cash_flow_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_12m_cash_shortfall",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_12m_cash_shortfall_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_12m_fwd_expected_loss",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
                (
                    "n_12m_fwd_expected_loss_pv",
                    models.DecimalField(decimal_places=3, max_digits=22, null=True),
                ),
            ],
            options={
                "db_table": "fsi_Financial_Cash_Flow_Cal",
                "unique_together": {
                    (
                        "v_account_number",
                        "d_cash_flow_date",
                        "fic_mis_date",
                        "n_run_skey",
                    )
                },
            },
        ),
    ]
