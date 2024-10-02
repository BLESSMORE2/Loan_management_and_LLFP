# Generated by Django 5.1 on 2024-10-02 21:43

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("IFRS9", "0061_collaterallgd_lgdcollateral"),
    ]

    operations = [
        migrations.AddField(
            model_name="dim_run",
            name="date",
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="dim_run",
            name="last_run_skey",
            field=models.BigIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="FCT_Reporting_Lines",
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
                ("n_run_key", models.BigIntegerField(blank=True, null=True)),
                ("fic_mis_date", models.DateField()),
                ("n_account_number", models.CharField(max_length=50, null=True)),
                ("d_acct_start_date", models.DateField(blank=True, null=True)),
                ("d_last_payment_date", models.DateField(blank=True, null=True)),
                ("d_next_payment_date", models.DateField(blank=True, null=True)),
                ("d_maturity_date", models.DateField(blank=True, null=True)),
                ("n_acct_classification", models.IntegerField(blank=True, null=True)),
                ("n_cust_ref_code", models.CharField(max_length=50, null=True)),
                ("n_partner_name", models.CharField(max_length=50)),
                ("n_party_type", models.CharField(max_length=50)),
                (
                    "n_accrual_basis_code",
                    models.CharField(blank=True, max_length=7, null=True),
                ),
                (
                    "n_curr_interest_rate",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=11, null=True
                    ),
                ),
                (
                    "n_effective_interest_rate",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "v_interest_freq_unit",
                    models.CharField(blank=True, max_length=1, null=True),
                ),
                (
                    "v_interest_method",
                    models.CharField(blank=True, max_length=5, null=True),
                ),
                (
                    "n_accrued_interest",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_rate_chg_min",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=10, null=True
                    ),
                ),
                (
                    "n_carrying_amount_ncy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_carrying_amount_rcy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_exposure_at_default_ncy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_exposure_at_default_rcy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_pv_of_cash_flows",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_write_off_amount",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_expected_recovery",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_lifetime_ecl_ncy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_lifetime_ecl_rcy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_12m_ecl_ncy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_12m_ecl_rcy",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                (
                    "n_lgd_percent",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "n_pd_percent",
                    models.DecimalField(decimal_places=4, max_digits=15, null=True),
                ),
                (
                    "n_twelve_months_orig_pd",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "n_lifetime_orig_pd",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "n_twelve_months_pd",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "n_lifetime_pd",
                    models.DecimalField(
                        blank=True, decimal_places=11, max_digits=15, null=True
                    ),
                ),
                (
                    "n_pd_term_structure_skey",
                    models.BigIntegerField(blank=True, null=True),
                ),
                (
                    "n_pd_term_structure_desc",
                    models.CharField(editable=False, max_length=50),
                ),
                (
                    "n_12m_pd_change",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                ("v_amrt_repayment_type", models.CharField(max_length=50, null=True)),
                ("n_remain_no_of_pmts", models.BigIntegerField(blank=True, null=True)),
                ("n_amrt_term", models.IntegerField(blank=True, null=True)),
                (
                    "v_amrt_term_unit",
                    models.CharField(blank=True, max_length=1, null=True),
                ),
                ("v_ccy_code", models.CharField(blank=True, max_length=3, null=True)),
                ("n_delinquent_days", models.IntegerField(blank=True, null=True)),
                ("n_delq_band_code", models.CharField(max_length=50, null=True)),
                ("n_stage_descr", models.CharField(max_length=50, null=True)),
                (
                    "n_curr_ifrs_stage_skey",
                    models.BigIntegerField(blank=True, null=True),
                ),
                (
                    "n_prev_ifrs_stage_skey",
                    models.BigIntegerField(blank=True, null=True),
                ),
                ("d_cooling_start_date", models.DateField(blank=True, null=True)),
                (
                    "n_target_ifrs_stage_skey",
                    models.BigIntegerField(blank=True, null=True),
                ),
                ("n_in_cooling_period_flag", models.BooleanField(default=False)),
                (
                    "n_cooling_period_duration",
                    models.IntegerField(blank=True, null=True),
                ),
                ("n_country", models.CharField(max_length=50, null=True)),
                ("n_segment_skey", models.BigIntegerField(blank=True, null=True)),
                ("n_prod_segment", models.CharField(max_length=255)),
                ("n_prod_code", models.CharField(max_length=50, null=True)),
                ("n_prod_name", models.CharField(max_length=50, null=True)),
                ("n_prod_type", models.CharField(max_length=50, null=True)),
                ("n_prod_desc", models.CharField(max_length=255)),
                ("n_credit_rating_code", models.CharField(max_length=50, null=True)),
                (
                    "n_org_credit_score",
                    models.DecimalField(decimal_places=2, max_digits=5, null=True),
                ),
                ("n_curr_credit_score", models.IntegerField(blank=True, null=True)),
                ("n_acct_rating_movement", models.IntegerField(blank=True, null=True)),
                ("n_party_rating_movement", models.IntegerField(blank=True, null=True)),
                (
                    "n_conditionally_cancel_flag",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "n_collateral_amount",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=22, null=True
                    ),
                ),
                ("n_loan_type", models.CharField(max_length=50, null=True)),
                (
                    "n_pd_term_structure_name",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="IFRS9.fsi_product_segment",
                    ),
                ),
            ],
            options={
                "db_table": "fct_reporting_lines",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("fic_mis_date", "n_account_number", "n_run_key"),
                        name="unique_fct_reporting_lines",
                    )
                ],
            },
        ),
    ]
