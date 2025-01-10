from decimal import Decimal
from django.db import connection, transaction
from .save_log import save_log

MAX_EIR = Decimal('999.99999999999')  # Max value with 15 digits and 11 decimal places
MIN_EIR = Decimal('0')                # Minimum EIR value (non-negative)

def update_stage_determination_eir(fic_mis_date):
    """
    Set-based SQL approach to update Effective Interest Rate (EIR) for accounts in FCT_Stage_Determination.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # SQL to calculate and update EIR
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET n_effective_interest_rate = (
                    CASE
                        WHEN n_curr_interest_rate IS NOT NULL AND v_amrt_term_unit IS NOT NULL THEN
                            CASE v_amrt_term_unit
                                WHEN 'D' THEN ROUND(POW((1 + n_curr_interest_rate / 100 / 365), 365) - 1, 11)
                                WHEN 'W' THEN ROUND(POW((1 + n_curr_interest_rate / 100 / 52), 52) - 1, 11)
                                WHEN 'M' THEN ROUND(POW((1 + n_curr_interest_rate / 100 / 12), 12) - 1, 11)
                                WHEN 'Q' THEN ROUND(POW((1 + n_curr_interest_rate / 100 / 4), 4) - 1, 11)
                                WHEN 'H' THEN ROUND(POW((1 + n_curr_interest_rate / 100 / 2), 2) - 1, 11)
                                WHEN 'Y' THEN ROUND(POW((1 + n_curr_interest_rate / 100), 1) - 1, 11)
                                ELSE NULL
                            END
                        ELSE NULL
                    END
                )
                WHERE fic_mis_date = %s
                  AND n_effective_interest_rate IS NULL
                  AND n_curr_interest_rate IS NOT NULL;
            """, [fic_mis_date])

            # Clamp the EIR to the defined MIN_EIR and MAX_EIR values
            cursor.execute("""
                UPDATE fct_stage_determination
                SET n_effective_interest_rate = LEAST(GREATEST(n_effective_interest_rate, %s), %s)
                WHERE fic_mis_date = %s AND n_effective_interest_rate IS NOT NULL;
            """, [MIN_EIR, MAX_EIR, fic_mis_date])

        # Log success
        save_log(
            'update_stage_determination_eir',
            'INFO',
            f"Successfully updated EIR for records with fic_mis_date={fic_mis_date}."
        )
        return 1  # Success

    except Exception as e:
        save_log(
            'update_stage_determination_eir',
            'ERROR',
            f"Error during EIR update for fic_mis_date={fic_mis_date}: {e}"
        )
        return 0  # Failure


# from decimal import Decimal, InvalidOperation
# from math import pow
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from django.db import transaction
# from django.db.models import F
# from ..models import FCT_Stage_Determination
# from .save_log import save_log

# MAX_EIR = Decimal('999.99999999999')  # Max value with 15 digits and 11 decimal places
# MIN_EIR = Decimal('0')                # EIR should not be negative, so we set the minimum at zero

# def calculate_eir_for_stage(entry):
#     """
#     Calculate the Effective Interest Rate (EIR) for a specific FCT_Stage_Determination entry.
#     """
#     try:
#         if not entry.n_curr_interest_rate:
#             return None

#         nominal_rate = Decimal(entry.n_curr_interest_rate) / Decimal(100)
#         v_amrt_term_unit = entry.v_amrt_term_unit

#         term_unit_map = {
#             'D': 365,  # Daily compounding
#             'W': 52,   # Weekly compounding
#             'M': 12,   # Monthly compounding
#             'Q': 4,    # Quarterly compounding
#             'H': 2,    # Semi-annual compounding
#             'Y': 1     # Annual compounding
#         }

#         compounding_frequency = term_unit_map.get(v_amrt_term_unit)
#         if compounding_frequency is None:
#             return None

#         # EIR = (1 + nominal_rate / compounding_frequency)^(compounding_frequency) - 1
#         eir_float = pow(
#             (1 + float(nominal_rate / compounding_frequency)),
#             compounding_frequency
#         ) - 1

#         eir = Decimal(eir_float)

#         # Clamp EIR to [MIN_EIR, MAX_EIR], then quantize to 11 decimals
#         eir = max(MIN_EIR, min(MAX_EIR, eir)).quantize(Decimal('1.00000000000'))
#         return eir

#     except (InvalidOperation, OverflowError, ValueError) as e:
#         save_log(
#             'calculate_eir_for_stage',
#             'ERROR',
#             f"Error calculating EIR for account={entry.n_account_number}, interest_rate={entry.n_curr_interest_rate}: {e}"
#         )
#         return None


# def update_stage_determination_eir(
#     fic_mis_date, 
#     max_workers=8, 
#     batch_size=2000,
#     update_batch_size=5000
# ):
#     """
#     Update the Effective Interest Rate (EIR) for accounts in the FCT_Stage_Determination table.

#     Steps:
#       1) Query records where n_effective_interest_rate is NULL.
#       2) Process them in parallel batches using ThreadPoolExecutor.
#       3) Bulk update each batch.
#       4) Log any unique errors.
    
#     :param fic_mis_date:      The date for filtering stage determination records.
#     :param max_workers:       Number of threads for parallel processing.
#     :param batch_size:        Number of records to process per thread.
#     :param update_batch_size: Number of records updated in a single bulk operation.
#     :return: 1 if successful, 0 if errors occurred or no updates performed.
#     """
#     try:
#         # Fetch only the fields needed for EIR calculation
#         stage_qs = FCT_Stage_Determination.objects.filter(
#             fic_mis_date=fic_mis_date, 
#             n_effective_interest_rate__isnull=True
#         ).only(
#             'n_account_number',
#             'n_curr_interest_rate',
#             'v_amrt_term_unit',
#             'n_effective_interest_rate'
#         )

#         total_entries = stage_qs.count()
#         if total_entries == 0:
#             save_log(
#                 'update_stage_determination_eir',
#                 'INFO',
#                 f"No records found with NULL EIR for fic_mis_date={fic_mis_date}."
#             )
#             return 0

#         save_log(
#             'update_stage_determination_eir',
#             'INFO',
#             f"Found {total_entries} entries needing EIR calculation."
#         )

#         # Convert QuerySet to a list for parallel processing
#         stage_entries = list(stage_qs)

#         # Utility to chunk the data
#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         # We'll store unique errors here
#         error_logs = {}

#         def process_batch(batch):
#             """
#             For each record in the batch, calculate EIR and store in memory
#             for a subsequent bulk update.
#             """
#             updated_records = []
#             for entry in batch:
#                 try:
#                     eir = calculate_eir_for_stage(entry)
#                     if eir is not None:
#                         entry.n_effective_interest_rate = eir
#                         updated_records.append(entry)
#                 except Exception as e:
#                     error_logs[f"Account {entry.n_account_number}, batch error: {str(e)}"] = 1
#             return updated_records

#         updated_entries_all = []

#         # Parallel processing with ThreadPoolExecutor
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             for batch in chunker(stage_entries, batch_size):
#                 futures.append(executor.submit(process_batch, batch))

#             # Gather results
#             for future in as_completed(futures):
#                 try:
#                     updated_entries_all.extend(future.result())
#                 except Exception as exc:
#                     error_logs[f"Thread encountered an error: {exc}"] = 1

#         total_updated = len(updated_entries_all)
#         if total_updated == 0:
#             # No updates
#             if not error_logs:
#                 save_log(
#                     'update_stage_determination_eir',
#                     'INFO',
#                     "No records were updated because no EIR could be calculated."
#                 )
#             else:
#                 for err_msg in error_logs:
#                     save_log('update_stage_determination_eir', 'ERROR', err_msg)
#             return 0 if error_logs else 1

#         # Perform bulk updates in sub-batches
#         from django.db import transaction
#         with transaction.atomic():
#             for start in range(0, total_updated, update_batch_size):
#                 end = start + update_batch_size
#                 FCT_Stage_Determination.objects.bulk_update(
#                     updated_entries_all[start:end],
#                     ['n_effective_interest_rate']
#                 )

#         # Log any errors
#         for err_msg in error_logs:
#             save_log('update_stage_determination_eir', 'ERROR', err_msg)

#         if error_logs:
#             save_log(
#                 'update_stage_determination_eir',
#                 'ERROR',
#                 f"Completed with errors. Processed={total_entries}, updated={total_updated}"
#             )
#             return 0
#         else:
#             save_log(
#                 'update_stage_determination_eir',
#                 'INFO',
#                 f"Successfully updated EIR for {total_updated} records out of {total_entries} total."
#             )
#             return 1

#     except Exception as e:
#         save_log(
#             'update_stage_determination_eir',
#             'ERROR',
#             f"Error during EIR update for fic_mis_date={fic_mis_date}: {e}"
#         )
#         return 0


# from decimal import Decimal, InvalidOperation
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from math import pow
# from ..models import FCT_Stage_Determination
# from .save_log import save_log

# MAX_EIR = Decimal('999.99999999999')  # Max value with 15 digits and 11 decimal places
# MIN_EIR = Decimal('0')  # EIR should not be negative, so we set the minimum at zero

# def calculate_eir_for_stage(entry):
#     """
#     Calculate the Effective Interest Rate (EIR) for a specific FCT_Stage_Determination entry.
#     """
#     try:
#         nominal_rate = Decimal(entry.n_curr_interest_rate/100) if entry.n_curr_interest_rate else None
#         v_amrt_term_unit = entry.v_amrt_term_unit
        
#         term_unit_map = {
#         'D': 365,  # Daily compounding
#         'W': 52,   # Weekly compounding
#         'M': 12,   # Monthly compounding
#         'Q': 4,    # Quarterly compounding
#         'H': 2,    # Semi-annual compounding
#         'Y': 1     # Annual compounding
#         }
        
#         if nominal_rate is None or v_amrt_term_unit not in term_unit_map:
#             return None
        
#         compounding_frequency = term_unit_map[v_amrt_term_unit]
#         eir = Decimal(pow((1 + float(nominal_rate / compounding_frequency)), compounding_frequency) - 1)

#         # Clamp and quantize EIR to fit within max_digits=15 and decimal_places=11
#         eir = max(MIN_EIR, min(MAX_EIR, eir)).quantize(Decimal('1.00000000000'))
        
#         return eir
    
#     except (InvalidOperation, OverflowError) as e:
#         save_log('calculate_eir_for_stage', 'ERROR', f"Error calculating EIR for account {entry.n_account_number}: {e}")
#         return None

# def update_stage_determination_eir(fic_mis_date, max_workers=8, batch_size=5000):
#     """
#     Update the Effective Interest Rate (EIR) for accounts in the FCT_Stage_Determination table.
#     """
#     try:
#         stage_determination_entries = FCT_Stage_Determination.objects.filter(
#             fic_mis_date=fic_mis_date, 
#             n_effective_interest_rate__isnull=True
#         )
        
#         total_entries = stage_determination_entries.count()
#         batches = [stage_determination_entries[i:i + batch_size] for i in range(0, total_entries, batch_size)]
#         save_log('update_stage_determination_eir', 'INFO', f"Processing {total_entries} entries in {len(batches)} batches...")

#         error_logs = {}

#         def process_batch(batch):
#             bulk_updates = []
#             for entry in batch:
#                 try:
#                     eir = calculate_eir_for_stage(entry)
                    
#                     if eir is not None:
#                         entry.n_effective_interest_rate = eir
#                         bulk_updates.append(entry)
                
#                 except Exception as e:
#                     error_message = f"Error processing account {entry.n_account_number}: {e}"
#                     error_logs[error_message] = 1  # Record unique errors
            
#             # Perform bulk update for the current batch
#             if bulk_updates:
#                 try:
#                     FCT_Stage_Determination.objects.bulk_update(bulk_updates, ['n_effective_interest_rate'])
#                 except Exception as e:
#                     error_logs[f"Bulk update error: {e}"] = 1

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = [executor.submit(process_batch, batch) for batch in batches]
#             for future in as_completed(futures):
#                 try:
#                     future.result()
#                 except Exception as exc:
#                     error_logs[f"Thread encountered an error: {exc}"] = 1

#         for error_message in error_logs:
#             save_log('update_stage_determination_eir', 'ERROR', error_message)

#         if not error_logs:
#             save_log('update_stage_determination_eir', 'INFO', f"Successfully processed {total_entries} records.")
#         return 1 if not error_logs else 0

#     except Exception as e:
#         save_log('update_stage_determination_eir', 'ERROR', f"Error during EIR update process: {e}")
#         return 0



