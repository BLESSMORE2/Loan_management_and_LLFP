from django.db import connection, transaction
from .save_log import save_log

def cal_lgd_and_loss_rate_for_cash_flows_using_collateral(mis_date):
    """
    Calculate and update LGD (capped at 65%) and then update n_cumulative_loss_rate 
    in fsi_Financial_Cash_Flow_Cal for each account using n_exposure_at_default 
    and n_collateral_amount from FCT_Stage_Determination.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Update n_lgd_percent with LGD capped at 65%
            cursor.execute("""
                UPDATE fsi_Financial_Cash_Flow_Cal AS cf
                JOIN FCT_Stage_Determination AS sd 
                  ON cf.v_account_number = sd.n_account_number
                 AND cf.fic_mis_date = sd.fic_mis_date
                SET cf.n_lgd_percent = GREATEST(
                    0,
                    LEAST(
                        0.65,
                        1 - (sd.n_collateral_amount / cf.n_exposure_at_default)
                    )
                )
                WHERE cf.fic_mis_date = %s
                  AND cf.n_exposure_at_default > 0
                  AND sd.n_collateral_amount IS NOT NULL;
            """, [mis_date])

            # Update n_cumulative_loss_rate using the formula: n_cumulative_impaired_prob * n_lgd_percent
            cursor.execute("""
                UPDATE fsi_Financial_Cash_Flow_Cal
                SET n_cumulative_loss_rate = n_cumulative_impaired_prob * n_lgd_percent
                WHERE fic_mis_date = %s;
            """, [mis_date])

        save_log('calculate_lgd_and_cumulative_loss_rate_for_financial_cash_flow_cal', 'INFO',
                 f"LGD and cumulative loss rate calculations completed for MIS date {mis_date}, with LGD capped at 65%.")
        return 1
    except Exception as e:
        save_log('calculate_lgd_and_cumulative_loss_rate_for_financial_cash_flow_cal', 'ERROR',
                 f"Error calculating LGD and cumulative loss rate for MIS date {mis_date}: {e}")
        return 0
