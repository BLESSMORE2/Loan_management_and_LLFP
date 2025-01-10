from django.db import connection, transaction
from ..models import Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.only('latest_run_skey').first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key is available.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def update_stage_determination(mis_date):
    """
    Set-based update of various fields in FCT_Stage_Determination for a given mis_date by joining with related tables.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Update product-related fields
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN ldn_bank_product_info AS p ON p.v_prod_code = sd.n_prod_code
                SET 
                    sd.n_prod_segment = p.v_prod_segment,
                    sd.n_prod_name = p.v_prod_name,
                    sd.n_prod_type = p.v_prod_type,
                    sd.n_prod_desc = p.v_prod_desc
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update segment key
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN fsi_product_segment AS s ON s.v_prod_segment = sd.n_prod_segment AND s.v_prod_type = sd.n_prod_type
                SET sd.n_segment_skey = s.segment_id
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update pd term structure key
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                SET  sd.n_pd_term_structure_skey = sd.n_segment_skey
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])


            # Update collateral amount where missing
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN lgd_collateral AS c ON c.v_cust_ref_code = sd.n_cust_ref_code AND c.fic_mis_date = sd.fic_mis_date
                SET sd.n_collateral_amount = c.total
                WHERE sd.fic_mis_date = %s AND (sd.n_collateral_amount IS NULL OR sd.n_collateral_amount = 0);
            """, [mis_date])

            # Update delinquency band code
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN dim_delinquency_band AS band 
                  ON sd.n_delinquent_days BETWEEN band.n_delq_lower_value AND band.n_delq_upper_value
                 AND band.v_amrt_term_unit = sd.v_amrt_term_unit
                SET sd.n_delq_band_code = band.n_delq_band_code
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update customer info
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN ldn_customer_info AS ci ON ci.v_party_id = sd.n_cust_ref_code
                SET 
                    sd.n_partner_name = ci.v_partner_name,
                    sd.n_party_type = ci.v_party_type
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update PD term structure info
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN ldn_pd_term_structure AS pdt ON pdt.v_pd_term_structure_id = sd.n_pd_term_structure_skey
                SET 
                    sd.n_pd_term_structure_name = pdt.v_pd_term_structure_desc,
                    sd.n_pd_term_structure_desc = pdt.v_pd_term_structure_desc
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update customer rating detail if missing
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN ldn_customer_rating_detail AS rd 
                  ON rd.fic_mis_date = sd.fic_mis_date 
                 AND rd.v_party_cd = sd.n_cust_ref_code
                SET sd.n_credit_rating_code = rd.v_rating_code
                WHERE sd.fic_mis_date = %s AND sd.n_credit_rating_code IS NULL;
            """, [mis_date])

            # Update account rating movement
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                SET sd.n_acct_rating_movement = sd.n_org_credit_score - sd.n_curr_credit_score
                WHERE sd.fic_mis_date = %s 
                  AND sd.n_org_credit_score IS NOT NULL 
                  AND sd.n_curr_credit_score IS NOT NULL;
            """, [mis_date])

        save_log('update_stage_determination_setbased', 'INFO',
                 f"Set-based update completed for mis_date={mis_date}.")
        return '1'

    except Exception as e:
        save_log('update_stage_determination_setbased', 'ERROR', f"Error during set-based update: {e}")
        return '0'


# from django.db import transaction
# from django.db.models import F, Q
# from decimal import Decimal

# from ..models import (
#     FCT_Stage_Determination,
#     Ldn_Bank_Product_Info,
#     FSI_Product_Segment,
#     LgdCollateral,
#     Dim_Delinquency_Band,
#     Ldn_Customer_Info,
#     Ldn_PD_Term_Structure,
#     Ldn_Customer_Rating_Detail
# )
# from .save_log import save_log


# BATCH_SIZE = 5000  # Adjust for your environment's performance sweet spot

# def update_stage_determination(mis_date):
#     """
#     Update FCT_Stage_Determination with product, segment, customer, delinquency band,
#     and PD term structure information based on the provided mis_date.
#     """
#     try:
#         # ----------------------------------
#         # 1. Fetch the Stage Determination entries for the given date
#         # ----------------------------------
#         stage_determination_entries = list(
#             FCT_Stage_Determination.objects
#             .filter(fic_mis_date=mis_date)
#             .exclude(n_prod_code__isnull=True)
#             .only(
#                 'n_account_number',
#                 'fic_mis_date',
#                 'n_prod_code',
#                 'n_org_credit_score',
#                 'n_curr_credit_score',
#                 'n_partner_name',
#                 'n_party_type',
#                 'n_delinquent_days',
#                 'v_amrt_term_unit',
#                 'n_cust_ref_code',
#                 'n_segment_skey',
#                 'n_pd_term_structure_skey',
#                 'n_prod_segment',
#                 'n_prod_name',
#                 'n_prod_type',
#                 'n_prod_desc',
#                 'n_collateral_amount',
#                 'n_delq_band_code',
#                 'n_pd_term_structure_name',
#                 'n_pd_term_structure_desc',
#                 'n_credit_rating_code',
#                 'n_acct_rating_movement'
#             )
#         )

#         if not stage_determination_entries:
#             save_log(
#                 'update_stage_determination',
#                 'INFO',
#                 f"No stage determination entries found for mis_date={mis_date}."
#             )
#             return '0'

#         # ----------------------------------
#         # 2. Prepare caches for lookups
#         # ----------------------------------

#         # a) Product info cache keyed by v_prod_code
#         product_info_cache = {
#             p.v_prod_code: p
#             for p in Ldn_Bank_Product_Info.objects.only(
#                 'v_prod_code', 'v_prod_segment', 'v_prod_name',
#                 'v_prod_type', 'v_prod_desc'
#             )
#         }

#         # b) Segment cache keyed by (v_prod_segment, v_prod_type)
#         segment_cache = {
#             (s.v_prod_segment, s.v_prod_type): s.segment_id
#             for s in FSI_Product_Segment.objects.only(
#                 'v_prod_segment', 'v_prod_type', 'segment_id'
#             )
#         }

#         # c) Collateral cache keyed by (v_cust_ref_code, fic_mis_date)
#         collateral_cache = {
#             (c.v_cust_ref_code, c.fic_mis_date): c
#             for c in lgd_collateral.objects.filter(fic_mis_date=mis_date).only(
#                 'v_cust_ref_code', 'fic_mis_date', 'total'
#             )
#         }

#         # d) Delinquency band cache keyed by (n_delq_lower_value, n_delq_upper_value, v_amrt_term_unit)
#         delinquency_band_cache = {
#             (band.n_delq_lower_value, band.n_delq_upper_value, band.v_amrt_term_unit): band.n_delq_band_code
#             for band in Dim_Delinquency_Band.objects.only(
#                 'n_delq_lower_value', 'n_delq_upper_value',
#                 'v_amrt_term_unit', 'n_delq_band_code'
#             )
#         }

#         # e) Customer info cache keyed by v_party_id
#         customer_info_cache = {
#             c.v_party_id: c
#             for c in Ldn_Customer_Info.objects.only(
#                 'v_party_id', 'v_partner_name', 'v_party_type'
#             )
#         }

#         # f) PD term structure cache keyed by v_pd_term_structure_id
#         pd_term_structure_cache = {
#             pd.v_pd_term_structure_id: pd
#             for pd in Ldn_PD_Term_Structure.objects.only(
#                 'v_pd_term_structure_id',
#                 'v_pd_term_structure_name',
#                 'v_pd_term_structure_desc'
#             )
#         }

#         # g) Rating detail cache keyed by (fic_mis_date, v_party_cd)
#         rating_detail_cache = {
#             (r.fic_mis_date, r.v_party_cd): r
#             for r in Ldn_Customer_Rating_Detail.objects
#             .filter(fic_mis_date=mis_date)
#             .only('fic_mis_date', 'v_party_cd', 'v_rating_code')
#         }

#         # ----------------------------------
#         # 3. Initialize error logs
#         # ----------------------------------
#         error_logs = {}

#         # ----------------------------------
#         # 4. Process each entry in memory
#         # ----------------------------------
#         updated_entries = []
#         for entry in stage_determination_entries:
#             # 4a) Product information
#             product_info = product_info_cache.get(entry.n_prod_code)
#             if product_info:
#                 entry.n_prod_segment = product_info.v_prod_segment
#                 entry.n_prod_name = product_info.v_prod_name
#                 entry.n_prod_type = product_info.v_prod_type
#                 entry.n_prod_desc = product_info.v_prod_desc
#             elif "product_info_missing" not in error_logs:
#                 error_logs["product_info_missing"] = f"Product info missing for code={entry.n_prod_code}"

#             # 4b) Segment key
#             if entry.n_prod_segment and entry.n_prod_type:
#                 entry.n_segment_skey = segment_cache.get((entry.n_prod_segment, entry.n_prod_type))
#                 if not entry.n_segment_skey and "segment_info_missing" not in error_logs:
#                     error_logs["segment_info_missing"] = (
#                         f"Segment info missing for segment={entry.n_prod_segment}, type={entry.n_prod_type}"
#                     )

#             # 4c) Collateral amount
#             if (entry.n_cust_ref_code, entry.fic_mis_date) in collateral_cache:
#                 collateral = collateral_cache[(entry.n_cust_ref_code, entry.fic_mis_date)]
#                 if not entry.n_collateral_amount:
#                     entry.n_collateral_amount = collateral.total
#             else:
#                 if "collateral_info_missing" not in error_logs:
#                     error_logs["collateral_info_missing"] = (
#                         f"Collateral missing for cust_ref={entry.n_cust_ref_code} at date={entry.fic_mis_date}"
#                     )

#             # 4d) Delinquency band
#             delinquency_band_found = False
#             for (lower, upper, unit), band_code in delinquency_band_cache.items():
#                 if (lower <= entry.n_delinquent_days <= upper) and (unit == entry.v_amrt_term_unit):
#                     entry.n_delq_band_code = band_code
#                     delinquency_band_found = True
#                     break

#             if not delinquency_band_found:
#                 if "delinquency_band_missing" not in error_logs:
#                     error_logs["delinquency_band_missing"] = (
#                         f"No delinquency band for delinq_days={entry.n_delinquent_days}, unit={entry.v_amrt_term_unit}"
#                     )

#             # 4e) Customer information
#             if entry.n_cust_ref_code in customer_info_cache:
#                 cust_info = customer_info_cache[entry.n_cust_ref_code]
#                 entry.n_partner_name = cust_info.v_partner_name
#                 entry.n_party_type = cust_info.v_party_type
#             else:
#                 if "customer_info_missing" not in error_logs:
#                     error_logs["customer_info_missing"] = (
#                         f"Customer info missing for cust_ref_code={entry.n_cust_ref_code}"
#                     )

#             # 4f) PD term structure
#             entry.n_pd_term_structure_skey = entry.n_segment_skey  # Simplified logic: PD structure = segment skey
#             pd_term_structure = pd_term_structure_cache.get(entry.n_pd_term_structure_skey)
#             if pd_term_structure:
#                 entry.n_pd_term_structure_name = pd_term_structure.v_pd_term_structure_name
#                 entry.n_pd_term_structure_desc = pd_term_structure.v_pd_term_structure_desc
#             else:
#                 if "pd_term_structure_missing" not in error_logs:
#                     error_logs["pd_term_structure_missing"] = (
#                         f"PD term structure missing for segment key={entry.n_segment_skey}"
#                     )

#             # 4g) Rating detail
#             rating_detail = rating_detail_cache.get((entry.fic_mis_date, entry.n_cust_ref_code))
#             if rating_detail and entry.n_credit_rating_code is None:
#                 entry.n_credit_rating_code = rating_detail.v_rating_code
#             else:
#                 if "rating_detail_missing" not in error_logs:
#                     error_logs["rating_detail_missing"] = (
#                         f"Rating detail missing for cust_ref={entry.n_cust_ref_code}, date={entry.fic_mis_date}"
#                     )

#             # 4h) Account rating movement
#             if (entry.n_org_credit_score is not None) and (entry.n_curr_credit_score is not None):
#                 entry.n_acct_rating_movement = entry.n_org_credit_score - entry.n_curr_credit_score

#             updated_entries.append(entry)

#         # ----------------------------------
#         # 5. Bulk update the processed entries in sub-batches
#         # ----------------------------------
#         updated_fields = [
#             'n_prod_segment', 'n_prod_name', 'n_prod_type', 'n_prod_desc', 'n_segment_skey',
#             'n_collateral_amount', 'n_delq_band_code', 'n_partner_name', 'n_party_type',
#             'n_pd_term_structure_skey', 'n_pd_term_structure_name', 'n_pd_term_structure_desc',
#             'n_credit_rating_code', 'n_acct_rating_movement'
#         ]

#         with transaction.atomic():
#             for start in range(0, len(updated_entries), BATCH_SIZE):
#                 end = start + BATCH_SIZE
#                 FCT_Stage_Determination.objects.bulk_update(
#                     updated_entries[start:end],
#                     updated_fields
#                 )

#         # ----------------------------------
#         # 6. Log warnings for missing data
#         # ----------------------------------
#         for error_type, msg in error_logs.items():
#             save_log('update_stage_determination', 'WARNING', msg)

#         # ----------------------------------
#         # 7. Final log & return
#         # ----------------------------------
#         save_log(
#             'update_stage_determination',
#             'INFO',
#             f"Successfully updated {len(updated_entries)} records for mis_date={mis_date}."
#         )
#         return '1'

#     except Exception as e:
#         save_log('update_stage_determination', 'ERROR', f"Error during update process for mis_date={mis_date}: {e}")
#         return '0'


# from django.db import transaction
# from ..models import *
# from .save_log import save_log

# def update_stage_determination(mis_date):
#     """
#     Update FCT_Stage_Determination with product, segment, customer, delinquency band,
#     and PD term structure information based on the provided mis_date.
#     """
#     try:
#         # Fetch all entries from FCT_Stage_Determination for the given mis_date
#         stage_determination_entries = FCT_Stage_Determination.objects.filter(fic_mis_date=mis_date).exclude(n_prod_code__isnull=True)
        
#         if not stage_determination_entries.exists():
#             save_log('update_stage_determination', 'INFO', f"No stage determination entries found for mis_date {mis_date}.")
#             return '0'

#         # Bulk fetch related data and store it in dictionaries for fast lookups
#         product_info_cache = {p.v_prod_code: p for p in Ldn_Bank_Product_Info.objects.all()}
#         segment_cache = {(s.v_prod_segment, s.v_prod_type): s.segment_id for s in FSI_Product_Segment.objects.all()}
#         collateral_cache = {(c.v_cust_ref_code, c.fic_mis_date): c for c in LgdCollateral.objects.filter(fic_mis_date=mis_date)}
#         delinquency_band_cache = {
#             (band.n_delq_lower_value, band.n_delq_upper_value, band.v_amrt_term_unit): band.n_delq_band_code
#             for band in Dim_Delinquency_Band.objects.all()
#         }
#         customer_info_cache = {c.v_party_id: c for c in Ldn_Customer_Info.objects.all()}
#         pd_term_structure_cache = {pd.v_pd_term_structure_id: pd for pd in Ldn_PD_Term_Structure.objects.all()}
#         rating_detail_cache = {(r.fic_mis_date, r.v_party_cd): r for r in Ldn_Customer_Rating_Detail.objects.filter(fic_mis_date=mis_date)}

#         # Initialize error logs to capture the first instance of each unique error
#         error_logs = {}

#         # Process each entry with cached data
#         updated_entries = []
#         for entry in stage_determination_entries:
#             # Update product information
#             product_info = product_info_cache.get(entry.n_prod_code)
#             if product_info:
#                 entry.n_prod_segment = product_info.v_prod_segment
#                 entry.n_prod_name = product_info.v_prod_name
#                 entry.n_prod_type = product_info.v_prod_type
#                 entry.n_prod_desc = product_info.v_prod_desc
#             elif "product_info_missing" not in error_logs:
#                 error_logs["product_info_missing"] = f"Product info missing for code: {entry.n_prod_code}"

#             # Update segment key
#             if entry.n_prod_segment and entry.n_prod_type:
#                 entry.n_segment_skey = segment_cache.get((entry.n_prod_segment, entry.n_prod_type))
#                 if not entry.n_segment_skey and "segment_info_missing" not in error_logs:
#                     error_logs["segment_info_missing"] = f"Segment info missing for segment: {entry.n_prod_segment}, type: {entry.n_prod_type}"
                
#             # Update collateral amount
#             collateral = collateral_cache.get((entry.n_cust_ref_code, entry.fic_mis_date))
#             if collateral and (entry.n_collateral_amount is None or entry.n_collateral_amount == 0):
#                 entry.n_collateral_amount = collateral.total
#             elif "collateral_info_missing" not in error_logs:
#                 error_logs["collateral_info_missing"] = f"Collateral info missing for cust ref code: {entry.n_cust_ref_code}"

#             # Update delinquency band
#             delinquency_band_found = False
#             for (lower, upper, unit), band_code in delinquency_band_cache.items():
#                 if lower <= entry.n_delinquent_days <= upper and unit == entry.v_amrt_term_unit:
#                     entry.n_delq_band_code = band_code
#                     delinquency_band_found = True
#                     break
#             if not delinquency_band_found and "delinquency_band_missing" not in error_logs:
#                 error_logs["delinquency_band_missing"] = (
#                     f"Delinquency band missing for delinquent days: {entry.n_delinquent_days}, term unit: {entry.v_amrt_term_unit}"
#                 )

#             # Update customer information
#             customer_info = customer_info_cache.get(entry.n_cust_ref_code)
#             if customer_info:
#                 entry.n_partner_name = customer_info.v_partner_name
#                 entry.n_party_type = customer_info.v_party_type
#             elif "customer_info_missing" not in error_logs:
#                 error_logs["customer_info_missing"] = f"Customer info missing for cust ref code: {entry.n_cust_ref_code}"

#             # Set PD term structure key to segment key
#             entry.n_pd_term_structure_skey = entry.n_segment_skey

#             # Update PD term structure
#             pd_term_structure = pd_term_structure_cache.get(entry.n_pd_term_structure_skey)
#             if pd_term_structure:
#                 entry.n_pd_term_structure_name = pd_term_structure.v_pd_term_structure_name
#                 entry.n_pd_term_structure_desc = pd_term_structure.v_pd_term_structure_desc
#             elif "pd_term_structure_missing" not in error_logs:
#                 error_logs["pd_term_structure_missing"] = f"PD term structure missing for segment key: {entry.n_segment_skey}"

#             # Update rating code
#             rating_detail = rating_detail_cache.get((entry.fic_mis_date, entry.n_cust_ref_code))
#             if rating_detail and entry.n_credit_rating_code is None:
#                 entry.n_credit_rating_code = rating_detail.v_rating_code
#             elif "rating_detail_missing" not in error_logs:
#                 error_logs["rating_detail_missing"] = f"Rating detail missing for cust ref code: {entry.n_cust_ref_code}, mis date: {entry.fic_mis_date}"

#             # Calculate account rating movement
#             if entry.n_org_credit_score is not None and entry.n_curr_credit_score is not None:
#                 entry.n_acct_rating_movement = entry.n_org_credit_score - entry.n_curr_credit_score

#             updated_entries.append(entry)

#         # Fields to be updated
#         updated_fields = [
#             'n_prod_segment', 'n_prod_name', 'n_prod_type', 'n_prod_desc', 'n_segment_skey',
#             'n_collateral_amount', 'n_delq_band_code', 'n_partner_name', 'n_party_type', 
#             'n_pd_term_structure_skey', 'n_pd_term_structure_name', 'n_pd_term_structure_desc', 
#             'n_credit_rating_code', 'n_acct_rating_movement'
#         ]

#         # Perform bulk update in batches of 5000
#         batch_size = 5000
#         with transaction.atomic():
#             for i in range(0, len(updated_entries), batch_size):
#                 FCT_Stage_Determination.objects.bulk_update(updated_entries[i:i + batch_size], updated_fields)

#         # Log the exact missing data errors, each type only once
#         for error_type, error_message in error_logs.items():
#             save_log('update_stage_determination', 'WARNING', error_message)

#         save_log('update_stage_determination', 'INFO', f"Successfully updated {len(updated_entries)} records for mis_date {mis_date}.")
#         return '1'

#     except Exception as e:
#         save_log('update_stage_determination', 'ERROR', f"Error during update process: {e}")
#         return '0'
