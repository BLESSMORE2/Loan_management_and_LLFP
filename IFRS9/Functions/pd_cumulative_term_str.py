from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.models import Sum
from ..models import FCT_Stage_Determination, fsi_Financial_Cash_Flow_Cal, FSI_PD_Interpolated, Dim_Run
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

def update_cash_flow_with_pd_buckets(fic_mis_date, max_workers=5, batch_size=1000):
    """
    Updates cash flow records with PD buckets using bulk updates and multi-threading.
    """
    try:
        n_run_skey = get_latest_run_skey()
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

        if not cash_flows.exists():
            save_log('update_cash_flow_with_pd_buckets', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
            return 0

        total_updated_records = 0

        def process_batch(batch):
            try:
                updates = []
                for cash_flow in batch:
                    account_data = FCT_Stage_Determination.objects.filter(
                        n_account_number=cash_flow.v_account_number,
                        fic_mis_date=fic_mis_date
                    ).first()

                    if account_data:
                        pd_records = FSI_PD_Interpolated.objects.filter(
                            v_pd_term_structure_id=account_data.n_pd_term_structure_skey,
                            fic_mis_date=fic_mis_date,
                        )

                        if pd_records.exists():
                            pd_record = None
                            if pd_records.first().v_pd_term_structure_type == 'R':
                                pd_record = pd_records.filter(
                                    v_int_rating_code=account_data.n_credit_rating_code,
                                    v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                                ).first()
                            elif pd_records.first().v_pd_term_structure_type == 'D':
                                pd_record = pd_records.filter(
                                    v_delq_band_code=account_data.n_delq_band_code,
                                    v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                                ).first()

                            if pd_record:
                                cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * account_data.n_lgd_percent
                                cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

                                months_to_12m = get_buckets_for_12_months(account_data.v_amrt_term_unit)
                                if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
                                    cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
                                else:
                                    pd_record_12 = pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
                                    if pd_record_12:
                                        cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

                                updates.append(cash_flow)

                if updates:
                    fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                        updates, 
                        ['n_cumulative_loss_rate', 'n_cumulative_impaired_prob', 'n_12m_cumulative_pd']
                    )
                return len(updates)

            except Exception as e:
                save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Error updating batch: {e}")
                return 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            batch = []
            for cash_flow in cash_flows.iterator(chunk_size=batch_size):
                batch.append(cash_flow)
                if len(batch) >= batch_size:
                    futures.append(executor.submit(process_batch, batch))
                    batch = []

            if batch:
                futures.append(executor.submit(process_batch, batch))

            for future in as_completed(futures):
                try:
                    total_updated_records += future.result()
                except Exception as exc:
                    save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Thread encountered an error: {exc}")
                    return 0

        save_log('update_cash_flow_with_pd_buckets', 'INFO', f"Updated {total_updated_records} records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}.")
        return 1 if total_updated_records > 0 else 0

    except Exception as e:
        save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Error updating cash flow for fic_mis_date {fic_mis_date}: {e}")
        return 0

def get_buckets_for_12_months(v_amrt_term_unit):
    """
    Returns the number of buckets required to reach 12 months based on the amortization term unit.
    """
    term_unit_to_buckets = {
        'M': 12,
        'Q': 4,
        'H': 2,
        'Y': 1
    }
    return term_unit_to_buckets.get(v_amrt_term_unit, 12)
