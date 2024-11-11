from django.db import transaction
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import FSI_Expected_Cashflow, Ldn_Financial_Instrument
from .save_log import save_log

def calculate_accrued_interest(principal, interest_rate, days, day_count_ind):
    """
    Calculate accrued interest based on principal, interest rate, number of days, and day count convention.
    """
    day_count = Decimal(360 if day_count_ind == '30/360' else 365)
    accrued_interest = principal * (interest_rate / Decimal(100)) * (Decimal(days) / day_count)
    return accrued_interest

def calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date):
    """
    Calculate the exposure at default and accrued interest for a given cash flow.
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
        save_log('calculate_exposure_and_accrued_interest', 'ERROR', f"Error for account {loan.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")
        return None

def load_loans_with_id_mapping(fic_mis_date):
    """
    Load all loans for the given MIS date into a dictionary with integer-based indexing for quick access.
    """
    loans = Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date)
    loans_cache = {}
    account_id_mapping = {}  # Map account numbers to integer IDs
    reverse_id_mapping = {}  # Map integer IDs back to loan records
    next_id = 1

    for loan in loans:
        account_number = loan.v_account_number
        account_id_mapping[account_number] = next_id
        reverse_id_mapping[next_id] = loan
        next_id += 1
    
    save_log('update_cash_flows_with_ead', 'INFO', f"Loaded {len(account_id_mapping)} loan records with integer indexing for MIS date {fic_mis_date}.")
    return account_id_mapping, reverse_id_mapping

def process_cash_flows(cash_flows, account_id_mapping, reverse_id_mapping, fic_mis_date):
    """
    Process cash flows and update accrued interest and exposure at default using integer-indexed loan data.
    """
    bulk_updates = []
    previous_dates = {}
    no_update_reasons = {}
    error_logs = {}

    for cash_flow in cash_flows:
        try:
            account_id = account_id_mapping.get(cash_flow.v_account_number)
            if account_id:
                loan = reverse_id_mapping[account_id]
                previous_date = previous_dates.get(account_id, loan.d_last_payment_date or cash_flow.d_cash_flow_date)
                
                n_exposure_at_default = calculate_exposure_and_accrued_interest(loan, cash_flow, previous_date)
                if n_exposure_at_default is not None:
                    cash_flow.n_exposure_at_default = n_exposure_at_default
                    bulk_updates.append(cash_flow)

                previous_dates[account_id] = cash_flow.d_cash_flow_date
            else:
                reason = f"Loan data not found for account {cash_flow.v_account_number} on MIS date {fic_mis_date}."
                no_update_reasons[reason] = no_update_reasons.get(reason, 0) + 1
        except Exception as e:
            error_message = f"Error processing cash flow for account {cash_flow.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}"
            error_logs[error_message] = error_logs.get(error_message, 0) + 1

    if bulk_updates:
        try:
            for i in range(0, len(bulk_updates), 5000):
                FSI_Expected_Cashflow.objects.bulk_update(bulk_updates[i:i + 5000], ['n_exposure_at_default', 'n_accrued_interest'])
        except Exception as e:
            error_message = f"Bulk update error: {e}"
            error_logs[error_message] = error_logs.get(error_message, 0) + 1

    # Log any unique errors and reasons for no updates
    for reason, count in no_update_reasons.items():
        save_log('process_cash_flows', 'INFO', f"{reason} occurred for {count} entries.")
    for error_message, count in error_logs.items():
        save_log('process_cash_flows', 'ERROR', f"{error_message} occurred {count} times.")

def update_cash_flows_with_ead(fic_mis_date, max_workers=8, batch_size=1000):
    """
    Main function to update cash flows with Exposure at Default and Accrued Interest.
    """
    try:
        account_id_mapping, reverse_id_mapping = load_loans_with_id_mapping(fic_mis_date)

        cash_flows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).order_by('v_account_number', 'd_cash_flow_date')
        total_cash_flows = cash_flows.count()
        if total_cash_flows == 0:
            save_log('update_cash_flows_with_ead', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date}.")
            return 0

        cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, total_cash_flows, batch_size)]
        save_log('update_cash_flows_with_ead', 'INFO', f"Processing {total_cash_flows} cash flow buckets in {len(cash_flow_batches)} batches...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_cash_flows, batch, account_id_mapping, reverse_id_mapping, fic_mis_date) for batch in cash_flow_batches]
            for future in as_completed(futures):
                try:
                    future.result()  # Retrieve results to raise any exceptions
                except Exception as exc:
                    save_log('update_cash_flows_with_ead', 'ERROR', f"Thread encountered an error: {exc}")

        save_log('update_cash_flows_with_ead', 'INFO', f"Updated {total_cash_flows} cash flow buckets with Exposure at Default and Accrued Interest.")
        return 1
    except Exception as e:
        save_log('update_cash_flows_with_ead', 'ERROR', f"Error updating cash flows for fic_mis_date {fic_mis_date}: {e}")
        return 0








# from django.db import transaction
# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from ..models import FSI_Expected_Cashflow, Ldn_Financial_Instrument
# from .save_log import save_log

# def calculate_accrued_interest(principal, interest_rate, days, day_count_ind):
#     """
#     Calculate accrued interest using the given day count convention.
#     """
#     day_count = Decimal(365)
#     if day_count_ind == '30/360':
#         day_count = Decimal(360)
#     elif day_count_ind == '30/365':
#         day_count = Decimal(365)
    
#     accrued_interest = principal * (interest_rate / Decimal(100)) * (Decimal(days) / day_count)
#     return accrued_interest

# def calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date):
#     """
#     Calculate both EAD (Exposure at Default) and Accrued Interest for a specific cash flow bucket.
#     """
#     try:
#         n_balance = Decimal(cash_flow.n_balance or 0)
#         n_exposure_at_default = n_balance

#         if loan.n_curr_interest_rate:
#             interest_rate = Decimal(loan.n_curr_interest_rate)
#             days_since_last_payment = (cash_flow.d_cash_flow_date - previous_cash_flow_date).days

#             accrued_interest = calculate_accrued_interest(
#                 n_balance,
#                 interest_rate,
#                 days_since_last_payment,
#                 loan.v_day_count_ind
#             )
            
#             n_exposure_at_default += accrued_interest
#             cash_flow.n_accrued_interest = accrued_interest
#         return n_exposure_at_default
#     except Exception as e:
#         # save_log('calculate_exposure_and_accrued_interest', 'ERROR', f"Error for account {loan.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")
#         return None

# def process_cash_flows(cash_flows, fic_mis_date):
#     """
#     Processes a list of cash flow records and updates their Exposure at Default (EAD) and accrued interest.
#     """
#     bulk_updates = []
#     previous_cash_flow_date = None

#     for cash_flow in cash_flows:
#         try:
#             loan = Ldn_Financial_Instrument.objects.get(v_account_number=cash_flow.v_account_number, fic_mis_date=fic_mis_date)
#             if previous_cash_flow_date is None:
#                 previous_cash_flow_date = loan.d_last_payment_date or cash_flow.d_cash_flow_date

#             n_exposure_at_default = calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date)
#             if n_exposure_at_default is not None:
#                 cash_flow.n_exposure_at_default = n_exposure_at_default
#                 bulk_updates.append(cash_flow)

#             previous_cash_flow_date = cash_flow.d_cash_flow_date
#         except Exception as e:
#             save_log('process_cash_flows', 'ERROR', f"Error processing cash flow for account {cash_flow.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")

#     # Perform bulk update if there are any updates to save
#     if bulk_updates:
#         try:
#             FSI_Expected_Cashflow.objects.bulk_update(bulk_updates, ['n_exposure_at_default', 'n_accrued_interest'])
#         except Exception as e:
#             save_log('bulk_update_stage_determination', 'ERROR', f"Error during bulk update: {e}")

# def update_cash_flows_with_ead(fic_mis_date, max_workers=8, batch_size=1000):
#     """
#     Update all cash flow buckets with Exposure at Default (EAD) and Accrued Interest using multi-threading and bulk updates.
#     """
#     try:
#         cash_flows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).order_by('d_cash_flow_date')
#         total_cash_flows = cash_flows.count()
#         if total_cash_flows == 0:
#             save_log('update_cash_flows_with_ead', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date}.")
#             return 0

#         cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, total_cash_flows, batch_size)]
#         save_log('update_cash_flows_with_ead', 'INFO', f"Processing {total_cash_flows} cash flow buckets in {len(cash_flow_batches)} batches...")

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = {executor.submit(process_cash_flows, batch, fic_mis_date): batch for batch in cash_flow_batches}
#             for future in as_completed(futures):
#                 try:
#                     future.result()
#                 except Exception as exc:
#                     save_log('update_cash_flows_with_ead', 'ERROR', f"Thread encountered an error: {exc}")
#                     return 0

#         save_log('update_cash_flows_with_ead', 'INFO', f"Updated {total_cash_flows} cash flow buckets with Exposure at Default and Accrued Interest.")
#         return 1
#     except Exception as e:
#         save_log('update_cash_flows_with_ead', 'ERROR', f"Error updating cash flows for fic_mis_date {fic_mis_date}: {e}")
#         return 0
