from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *

def update_stage_determination(mis_date):
    """
    Update FCT_Stage_Determination with product, segment, customer, delinquency band,
    and PD term structure information based on the provided mis_date.
    :param mis_date: Date (fic_mis_date) in 'YYYY-MM-DD' format.
    :return: String, status of the update process ('1' for success, '0' for failure').
    """
    try:
        # Fetch all entries from FCT_Stage_Determination for the given mis_date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(fic_mis_date=mis_date).exclude(n_prod_code__isnull=True)

        if not stage_determination_entries.exists():
            print(f"No stage determination entries found for mis_date {mis_date}.")
            return '0'  # Return '0' if no records are found

        # Use ThreadPoolExecutor to process updates in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_product_info_update, entry)
                for entry in stage_determination_entries
            ]

            # Process each future and catch any exceptions
            for future in futures:
                try:
                    future.result()  # Raises any exception that occurred in the thread
                except Exception as exc:
                    print(f"Error during update for an entry: {exc}")
                    return '0'  # Return '0' if any thread encounters an error

        return '1'  # Return '1' on successful completion

    except Exception as e:
        print(f"Error during update process: {e}")
        return '0'  # Return '0' in case of any exception


def process_product_info_update(entry):
    """
    Update product info, segment key, customer info, delinquency band, and PD term structure info
    for a single FCT_Stage_Determination entry.
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
        print(f"Updated product info for entry {entry.n_prod_code}: n_prod_segment={entry.n_prod_segment}, "
              f"n_prod_name={entry.n_prod_name}, n_prod_type={entry.n_prod_type}, n_prod_desc={entry.n_prod_desc}")

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
        print(f"Updated segment key for entry {entry.n_prod_code}: n_segment_skey={entry.n_segment_skey}")

    except FSI_Product_Segment.DoesNotExist:
        print(f"No matching segment found for {entry.n_prod_segment}, {entry.n_prod_type}, {entry.n_prod_desc}")
    except Exception as e:
        print(f"Error updating segment key for entry {entry.n_prod_code}: {e}")

    # Update collateral amount only if n_collateral_amount is null or zero
    if entry.n_collateral_amount is None or entry.n_collateral_amount == 0:
        try:
            # Find collateral data from LgdCollateral using v_cust_ref_code and fic_mis_date
            collateral = LgdCollateral.objects.get(v_cust_ref_code=entry.n_cust_ref_code, fic_mis_date=entry.fic_mis_date)

            # Update n_collateral_amount with the total from LgdCollateral
            entry.n_collateral_amount = collateral.total
            entry.save(update_fields=['n_collateral_amount'])
            print(f"Updated collateral amount for entry {entry.n_account_number}: n_collateral_amount={entry.n_collateral_amount}")

        except LgdCollateral.DoesNotExist:
            print(f"No collateral data found for customer {entry.n_cust_ref_code} and mis_date {entry.fic_mis_date}")
        except Exception as e:
            print(f"Error updating collateral amount for entry {entry.n_account_number}: {e}")


    # Update delinquency band code based on n_delinquent_days and v_amrt_term_unit
    try:
        delinquency_band = Dim_Delinquency_Band.objects.get(
            n_delq_lower_value__lte=entry.n_delinquent_days,
            n_delq_upper_value__gte=entry.n_delinquent_days,
            v_amrt_term_unit=entry.v_amrt_term_unit
        )
        entry.n_delq_band_code = delinquency_band.n_delq_band_code
        entry.save(update_fields=['n_delq_band_code'])
        print(f"Updated delinquency band for entry {entry.n_account_number}: n_delq_band_code={entry.n_delq_band_code}")

    except Dim_Delinquency_Band.DoesNotExist:
        print(f"No matching delinquency band found for account {entry.n_account_number} with {entry.n_delinquent_days} delinquent days")
    except Exception as e:
        print(f"Error updating delinquency band for account {entry.n_account_number}: {e}")

    # Update customer information (n_partner_name, n_party_type) using Ldn_Customer_Info
    try:
        customer_info = Ldn_Customer_Info.objects.get(v_party_id=entry.n_cust_ref_code)

        # Update customer fields in FCT_Stage_Determination
        entry.n_partner_name = customer_info.v_partner_name
        entry.n_party_type = customer_info.v_party_type

        # Save the updated customer information
        entry.save(update_fields=['n_partner_name', 'n_party_type'])
        print(f"Updated customer info for entry {entry.n_prod_code}: n_partner_name={entry.n_partner_name}, "
              f"n_party_type={entry.n_party_type}")

    except Ldn_Customer_Info.DoesNotExist:
        print(f"Customer info not found for customer reference: {entry.n_cust_ref_code}")
    except Exception as e:
        print(f"Error updating customer info for entry {entry.n_prod_code}: {e}")

    # First set n_pd_term_structure_skey = n_segment_skey
    try:
        entry.n_pd_term_structure_skey = entry.n_segment_skey
        entry.save(update_fields=['n_pd_term_structure_skey'])
        print(f"Updated n_pd_term_structure_skey for entry {entry.n_prod_code}: n_pd_term_structure_skey={entry.n_pd_term_structure_skey}")

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
        print(f"Updated PD term structure for entry {entry.n_prod_code}: n_pd_term_structure_name={entry.n_pd_term_structure_name}, "
              f"n_pd_term_structure_desc={entry.n_pd_term_structure_desc}")

    except Ldn_PD_Term_Structure.DoesNotExist:
        print(f"PD Term Structure not found for term structure key: {entry.n_pd_term_structure_skey}")
    except Exception as e:
        print(f"Error updating PD term structure for entry {entry.n_prod_code}: {e}")

    # Update rating code using Ldn_Customer_Rating_Detail
    try:
        # Fetch the rating code from Ldn_Customer_Rating_Detail using fic_mis_date and n_cust_ref_code (v_party_id)
        rating_detail = Ldn_Customer_Rating_Detail.objects.get(
            fic_mis_date=entry.fic_mis_date,
            v_party_cd=entry.n_cust_ref_code  # Using n_cust_ref_code directly
        )

        # Update the credit rating code only if it is None
        if entry.n_credit_rating_code is None:
            entry.n_credit_rating_code = rating_detail.v_rating_code

            # Save the updated rating code
            entry.save(update_fields=['n_credit_rating_code'])
            print(f"Updated n_credit_rating_code for entry {entry.n_account_number}: n_credit_rating_code={entry.n_credit_rating_code}")
        else:
            print(f"n_credit_rating_code already exists for entry {entry.n_account_number}: {entry.n_credit_rating_code}")

    except Ldn_Customer_Rating_Detail.DoesNotExist:
        print(f"Rating detail not found for customer {entry.n_cust_ref_code} and fic_mis_date {entry.fic_mis_date}")
    except Exception as e:
        print(f"Error updating rating code for entry {entry.n_prod_code}: {e}")

    # Calculate and update v_acct_rating_movement
    try:
        if entry.n_org_credit_score is not None and entry.n_curr_credit_score is not None:
            entry.n_acct_rating_movement = entry.n_org_credit_score - entry.n_curr_credit_score
            entry.save(update_fields=['n_acct_rating_movement'])
            print(f"Updated v_acct_rating_movement for entry {entry.n_account_number}: v_acct_rating_movement={entry.n_acct_rating_movement}")
        else:
            print(f"Credit score data missing for entry {entry.n_account_number}, cannot calculate v_acct_rating_movement")
    
    except Exception as e:
        print(f"Error calculating v_acct_rating_movement for entry {entry.n_account_number}: {e}")
