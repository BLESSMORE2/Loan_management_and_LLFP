# Generated by Django 5.1 on 2024-09-11 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "IFRS9",
            "0027_rename_n_acct_risk_score_ldn_financial_instrument_n_curr_credit_score_and_more",
        ),
    ]

    operations = [
        migrations.RenameField(
            model_name="fct_stage_determination",
            old_name="n_acct_classification_skey",
            new_name="n_acct_classification",
        ),
        migrations.RenameField(
            model_name="ldn_financial_instrument",
            old_name="n_curr_credit_score",
            new_name="v_curr_credit_score",
        ),
        migrations.RenameField(
            model_name="ldn_financial_instrument",
            old_name="v_credit_score",
            new_name="v_org_credit_score",
        ),
        migrations.RemoveField(
            model_name="fct_stage_determination",
            name="n_country_skey",
        ),
        migrations.RemoveField(
            model_name="fct_stage_determination",
            name="n_delq_impaired_state_skey",
        ),
        migrations.RemoveField(
            model_name="fct_stage_determination",
            name="n_prod_type_skey",
        ),
        migrations.AddField(
            model_name="fct_stage_determination",
            name="n_country",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="fct_stage_determination",
            name="n_org_credit_score",
            field=models.DecimalField(decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="fct_stage_determination",
            name="n_prod_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="fct_stage_determination",
            name="n_prod_type",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="fct_stage_determination",
            name="n_stage_descr",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="fct_stage_determination",
            name="n_prod_code",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
