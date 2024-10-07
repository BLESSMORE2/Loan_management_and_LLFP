from django.db import transaction
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import FSI_Expected_Cashflow, Ldn_Financial_Instrument
from .save_log import save_log

def calculate_accrued_interest(principal, interest_rate, days, day_count_ind):
    """
    Calculate accrued interest using the given day count convention.
    """
    day_count = Decimal(365)
    if day_count_ind == '30/360':
        day_count = Decimal(360)
    elif day_count_ind == '30/365':
        day_count = Decimal(365)
    
    accrued_interest = principal * (interest_rate / Decimal(100)) * (Decimal(days) / day_count)
    return accrued_interest

def calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date):
    """
    Calculate both EAD (Exposure at Default) and Accrued Interest for a specific cash flow bucket.
    """
    try:
        n_balance = Decimal(cash_flow.n_balance or 0)
        n_exposure_at_default = n_balance

        if loan.n_curr_interest_rate:
            interest_rate = Decimal(loan.n_curr_interest_rate)
            days_since_last_payment = (cash_flow.d_cash_flow_date - previous_cash_flow_date).days

            accrued_interest = calculate_accrued_interest(
                n_balance,
                interest_rate,
                days_since_last_payment,
                loan.v_day_count_ind
            )
            
            n_exposure_at_default += accrued_interest
            cash_flow.n_accrued_interest = accrued_interest
        return n_exposure_at_default
    except Exception as e:
        # save_log('calculate_exposure_and_accrued_interest', 'ERROR', f"Error for account {loan.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")
        return None

def process_cash_flows(cash_flows, fic_mis_date):
    """
    Processes a list of cash flow records and updates their Exposure at Default (EAD) and accrued interest.
    """
    bulk_updates = []
    previous_cash_flow_date = None

    for cash_flow in cash_flows:
        try:
            loan = Ldn_Financial_Instrument.objects.get(v_account_number=cash_flow.v_account_number, fic_mis_date=fic_mis_date)
            if previous_cash_flow_date is None:
                previous_cash_flow_date = loan.d_last_payment_date or cash_flow.d_cash_flow_date

            n_exposure_at_default = calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date)
            if n_exposure_at_default is not None:
                cash_flow.n_exposure_at_default = n_exposure_at_default
                bulk_updates.append(cash_flow)

            previous_cash_flow_date = cash_flow.d_cash_flow_date
        except Exception as e:
            save_log('process_cash_flows', 'ERROR', f"Error processing cash flow for account {cash_flow.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")

    # Perform bulk update if there are any updates to save
    if bulk_updates:
        try:
            FSI_Expected_Cashflow.objects.bulk_update(bulk_updates, ['n_exposure_at_default', 'n_accrued_interest'])
        except Exception as e:
            save_log('bulk_update_stage_determination', 'ERROR', f"Error during bulk update: {e}")

def update_cash_flows_with_ead(fic_mis_date, max_workers=8, batch_size=1000):
    """
    Update all cash flow buckets with Exposure at Default (EAD) and Accrued Interest using multi-threading and bulk updates.
    """
    try:
        cash_flows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).order_by('d_cash_flow_date')
        total_cash_flows = cash_flows.count()
        if total_cash_flows == 0:
            save_log('update_cash_flows_with_ead', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date}.")
            return 0

        cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, total_cash_flows, batch_size)]
        save_log('update_cash_flows_with_ead', 'INFO', f"Processing {total_cash_flows} cash flow buckets in {len(cash_flow_batches)} batches...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_cash_flows, batch, fic_mis_date): batch for batch in cash_flow_batches}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    save_log('update_cash_flows_with_ead', 'ERROR', f"Thread encountered an error: {exc}")
                    return 0

        save_log('update_cash_flows_with_ead', 'INFO', f"Updated {total_cash_flows} cash flow buckets with Exposure at Default and Accrued Interest.")
        return 1
    except Exception as e:
        save_log('update_cash_flows_with_ead', 'ERROR', f"Error updating cash flows for fic_mis_date {fic_mis_date}: {e}")
        return 0
