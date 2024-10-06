from django.db import transaction
from concurrent.futures import ThreadPoolExecutor
from ..models import FCT_Stage_Determination, fsi_Financial_Cash_Flow_Cal,Dim_Run

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
    
# Function to fetch and update n_effective_interest_rate and n_lgd_percent from FCT_Stage_Determination
def update_financial_cash_flow(fic_mis_date, max_workers=5, batch_size=1000):
    """
    This function updates the `n_effective_interest_rate` and `n_lgd_percent` fields in the `fsi_Financial_Cash_Flow_Cal`
    table using values from the `FCT_Stage_Determination` table, based on matching `v_account_number`, `fic_mis_date`,
    and `n_run_skey`.
    
    :param fic_mis_date: The financial MIS date used for filtering the records.
    :param max_workers: Maximum number of threads for parallel processing.
    :param batch_size: Size of each batch for processing records in bulk updates.
    """
    try:
        n_run_skey = get_latest_run_skey()
        # Fetch all cash flow entries for the given fic_mis_date and n_run_skey
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)
        
        if cash_flows.count() == 0:
            print(f"No financial cash flows found for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}.")
            return '0'  # Return '0' if no records are found

        # Process cash flows in batches
        cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, cash_flows.count(), batch_size)]
        print(f"Processing {cash_flows.count()} cash flow records in {len(cash_flow_batches)} batches...")

        def process_batch(batch):
            bulk_updates = []

            for cash_flow in batch:
                try:
                    # Fetch the corresponding stage determination record
                    stage_entry = FCT_Stage_Determination.objects.filter(
                        n_account_number=cash_flow.v_account_number,
                        fic_mis_date=cash_flow.fic_mis_date
                    ).first()

                    if stage_entry:
                        # Update n_effective_interest_rate and n_lgd_percent in cash flow entry
                        cash_flow.n_effective_interest_rate = stage_entry.n_effective_interest_rate
                        cash_flow.n_lgd_percent = stage_entry.n_lgd_percent
                        bulk_updates.append(cash_flow)
                    else:
                        print(f"Stage entry not found for account {cash_flow.v_account_number} on fic_mis_date {cash_flow.fic_mis_date}")

                except Exception as e:
                    print(f"Error processing account {cash_flow.v_account_number}: {e}")

            # Bulk update the batch
            if bulk_updates:
                try:
                    fsi_Financial_Cash_Flow_Cal.objects.bulk_update(bulk_updates, ['n_effective_interest_rate', 'n_lgd_percent'])
                    print(f"Successfully updated {len(bulk_updates)} records.")
                except Exception as e:
                    print(f"Error during bulk update: {e}")

        # Use multi-threading to process batches in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_batch, batch) for batch in cash_flow_batches]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()
                except Exception as exc:
                    print(f"Thread encountered an error: {exc}")
                    return '0'  # Return '0' if any thread encounters an error

        print(f"Successfully processed {cash_flows.count()} financial cash flow records for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}.")
        return 1  # Return '1' on successful completion

    except Exception as e:
        print(f"Error updating financial cash flow records for fic_mis_date {fic_mis_date} and n_run_skey {n_run_skey}: {e}")
        return 0  # Return '0' in case of any exception


