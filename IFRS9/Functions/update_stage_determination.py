from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *
from .save_log import save_log

def update_stage_determination(mis_date):
    """
    Update FCT_Stage_Determination with product, segment, customer, delinquency band,
    and PD term structure information based on the provided mis_date.
    """
    try:
        # Fetch all entries from FCT_Stage_Determination for the given mis_date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(fic_mis_date=mis_date).exclude(n_prod_code__isnull=True)

        if not stage_determination_entries.exists():
            save_log('update_stage_determination', 'INFO', f"No stage determination entries found for mis_date {mis_date}.")
            return '0'  # Return '0' if no records are found

        # Use ThreadPoolExecutor to process updates in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            updated_entries = list(executor.map(process_product_info_update, stage_determination_entries))

        # Perform bulk update for all processed entries
        updated_fields = [
            'n_prod_segment', 'n_prod_name', 'n_prod_type', 'n_prod_desc', 'n_segment_skey',
            'n_collateral_amount', 'n_delq_band_code', 'n_partner_name', 'n_party_type', 
            'n_pd_term_structure_skey', 'n_pd_term_structure_name', 'n_pd_term_structure_desc', 
            'n_credit_rating_code', 'n_acct_rating_movement'
        ]
        
        with transaction.atomic():
            updated_count = FCT_Stage_Determination.objects.bulk_update(updated_entries, updated_fields)

        save_log('update_stage_determination', 'INFO', f"Successfully updated {updated_count} records for mis_date {mis_date}.")
        return '1'  # Return '1' on successful completion

    except Exception as e:
        save_log('update_stage_determination', 'ERROR', f"Error during update process: {e}")
        return '0'  # Return '0' in case of any exception

def process_product_info_update(entry):
    """
    Update product info, segment key, customer info, delinquency band, and PD term structure info
    for a single FCT_Stage_Determination entry.
    """
    try:
        # Update product information from Ldn_Bank_Product_Info
        product_info = Ldn_Bank_Product_Info.objects.get(v_prod_code=entry.n_prod_code)
        entry.n_prod_segment = product_info.v_prod_segment
        entry.n_prod_name = product_info.v_prod_name
        entry.n_prod_type = product_info.v_prod_type
        entry.n_prod_desc = product_info.v_prod_desc

    except Ldn_Bank_Product_Info.DoesNotExist:
        save_log('process_product_info_update', 'ERROR', f"Product info not found for code: {entry.n_prod_code}")
    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating product info for entry {entry.n_prod_code}: {e}")

    try:
        # Update the segment key (n_segment_skey) using FSI_Product_Segment
        product_segment = FSI_Product_Segment.objects.get(
            v_prod_segment=entry.n_prod_segment,
            v_prod_type=entry.n_prod_type
         
        )
        entry.n_segment_skey = product_segment.segment_id

    except FSI_Product_Segment.DoesNotExist:
        save_log('process_product_info_update', 'ERROR', f"No matching segment found for {entry.n_prod_segment}, {entry.n_prod_type}, {entry.n_prod_desc}")
    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating segment key for entry {entry.n_prod_code}: {e}")

    if entry.n_collateral_amount is None or entry.n_collateral_amount == 0:
        try:
            # Find collateral data from LgdCollateral using v_cust_ref_code and fic_mis_date
            collateral = LgdCollateral.objects.get(v_cust_ref_code=entry.n_cust_ref_code, fic_mis_date=entry.fic_mis_date)
            entry.n_collateral_amount = collateral.total

        except Exception as e:
            save_log('process_product_info_update', 'ERROR', f"Error updating collateral amount for entry {entry.n_account_number}: {e}")

    try:
        # Update delinquency band code based on n_delinquent_days and v_amrt_term_unit
        delinquency_band = Dim_Delinquency_Band.objects.get(
            n_delq_lower_value__lte=entry.n_delinquent_days,
            n_delq_upper_value__gte=entry.n_delinquent_days,
            v_amrt_term_unit=entry.v_amrt_term_unit
        )
        entry.n_delq_band_code = delinquency_band.n_delq_band_code

    except Dim_Delinquency_Band.DoesNotExist:
        save_log('process_product_info_update', 'ERROR', f"No matching delinquency band found for account {entry.n_account_number} with {entry.n_delinquent_days} delinquent days")
    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating delinquency band for account {entry.n_account_number}: {e}")

    try:
        # Update customer information (n_partner_name, n_party_type) using Ldn_Customer_Info
        customer_info = Ldn_Customer_Info.objects.get(v_party_id=entry.n_cust_ref_code)
        entry.n_partner_name = customer_info.v_partner_name
        entry.n_party_type = customer_info.v_party_type

    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating customer info for entry {entry.n_prod_code}: {e}")

    try:
        # First set n_pd_term_structure_skey = n_segment_skey
        entry.n_pd_term_structure_skey = entry.n_segment_skey

        # Update n_pd_term_structure_name and n_pd_term_structure_desc using Ldn_PD_Term_Structure
        pd_term_structure = Ldn_PD_Term_Structure.objects.get(v_pd_term_structure_id=entry.n_pd_term_structure_skey)
        entry.n_pd_term_structure_name = pd_term_structure.v_pd_term_structure_name
        entry.n_pd_term_structure_desc = pd_term_structure.v_pd_term_structure_desc

    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating PD term structure for entry {entry.n_prod_code}: {e}")

    try:
        # Update rating code using Ldn_Customer_Rating_Detail
        rating_detail = Ldn_Customer_Rating_Detail.objects.get(
            fic_mis_date=entry.fic_mis_date,
            v_party_cd=entry.n_cust_ref_code
        )
        if entry.n_credit_rating_code is None:
            entry.n_credit_rating_code = rating_detail.v_rating_code

    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error updating rating code for entry {entry.n_prod_code}: {e}")

    try:
        if entry.n_org_credit_score is not None and entry.n_curr_credit_score is not None:
            entry.n_acct_rating_movement = entry.n_org_credit_score - entry.n_curr_credit_score
    except Exception as e:
        save_log('process_product_info_update', 'ERROR', f"Error calculating v_acct_rating_movement for entry {entry.n_account_number}: {e}")

    return entry
