import concurrent.futures
from django.db import transaction
from ..models import FSI_Expected_Cashflow, fsi_Financial_Cash_Flow_Cal, Dim_Run
from django.utils import timezone
from .save_log import save_log

def get_next_run_skey():
    """
    Retrieve the next n_run_skey from the Dim_Run table.
    """
    try:
        with transaction.atomic():
            run_key_record, created = Dim_Run.objects.get_or_create(id=1)

            if created:
                run_key_record.latest_run_skey = 1
            else:
                run_key_record.latest_run_skey += 1

            run_key_record.date = timezone.now()
            run_key_record.save()

            return run_key_record.latest_run_skey

    except Exception as e:
        save_log('get_next_run_skey', 'ERROR', f"Error in getting next run skey: {e}")
        return 1  # Default value in case of error


def insert_cash_flow_record(cashflow, run_skey):
    """
    Function to insert a single cash flow record.
    """
    try:
        data_to_insert = {
            'v_account_number': cashflow.v_account_number,
            'd_cash_flow_date': cashflow.d_cash_flow_date,
            'n_run_skey': run_skey,
            'fic_mis_date': cashflow.fic_mis_date,
            'n_principal_run_off': cashflow.n_principal_payment,
            'n_interest_run_off': cashflow.n_interest_payment,
            'n_cash_flow_bucket_id': cashflow.n_cash_flow_bucket,
            'n_cash_flow_amount': cashflow.n_cash_flow_amount,
            'v_ccy_code': cashflow.V_CCY_CODE,
            'n_exposure_at_default': cashflow.n_exposure_at_default
        }

        fsi_Financial_Cash_Flow_Cal.objects.create(**data_to_insert)
        return True

    except Exception as e:
        save_log('insert_cash_flow_record', 'ERROR', f"Error inserting data for account {cashflow.v_account_number} on {cashflow.d_cash_flow_date}: {e}")
        return False


def insert_cash_flow_data(fic_mis_date):
    """
    Function to insert data from FSI_Expected_Cashflow into fsi_Financial_Cash_Flow_Cal with multi-threading.
    """
    try:
        expected_cashflows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date)
        total_selected = expected_cashflows.count()

        if total_selected == 0:
            save_log('insert_cash_flow_data', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date}.")
            return '0'

        total_inserted = 0
        next_run_skey = get_next_run_skey()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(insert_cash_flow_record, cashflow, next_run_skey) for cashflow in expected_cashflows]

            for future in concurrent.futures.as_completed(futures):
                try:
                    if future.result():
                        total_inserted += 1
                except Exception as exc:
                    save_log('insert_cash_flow_data', 'ERROR', f"Error occurred during insertion: {exc}")
                    return '0' 

        update_run_key(next_run_skey)
        save_log('insert_cash_flow_data', 'INFO', f"{total_inserted} out of {total_selected} cash flow records inserted successfully.")
        return '1'

    except Exception as e:
        save_log('insert_cash_flow_data', 'ERROR', f"Error during cash flow insertion process: {e}")
        return '0'


def update_run_key(next_run_skey):
    """
    Update the Dim_Run table with the next run_skey.
    """
    try:
        with transaction.atomic():
            run_key_record, _ = Dim_Run.objects.get_or_create(id=1)
            run_key_record.latest_run_skey = next_run_skey
            run_key_record.date = timezone.now()
            run_key_record.save()

    except Exception as e:
        save_log('update_run_key', 'ERROR', f"Error in updating run key: {e}")
