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
            return '0'

        # Bulk fetch related data and store it in dictionaries for fast lookups
        product_info_cache = {p.v_prod_code: p for p in Ldn_Bank_Product_Info.objects.all()}
        segment_cache = {(s.v_prod_segment, s.v_prod_type): s.segment_id for s in FSI_Product_Segment.objects.all()}
        collateral_cache = {(c.v_cust_ref_code, c.fic_mis_date): c for c in LgdCollateral.objects.filter(fic_mis_date=mis_date)}
        delinquency_band_cache = {
            (band.n_delq_lower_value, band.n_delq_upper_value, band.v_amrt_term_unit): band.n_delq_band_code
            for band in Dim_Delinquency_Band.objects.all()
        }
        customer_info_cache = {c.v_party_id: c for c in Ldn_Customer_Info.objects.all()}
        pd_term_structure_cache = {pd.v_pd_term_structure_id: pd for pd in Ldn_PD_Term_Structure.objects.all()}
        rating_detail_cache = {(r.fic_mis_date, r.v_party_cd): r for r in Ldn_Customer_Rating_Detail.objects.filter(fic_mis_date=mis_date)}

        # Initialize error logs to capture the first instance of each unique error
        error_logs = {}

        # Process each entry with cached data
        updated_entries = []
        for entry in stage_determination_entries:
            # Update product information
            product_info = product_info_cache.get(entry.n_prod_code)
            if product_info:
                entry.n_prod_segment = product_info.v_prod_segment
                entry.n_prod_name = product_info.v_prod_name
                entry.n_prod_type = product_info.v_prod_type
                entry.n_prod_desc = product_info.v_prod_desc
            elif "product_info_missing" not in error_logs:
                error_logs["product_info_missing"] = f"Product info missing for code: {entry.n_prod_code}"

            # Update segment key
            if entry.n_prod_segment and entry.n_prod_type:
                entry.n_segment_skey = segment_cache.get((entry.n_prod_segment, entry.n_prod_type))
                if not entry.n_segment_skey and "segment_info_missing" not in error_logs:
                    error_logs["segment_info_missing"] = f"Segment info missing for segment: {entry.n_prod_segment}, type: {entry.n_prod_type}"
                
            # Update collateral amount
            collateral = collateral_cache.get((entry.n_cust_ref_code, entry.fic_mis_date))
            if collateral and (entry.n_collateral_amount is None or entry.n_collateral_amount == 0):
                entry.n_collateral_amount = collateral.total
            elif "collateral_info_missing" not in error_logs:
                error_logs["collateral_info_missing"] = f"Collateral info missing for cust ref code: {entry.n_cust_ref_code}"

            # Update delinquency band
            delinquency_band_found = False
            for (lower, upper, unit), band_code in delinquency_band_cache.items():
                if lower <= entry.n_delinquent_days <= upper and unit == entry.v_amrt_term_unit:
                    entry.n_delq_band_code = band_code
                    delinquency_band_found = True
                    break
            if not delinquency_band_found and "delinquency_band_missing" not in error_logs:
                error_logs["delinquency_band_missing"] = (
                    f"Delinquency band missing for delinquent days: {entry.n_delinquent_days}, term unit: {entry.v_amrt_term_unit}"
                )

            # Update customer information
            customer_info = customer_info_cache.get(entry.n_cust_ref_code)
            if customer_info:
                entry.n_partner_name = customer_info.v_partner_name
                entry.n_party_type = customer_info.v_party_type
            elif "customer_info_missing" not in error_logs:
                error_logs["customer_info_missing"] = f"Customer info missing for cust ref code: {entry.n_cust_ref_code}"

            # Set PD term structure key to segment key
            entry.n_pd_term_structure_skey = entry.n_segment_skey

            # Update PD term structure
            pd_term_structure = pd_term_structure_cache.get(entry.n_pd_term_structure_skey)
            if pd_term_structure:
                entry.n_pd_term_structure_name = pd_term_structure.v_pd_term_structure_name
                entry.n_pd_term_structure_desc = pd_term_structure.v_pd_term_structure_desc
            elif "pd_term_structure_missing" not in error_logs:
                error_logs["pd_term_structure_missing"] = f"PD term structure missing for segment key: {entry.n_segment_skey}"

            # Update rating code
            rating_detail = rating_detail_cache.get((entry.fic_mis_date, entry.n_cust_ref_code))
            if rating_detail and entry.n_credit_rating_code is None:
                entry.n_credit_rating_code = rating_detail.v_rating_code
            elif "rating_detail_missing" not in error_logs:
                error_logs["rating_detail_missing"] = f"Rating detail missing for cust ref code: {entry.n_cust_ref_code}, mis date: {entry.fic_mis_date}"

            # Calculate account rating movement
            if entry.n_org_credit_score is not None and entry.n_curr_credit_score is not None:
                entry.n_acct_rating_movement = entry.n_org_credit_score - entry.n_curr_credit_score

            updated_entries.append(entry)

        # Fields to be updated
        updated_fields = [
            'n_prod_segment', 'n_prod_name', 'n_prod_type', 'n_prod_desc', 'n_segment_skey',
            'n_collateral_amount', 'n_delq_band_code', 'n_partner_name', 'n_party_type', 
            'n_pd_term_structure_skey', 'n_pd_term_structure_name', 'n_pd_term_structure_desc', 
            'n_credit_rating_code', 'n_acct_rating_movement'
        ]

        # Perform bulk update in batches of 5000
        batch_size = 5000
        with transaction.atomic():
            for i in range(0, len(updated_entries), batch_size):
                FCT_Stage_Determination.objects.bulk_update(updated_entries[i:i + batch_size], updated_fields)

        # Log the exact missing data errors, each type only once
        for error_type, error_message in error_logs.items():
            save_log('update_stage_determination', 'WARNING', error_message)

        save_log('update_stage_determination', 'INFO', f"Successfully updated {len(updated_entries)} records for mis_date {mis_date}.")
        return '1'

    except Exception as e:
        save_log('update_stage_determination', 'ERROR', f"Error during update process: {e}")
        return '0'
