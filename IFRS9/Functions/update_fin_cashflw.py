from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import FCT_Stage_Determination, fsi_Financial_Cash_Flow_Cal, Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            raise ValueError("No run key is available in the Dim_Run table.")
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        raise ValueError("Dim_Run table is missing.")

def update_financial_cash_flow(fic_mis_date, max_workers=5, batch_size=1000):
    """
    Updates the `n_effective_interest_rate` and `n_lgd_percent` fields in the `fsi_Financial_Cash_Flow_Cal`
    table using values from the `FCT_Stage_Determination` table, based on matching `v_account_number`, `fic_mis_date`,
    and `n_run_skey`.
    """
    try:
        n_run_skey = get_latest_run_skey()
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)
        
        total_cash_flows = cash_flows.count()
        if total_cash_flows == 0:
            save_log('update_financial_cash_flow', 'INFO', f"No financial cash flows found for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}.")
            return '0'

        cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, total_cash_flows, batch_size)]
        updated_records = 0

        def process_batch(batch):
            bulk_updates = []
            for cash_flow in batch:
                try:
                    stage_entry = FCT_Stage_Determination.objects.filter(
                        n_account_number=cash_flow.v_account_number,
                        fic_mis_date=cash_flow.fic_mis_date
                    ).first()

                    if stage_entry:
                        cash_flow.n_effective_interest_rate = stage_entry.n_effective_interest_rate
                        cash_flow.n_lgd_percent = stage_entry.n_lgd_percent
                        bulk_updates.append(cash_flow)
                except Exception as e:
                    save_log('update_financial_cash_flow', 'ERROR', f"Error processing account {cash_flow.v_account_number}: {e}")

            if bulk_updates:
                try:
                    fsi_Financial_Cash_Flow_Cal.objects.bulk_update(bulk_updates, ['n_effective_interest_rate', 'n_lgd_percent'])
                    return len(bulk_updates)
                except Exception as e:
                    save_log('update_financial_cash_flow', 'ERROR', f"Error during bulk update: {e}")
                    return 0
            return 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_batch, batch): batch for batch in cash_flow_batches}

            for future in as_completed(futures):
                try:
                    updated_records += future.result()
                except Exception as exc:
                    save_log('update_financial_cash_flow', 'ERROR', f"Thread encountered an error: {exc}")
                    return '0'

        save_log('update_financial_cash_flow', 'INFO', f"Successfully updated {updated_records} out of {total_cash_flows} financial cash flow records for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}.")
        return '1' if updated_records > 0 else '0'

    except Exception as e:
        save_log('update_financial_cash_flow', 'ERROR', f"Error updating financial cash flow records for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}: {e}")
        return '0'
