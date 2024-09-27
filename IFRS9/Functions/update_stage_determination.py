from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *

def update_stage_determination(mis_date):
    """
    Update FCT_Stage_Determination with product, segment, customer, and PD term structure information from Ldn_Bank_Product_Info, 
    FSI_Product_Segment, Ldn_Customer_Info, and Ldn_PD_Term_Structure based on the provided mis_date.
    This function updates fields such as n_prod_segment, n_prod_name, n_prod_type, n_prod_desc, n_segment_skey,
    n_partner_name, n_party_type, n_pd_term_structure_skey, n_pd_term_structure_name, and n_pd_term_structure_desc for records with the given mis_date.
    :param mis_date: Date (fic_mis_date) in 'YYYY-MM-DD' format.
    :return: String, status of the update process ('1' for success, '0' for failure').
    """
    try:
        # Fetch all entries from FCT_Stage_Determination for the given mis_date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(fic_mis_date=mis_date).exclude(n_prod_code__isnull=True)

        # Use ThreadPoolExecutor to process updates in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_product_info_update, entry)
                for entry in stage_determination_entries
            ]

            # Wait for all threads to complete
            for future in futures:
                future.result()

        return '1'

    except Exception as e:
        print(f"Error during update process: {e}")
        return '0'

def process_product_info_update(entry):
    """
    Update product info, segment key, customer info, and PD term structure info for a single FCT_Stage_Determination entry.
    This function looks up the product information based on the n_prod_code and updates the entry accordingly.
    It also updates the n_segment_skey, customer info, and PD term structure info based on other tables.
    """
    # Update product information from Ldn_Bank_Product_Info
    try:
        product_info = Ldn_Bank_Product_Info.objects.get(v_prod_code=entry.n_prod_code)

        # Update fields in FCT_Stage_Determination
        entry.n_prod_segment = product_info.v_prod_segment
        entry.n_prod_name = product_info.v_prod_name
        entry.n_prod_type = product_info.v_prod_type
        entry.n_prod_desc = product_info.v_prod_desc

        # Save the updated entry
        entry.save(update_fields=['n_prod_segment', 'n_prod_name', 'n_prod_type', 'n_prod_desc'])

    except Ldn_Bank_Product_Info.DoesNotExist:
        print(f"Product info not found for code: {entry.n_prod_code}")
    except Exception as e:
        print(f"Error updating product info for entry {entry.n_prod_code}: {e}")
    
    # Update the segment key (n_segment_skey) using FSI_Product_Segment
    try:
        product_segment = FSI_Product_Segment.objects.get(
            v_prod_segment=entry.n_prod_segment,
            v_prod_type=entry.n_prod_type,
            v_prod_desc=entry.n_prod_desc
        )
        entry.n_segment_skey = product_segment.segment_id

        # Save the updated segment key
        entry.save(update_fields=['n_segment_skey'])

    except FSI_Product_Segment.DoesNotExist:
        print(f"No matching segment found for {entry.n_prod_segment}, {entry.n_prod_type}, {entry.n_prod_desc}")
    except Exception as e:
        print(f"Error updating segment key for entry {entry.n_prod_code}: {e}")

    # Update customer information (n_partner_name, n_party_type) using Ldn_Customer_Info
    try:
        customer_info = Ldn_Customer_Info.objects.get(v_party_id=entry.n_cust_ref_code)

        # Update customer fields in FCT_Stage_Determination
        entry.n_partner_name = customer_info.v_partner_name
        entry.n_party_type = customer_info.v_party_type

        # Save the updated customer information
        entry.save(update_fields=['n_partner_name', 'n_party_type'])

    except Ldn_Customer_Info.DoesNotExist:
        print(f"Customer info not found for customer reference: {entry.n_cust_ref_code}")
    except Exception as e:
        print(f"Error updating customer info for entry {entry.n_prod_code}: {e}")
    
    # First set n_pd_term_structure_skey = n_segment_skey
    try:
        entry.n_pd_term_structure_skey = entry.n_segment_skey
        entry.save(update_fields=['n_pd_term_structure_skey'])

    except Exception as e:
        print(f"Error updating n_pd_term_structure_skey for entry {entry.n_prod_code}: {e}")

    # Update n_pd_term_structure_name and n_pd_term_structure_desc using Ldn_PD_Term_Structure
    try:
        pd_term_structure = Ldn_PD_Term_Structure.objects.get(v_pd_term_structure_id=entry.n_pd_term_structure_skey)

        # Update PD term structure fields in FCT_Stage_Determination
        entry.n_pd_term_structure_name = pd_term_structure.v_pd_term_structure_name
        entry.n_pd_term_structure_desc = pd_term_structure.v_pd_term_structure_desc

        # Save the updated PD term structure info
        entry.save(update_fields=['n_pd_term_structure_name', 'n_pd_term_structure_desc'])

    except Ldn_PD_Term_Structure.DoesNotExist:
        print(f"PD Term Structure not found for term structure key: {entry.n_pd_term_structure_skey}")
    except Exception as e:
        print(f"Error updating PD term structure for entry {entry.n_prod_code}: {e}")
