from ast import Import
from django.shortcuts import render,redirect, get_object_or_404
from ..models import FCT_Reporting_Lines, ReportColumnConfig
from django.db.models import Max
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import pandas as pd
import numpy as np
import os
from openpyxl import Workbook
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def reporting_home(request):
    return render(request, 'reports/reporting.html')
def list_reports(request):
    # This view will render the list of available reports
    return render(request, 'reports/list_reports.html')

def view_results_and_extract(request):
    # Get the latest `fic_mis_date` and `n_run_key`
    latest_fic_mis_date = FCT_Reporting_Lines.objects.aggregate(Max('fic_mis_date'))['fic_mis_date__max']
    latest_n_run_key = FCT_Reporting_Lines.objects.aggregate(Max('n_run_key'))['n_run_key__max']
    
    # Fetch FIC MIS Date and Run Key from the request, default to latest if not provided
    fic_mis_date = request.GET.get('fic_mis_date', latest_fic_mis_date)
    n_run_key = request.GET.get('n_run_key', latest_n_run_key)

    # Ensure FIC MIS Date and Run Key are provided, these are mandatory
    if not fic_mis_date or not n_run_key:
        messages.error(request, "Both FIC MIS Date and Run Key are required.")
        return render(request, 'reports/report_view.html', {
            'selected_columns': [],
            'report_data': [],
            'filters': request.GET,
            'latest_fic_mis_date': latest_fic_mis_date,
            'latest_n_run_key': latest_n_run_key,
            'fic_mis_date': fic_mis_date,
            'n_run_key': n_run_key,
        })

    # Apply filters, ensuring FIC MIS Date and Run Key are always included
    filters = {
        'fic_mis_date': fic_mis_date,
        'n_run_key': n_run_key,
    }

    # Dynamically add optional filters if they have a valid value
    if request.GET.get('n_prod_code'):
        filters['n_prod_code'] = request.GET.get('n_prod_code')
    
    if request.GET.get('n_prod_type'):
        filters['n_prod_type'] = request.GET.get('n_prod_type')
    
    if request.GET.get('n_pd_term_structure_name'):
        filters['n_pd_term_structure_name'] = request.GET.get('n_pd_term_structure_name')

    if request.GET.get('n_curr_ifrs_stage_skey'):
        try:
            filters['n_curr_ifrs_stage_skey'] = int(request.GET.get('n_curr_ifrs_stage_skey'))
        except ValueError:
            messages.error(request, "Invalid IFRS Stage Key. Please enter a valid number.")
            return render(request, 'reports/report_view.html', {
                'selected_columns': [],
                'report_data': [],
                'filters': request.GET,
                'latest_fic_mis_date': latest_fic_mis_date,
                'latest_n_run_key': latest_n_run_key,
                'fic_mis_date': fic_mis_date,
                'n_run_key': n_run_key,
            })

    # Fetch the saved column mappings for the report
    report_config = get_object_or_404(ReportColumnConfig, report_name="default_report")
    selected_columns = report_config.selected_columns

    # Query the FCT_Reporting_Lines table using only the selected columns and applied filters
    report_data = FCT_Reporting_Lines.objects.filter(**filters).values(*selected_columns)

    # Paginate the report data
    paginator = Paginator(report_data, 25)  # Show 25 results per page
    page = request.GET.get('page', 1)

    try:
        paginated_report_data = paginator.page(page)
    except PageNotAnInteger:
        paginated_report_data = paginator.page(1)
    except EmptyPage:
        paginated_report_data = paginator.page(paginator.num_pages)

    # Pass the data and the selected columns to the template
    context = {
        'selected_columns': selected_columns,
        'report_data': paginated_report_data,  # Pass paginated data
        'filters': filters,
        'latest_fic_mis_date': latest_fic_mis_date,
        'latest_n_run_key': latest_n_run_key,
        'fic_mis_date': fic_mis_date,  # Pass FIC MIS Date to template
        'n_run_key': n_run_key,        # Pass Run Key to template
    }
    return render(request, 'reports/report_view.html', context)



def download_report(request):
    # Fetch the same filters as used in the view_results_and_extract
    filters = {
        'fic_mis_date': request.GET.get('fic_mis_date'),
        'n_run_key': request.GET.get('n_run_key'),
        'n_prod_code': request.GET.get('n_prod_code'),
        'n_prod_type': request.GET.get('n_prod_type'),
        'n_pd_term_structure_name': request.GET.get('n_pd_term_structure_name'),
        'n_curr_ifrs_stage_skey': request.GET.get('n_curr_ifrs_stage_skey'),
    }
    
    # Remove None values from filters
    filters = {k: v for k, v in filters.items() if v is not None}

    # Fetch the saved column mappings
    report_config = ReportColumnConfig.objects.get(report_name="default_report")
    selected_columns = report_config.selected_columns

    # Query the FCT_Reporting_Lines with the filters
    report_data = FCT_Reporting_Lines.objects.filter(**filters).values(*selected_columns)

    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'

    # Write the selected columns as the header
    writer = csv.writer(response)
    writer.writerow(selected_columns)

    # Write the data rows
    for row in report_data:
        writer.writerow([row[column] for column in selected_columns])

    return response


############################################

# Directory to save the CSV files
CSV_DIR = os.path.join(os.getcwd(), 'csv_files')

@require_http_methods(["GET", "POST"])
def ecl_main_filter_view(request):
    # Handle POST request (applying the filter)
    if request.method == 'POST':
        # Retrieve selected FIC MIS Date and Run Key from the form
        fic_mis_date = request.POST.get('fic_mis_date')
        n_run_key = request.POST.get('n_run_key')
        
        if fic_mis_date and n_run_key:
            # Store the selected filter values in session for later use
            request.session['fic_mis_date'] = fic_mis_date
            request.session['n_run_key'] = n_run_key

            # Retrieve filtered data based on the selected main filter values
            ecl_data = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date, n_run_key=n_run_key)

            # Convert the filtered data into a DataFrame
            ecl_data_df = pd.DataFrame(list(ecl_data.values()))

            # Convert date fields to strings
            if 'fic_mis_date' in ecl_data_df.columns:
                ecl_data_df['fic_mis_date'] = ecl_data_df['fic_mis_date'].astype(str)
            if 'd_maturity_date' in ecl_data_df.columns:
                ecl_data_df['d_maturity_date'] = ecl_data_df['d_maturity_date'].astype(str)

            # Create the directory if it doesn't exist
            if not os.path.exists(CSV_DIR):
                os.makedirs(CSV_DIR)

            # Save the data as a CSV file in the session (store the filename)
            csv_filename = os.path.join(CSV_DIR, f"ecl_data_{fic_mis_date}_{n_run_key}.csv")
            ecl_data_df.to_csv(csv_filename, index=False)
            request.session['csv_filename'] = csv_filename

            # Redirect to the sub-filter view
            return redirect('ecl_sub_filter_view')

    # Handle GET request
    fic_mis_dates = FCT_Reporting_Lines.objects.order_by('-fic_mis_date').values_list('fic_mis_date', flat=True).distinct()

    # Check for AJAX requests to dynamically update run key dropdown
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        field_name = request.GET.get('field')
        field_value = request.GET.get('value')

        if field_name == 'fic_mis_date':
            # Fetch run keys corresponding to the selected FIC MIS date
            n_run_keys = FCT_Reporting_Lines.objects.filter(fic_mis_date=field_value).order_by('-n_run_key').values_list('n_run_key', flat=True).distinct()
            return JsonResponse({'n_run_keys': list(n_run_keys)})

    # Render the main filter template with FIC MIS Dates
    return render(request, 'reports/ecl_summary_report.html', {'fic_mis_dates': fic_mis_dates})





@require_http_methods(["GET", "POST"])
def ecl_sub_filter_view(request):
    # Retrieve the CSV filename from the session
    csv_filename = request.session.get('csv_filename')

    # If no data is available, redirect to the main filter page
    if not csv_filename or not os.path.exists(csv_filename):
        return redirect('ecl_main_filter_view')

    # Load the data from the CSV file
    ecl_data_df = pd.read_csv(csv_filename)

    # Retrieve sub-filter form fields from the request
    n_prod_segment = request.GET.get('n_prod_segment')
    n_prod_type = request.GET.get('n_prod_type')
    n_stage_descr = request.GET.get('n_stage_descr')
    n_loan_type = request.GET.get('n_loan_type')

    # Apply sub-filters if provided
    if n_prod_segment:
        ecl_data_df = ecl_data_df[ecl_data_df['n_prod_segment'] == n_prod_segment]
    if n_prod_type:
        ecl_data_df = ecl_data_df[ecl_data_df['n_prod_type'] == n_prod_type]
    if n_stage_descr:
        ecl_data_df = ecl_data_df[ecl_data_df['n_stage_descr'] == n_stage_descr]
    if n_loan_type:
        ecl_data_df = ecl_data_df[ecl_data_df['n_loan_type'] == n_loan_type]

    # Retrieve the selected group by field from the request (GET or POST)
    group_by_field = request.GET.get('group_by_field', 'n_stage_descr')  # Default group by 'n_stage_descr'

    # Group the data by the selected field and sum the amounts, while also counting unique accounts
    grouped_data = (
        ecl_data_df.groupby(group_by_field)
        .agg({
            'n_exposure_at_default_ncy': 'sum',
            'n_exposure_at_default_rcy': 'sum',
            'n_12m_ecl_rcy': 'sum',
            'n_lifetime_ecl_rcy': 'sum',
            'n_account_number': pd.Series.nunique,  # Count unique accounts in each group
        })
        .reset_index()
        .to_dict(orient='records')
    )

    # Calculate grand totals
    grand_totals = {
        'n_exposure_at_default_ncy': ecl_data_df['n_exposure_at_default_ncy'].sum(),
        'n_exposure_at_default_rcy': ecl_data_df['n_exposure_at_default_rcy'].sum(),
        'n_12m_ecl_rcy': ecl_data_df['n_12m_ecl_rcy'].sum(),
        'n_lifetime_ecl_rcy': ecl_data_df['n_lifetime_ecl_rcy'].sum(),
        'n_account_number': ecl_data_df['n_account_number'].nunique(),  # Grand total for unique accounts
    }

    # Distinct values for sub-filters
    distinct_prod_segments = list(ecl_data_df['n_prod_segment'].unique())
    distinct_prod_types = list(ecl_data_df['n_prod_type'].unique())
    distinct_stage_descrs = list(ecl_data_df['n_stage_descr'].unique())
    distinct_loan_types = list(ecl_data_df['n_loan_type'].unique())

    # Store the grouped data and grand totals in the session for Excel export
    request.session['grouped_data'] = grouped_data
    request.session['group_by_field'] = group_by_field
    request.session['grand_totals'] = grand_totals

    # Render the sub-filter view template
    return render(request, 'reports/ecl_summary_report_sub.html', {
        'grouped_data': grouped_data,
        'group_by_field': group_by_field,
        'distinct_prod_segments': distinct_prod_segments,
        'distinct_prod_types': distinct_prod_types,
        'distinct_stage_descrs': distinct_stage_descrs,
        'distinct_loan_types': distinct_loan_types,
        'grand_totals': grand_totals,
    })



# Export to Excel dynamically based on the current filtered and grouped data
def export_ecl_report_to_excel(request):
    # Retrieve the filtered data and grand totals from session
    grouped_data = request.session.get('grouped_data', [])
    group_by_field = request.session.get('group_by_field', 'v_ccy_code')
    grand_totals = request.session.get('grand_totals', {})

    # Convert the grouped data into a pandas DataFrame
    df = pd.DataFrame(grouped_data)

    # Create a new Excel workbook and add a sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ECL Report"

    # Add the column headers dynamically based on the DataFrame columns
    headers = [group_by_field, "EAD Orig Currency ", 
               "EAD Reporting Currency ", 
               "12 Month Reporting ECL ", "Lifetime Reporting ECL"]
    ws.append(headers)

    # Add the grouped data to the sheet
    for row in dataframe_to_rows(df, index=False, header=False):
        ws.append(row)

    # Add the grand totals at the bottom
    ws.append(['Grand Total', grand_totals['n_exposure_at_default_ncy'], 
               grand_totals['n_exposure_at_default_rcy'], 
               grand_totals['n_12m_ecl_rcy'], 
               grand_totals['n_lifetime_ecl_rcy']])

    # Apply styling to the header row (first row)
    header_fill = PatternFill(start_color="2d5c8e", end_color="2d5c8e", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    alignment = Alignment(horizontal="center", vertical="center")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = alignment

    # Apply styling to the data rows (zebra striping)
    light_fill = PatternFill(start_color="d1e7dd", end_color="d1e7dd", fill_type="solid")
    for row in ws.iter_rows(min_row=2, max_row=len(grouped_data) + 2, min_col=1, max_col=5):
        for cell in row:
            cell.fill = light_fill

    # Apply bold font for the grand total row
    for cell in ws[len(grouped_data) + 2]:
        cell.font = Font(bold=True)

    # Adjust the column widths
    for column in ws.columns:
        max_length = max(len(str(cell.value)) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = max_length + 2

    # Create an HTTP response with an Excel attachment
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ecl_report.xlsx"'

    # Save the workbook to the response
    wb.save(response)
    return response




CSV_DIR = os.path.join(os.getcwd(), 'csv_files')

@require_http_methods(["GET", "POST"])
def ecl_reconciliation_main_filter_view(request):
    # Initialize an empty errors dictionary
    errors = {}

    # Handle POST request (applying the filter)
    if request.method == 'POST':
        # Retrieve selected FIC MIS Dates and Run Keys from the form
        fic_mis_date1 = request.POST.get('fic_mis_date1')
        run_key1 = request.POST.get('run_key1')
        fic_mis_date2 = request.POST.get('fic_mis_date2')
        run_key2 = request.POST.get('run_key2')

        # Validate that both dates and run keys are provided
        if not fic_mis_date1:
            errors['fic_mis_date1'] = 'Please select FIC MIS Date 1.'
        if not run_key1:
            errors['run_key1'] = 'Please select Run Key 1.'
        if not fic_mis_date2:
            errors['fic_mis_date2'] = 'Please select FIC MIS Date 2.'
        if not run_key2:
            errors['run_key2'] = 'Please select Run Key 2.'

        # If there are no errors, proceed to filtering
        if not errors:
            # Store the selected filter values in session for later use
            request.session['fic_mis_date1'] = fic_mis_date1
            request.session['run_key1'] = run_key1
            request.session['fic_mis_date2'] = fic_mis_date2
            request.session['run_key2'] = run_key2

            # Retrieve filtered data based on the selected main filter values
            ecl_data1 = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date1, n_run_key=run_key1)
            ecl_data2 = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date2, n_run_key=run_key2)

            # Convert the filtered data into a DataFrame
            ecl_data1_df = pd.DataFrame(list(ecl_data1.values()))
            ecl_data2_df = pd.DataFrame(list(ecl_data2.values()))

            # Convert date fields to strings for both DataFrames
            for df in [ecl_data1_df, ecl_data2_df]:
                if 'fic_mis_date' in df.columns:
                    df['fic_mis_date'] = df['fic_mis_date'].astype(str)
                if 'd_maturity_date' in df.columns:
                    df['d_maturity_date'] = df['d_maturity_date'].astype(str)

            # Create the directory if it doesn't exist
            if not os.path.exists(CSV_DIR):
                os.makedirs(CSV_DIR)

            # Save the data as CSV files in the session (store the filenames)
            csv_filename1 = os.path.join(CSV_DIR, f"ecl_data_{fic_mis_date1}_{run_key1}.csv")
            csv_filename2 = os.path.join(CSV_DIR, f"ecl_data_{fic_mis_date2}_{run_key2}.csv")
            
            ecl_data1_df.to_csv(csv_filename1, index=False)
            ecl_data2_df.to_csv(csv_filename2, index=False)
            # Store the filenames in the session and explicitly mark the session as modified
            request.session['csv_filename1'] = csv_filename1
            request.session['csv_filename2'] = csv_filename2
            request.session.modified = True
            # Redirect to the sub-filter view
            return redirect('ecl_reconciliation_sub_filter_view')

    # Handle GET request to load FIC MIS Dates
    fic_mis_dates = FCT_Reporting_Lines.objects.order_by('-fic_mis_date').values_list('fic_mis_date', flat=True).distinct()

    # Check for AJAX requests to dynamically update run key dropdown
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        field_name = request.GET.get('field')
        field_value = request.GET.get('value')

        if field_name == 'fic_mis_date':
            # Fetch run keys corresponding to the selected FIC MIS date
            n_run_keys = FCT_Reporting_Lines.objects.filter(fic_mis_date=field_value).order_by('-n_run_key').values_list('n_run_key', flat=True).distinct()
            return JsonResponse({'n_run_keys': list(n_run_keys)})

    # If there are errors or it's a GET request, render the form with any errors
    return render(request, 'reports/ecl_reconciliation_main_filter.html', {
        'fic_mis_dates': fic_mis_dates,
        'errors': errors  # Pass the errors to the template
    })




@require_http_methods(["GET", "POST"])
def ecl_reconciliation_sub_filter_view(request):
    # Retrieve the CSV filenames from the session
    csv_filename_1 = request.session.get('csv_filename1')
    csv_filename_2 = request.session.get('csv_filename2')

    # Check if the CSV files exist and display error if missing
    errors = []
    if not csv_filename_1:
        errors.append('The first dataset is missing. Please select a valid FIC MIS Date 1 and Run Key 1.')
    elif not os.path.exists(csv_filename_1):
        errors.append(f"The file for FIC MIS Date 1 does not exist: {csv_filename_1}")
    
    if not csv_filename_2:
        errors.append('The second dataset is missing. Please select a valid FIC MIS Date 2 and Run Key 2.')
    elif not os.path.exists(csv_filename_2):
        errors.append(f"The file for FIC MIS Date 2 does not exist: {csv_filename_2}")

    # If there are any errors, display them and do not proceed further
    if errors:
        for error in errors:
            messages.error(request, error)
        return render(request, 'reports/ecl_reconciliation_report_sub.html', {'errors': errors})

    # Load the data from the CSV files
    ecl_data_df_1 = pd.read_csv(csv_filename_1)
    ecl_data_df_2 = pd.read_csv(csv_filename_2)

    # Determine which dataframe has the higher and lower date based on fic_mis_date
    if ecl_data_df_1['fic_mis_date'].max() > ecl_data_df_2['fic_mis_date'].max():
        df_higher_date = ecl_data_df_1
        df_lower_date = ecl_data_df_2
    else:
        df_higher_date = ecl_data_df_2
        df_lower_date = ecl_data_df_1

    # Merge based on fic_mis_date and other keys
    merged_data = pd.merge(
        df_higher_date, 
        df_lower_date, 
        on=['fic_mis_date', 'n_run_key', 'n_stage_descr','v_ccy_code','n_prod_segment','n_prod_type','n_loan_type'],  
        how='outer', 
        suffixes=('_higher', '_lower')
    )

    # Fill NaN values with zeros for numeric fields
    merged_data.fillna({
        'n_exposure_at_default_ncy_higher': 0, 'n_exposure_at_default_ncy_lower': 0,
        'n_exposure_at_default_rcy_higher': 0, 'n_exposure_at_default_rcy_lower': 0,
        'n_12m_ecl_rcy_higher': 0, 'n_12m_ecl_rcy_lower': 0,
        'n_lifetime_ecl_rcy_higher': 0, 'n_lifetime_ecl_rcy_lower': 0
    }, inplace=True)

    # Apply sub-filters to the merged data
    v_ccy_code = request.GET.get('v_ccy_code')
    n_prod_segment = request.GET.get('n_prod_segment')
    n_prod_type = request.GET.get('n_prod_type')
    n_stage_descr = request.GET.get('n_stage_descr')
    n_loan_type = request.GET.get('n_loan_type')

    if v_ccy_code:
        merged_data = merged_data[merged_data['v_ccy_code'] == v_ccy_code]
    if n_prod_segment:
        merged_data = merged_data[merged_data['n_prod_segment'] == n_prod_segment]
    if n_prod_type:
        merged_data = merged_data[merged_data['n_prod_type'] == n_prod_type]
    if n_stage_descr:
        merged_data = merged_data[merged_data['n_stage_descr'] == n_stage_descr]
    if n_loan_type:
        merged_data = merged_data[merged_data['n_loan_type'] == n_loan_type]

    # Group by functionality after merging and applying filters
    group_by_field = request.GET.get('group_by_field', 'n_stage_descr') 

    # Group data and calculate the sum, while counting unique account numbers for higher and lower datasets
    grouped_data = merged_data.groupby(group_by_field).agg({
        'n_exposure_at_default_ncy_higher': 'sum',
        'n_exposure_at_default_ncy_lower': 'sum',
        'n_exposure_at_default_rcy_higher': 'sum',
        'n_exposure_at_default_rcy_lower': 'sum',
        'n_12m_ecl_rcy_higher': 'sum',
        'n_12m_ecl_rcy_lower': 'sum',
        'n_lifetime_ecl_rcy_higher': 'sum',
        'n_lifetime_ecl_rcy_lower': 'sum',
        # Counting distinct account numbers for higher and lower
        'n_account_number_higher': pd.Series.nunique,  
        'n_account_number_lower': pd.Series.nunique    
    }).reset_index()

    # Create new columns for account counts based on the 'n_account_number' column
    grouped_data['n_accounts_in_higher'] = grouped_data['n_account_number_higher']
    grouped_data['n_accounts_in_lower'] = grouped_data['n_account_number_lower']

    # Calculate differences (higher date minus lower date)
    grouped_data['difference_ead_ncy'] = grouped_data['n_exposure_at_default_ncy_higher'] - grouped_data['n_exposure_at_default_ncy_lower']
    grouped_data['difference_ead_rcy'] = grouped_data['n_exposure_at_default_rcy_higher'] - grouped_data['n_exposure_at_default_rcy_lower']
    grouped_data['difference_12m_ecl'] = grouped_data['n_12m_ecl_rcy_higher'] - grouped_data['n_12m_ecl_rcy_lower']
    grouped_data['difference_lifetime_ecl'] = grouped_data['n_lifetime_ecl_rcy_higher'] - grouped_data['n_lifetime_ecl_rcy_lower']

    # Status calculation based on 12-month ECL differences
    grouped_data['status_ead_ncy'] = grouped_data['difference_12m_ecl'].apply(
        lambda x: 'Increased' if x > 0 else ('Decreased' if x < 0 else 'No Change')
    )

    # Convert numeric columns to Python native types for JSON serialization
    grouped_data = grouped_data.applymap(lambda x: int(x) if isinstance(x, np.int64) else x)
    grouped_data = grouped_data.applymap(lambda x: float(x) if isinstance(x, np.float64) else x)

    # Convert to JSON-serializable format (a list of dictionaries) to store in session
    grouped_data_json = grouped_data.to_dict(orient='records')

    # Grand totals for columns and differences, also converted to Python native types
    grand_totals = {
        'n_exposure_at_default_ncy_higher': int(grouped_data['n_exposure_at_default_ncy_higher'].sum()),
        'n_exposure_at_default_rcy_higher': int(grouped_data['n_exposure_at_default_rcy_higher'].sum()),
        'n_12m_ecl_rcy_higher': int(grouped_data['n_12m_ecl_rcy_higher'].sum()),
        'n_lifetime_ecl_rcy_higher': int(grouped_data['n_lifetime_ecl_rcy_higher'].sum()),
        'n_exposure_at_default_ncy_lower': int(grouped_data['n_exposure_at_default_ncy_lower'].sum()),
        'n_exposure_at_default_rcy_lower': int(grouped_data['n_exposure_at_default_rcy_lower'].sum()),
        'n_12m_ecl_rcy_lower': int(grouped_data['n_12m_ecl_rcy_lower'].sum()),
        'n_lifetime_ecl_rcy_lower': int(grouped_data['n_lifetime_ecl_rcy_lower'].sum()),
        'difference_ead_rcy': int(grouped_data['difference_ead_rcy'].sum()),
        'difference_12m_ecl': int(grouped_data['difference_12m_ecl'].sum()),
        'difference_lifetime_ecl': int(grouped_data['difference_lifetime_ecl'].sum()),
        'n_accounts_in_higher': int(grouped_data['n_accounts_in_higher'].sum()),
        'n_accounts_in_lower': int(grouped_data['n_accounts_in_lower'].sum()),
    }

    # Store the grouped data and grand totals in the session for Excel export (JSON serializable format)
    request.session['grouped_data'] = grouped_data_json
    request.session['group_by_field'] = group_by_field
    request.session['grand_totals'] = grand_totals

    # Distinct values for sub-filters
    distinct_currency_codes = list(merged_data['v_ccy_code'].unique())
    distinct_prod_segments = list(merged_data['n_prod_segment'].unique())
    distinct_prod_types = list(merged_data['n_prod_type'].unique())
    distinct_stage_descrs = list(merged_data['n_stage_descr'].unique())
    distinct_loan_types = list(merged_data['n_loan_type'].unique())

    # Render the sub-filter view with the reconciliation data
    return render(request, 'reports/ecl_reconciliation_report_sub.html', {
        'grouped_data': grouped_data_json,  # Pass the JSON-serializable grouped data
        'group_by_field': group_by_field,
        'distinct_currency_codes': distinct_currency_codes,
        'distinct_prod_segments': distinct_prod_segments,
        'distinct_prod_types': distinct_prod_types,
        'distinct_stage_descrs': distinct_stage_descrs,
        'distinct_loan_types': distinct_loan_types,
        'grand_totals': grand_totals,
    })


@require_http_methods(["POST"])
def export_ecl_reconciliation_to_excel(request):
    # Retrieve the filtered data and grand totals from session
    grouped_data = request.session.get('grouped_data', [])
    group_by_field = request.session.get('group_by_field', 'n_stage_descr')
    grand_totals = request.session.get('grand_totals', {})
    fic_mis_date1 = request.session.get('fic_mis_date1', '')
    run_key1 = request.session.get('run_key1', '')
    fic_mis_date2 = request.session.get('fic_mis_date2', '')
    run_key2 = request.session.get('run_key2', '')

    # Create a new Excel workbook and add a sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "ECL Reconciliation Report"

    # Add the column headers dynamically based on the DataFrame columns
    headers = [
        group_by_field,
        f"EAD Orig Currency ({fic_mis_date1} - {run_key1})",
        f"EAD Reporting Currency ({fic_mis_date1} - {run_key1})",
        f"12 Month ECL ({fic_mis_date1} - {run_key1})",
        f"Lifetime ECL ({fic_mis_date1} - {run_key1})",
        f"EAD Orig Currency ({fic_mis_date2} - {run_key2})",
        f"EAD Reporting Currency ({fic_mis_date2} - {run_key2})",
        f"12 Month ECL ({fic_mis_date2} - {run_key2})",
        f"Lifetime ECL ({fic_mis_date2} - {run_key2})",
        "EAD Reporting Currency Difference",
        "12 Month ECL Difference",
        "Lifetime ECL Difference",
        f"Total Accounts ({fic_mis_date1})",
        f"Total Accounts ({fic_mis_date2})",
        "Status"
    ]
    ws.append(headers)

    # Add the grouped data to the sheet
    for row in grouped_data:
        ws.append([
            row.get(group_by_field, ''),
            row.get('n_exposure_at_default_ncy_higher', 0),
            row.get('n_exposure_at_default_rcy_higher', 0),
            row.get('n_12m_ecl_rcy_higher', 0),
            row.get('n_lifetime_ecl_rcy_higher', 0),
            row.get('n_exposure_at_default_ncy_lower', 0),
            row.get('n_exposure_at_default_rcy_lower', 0),
            row.get('n_12m_ecl_rcy_lower', 0),
            row.get('n_lifetime_ecl_rcy_lower', 0),
            row.get('difference_ead_rcy', 0),
            row.get('difference_12m_ecl', 0),
            row.get('difference_lifetime_ecl', 0),
            row.get('n_accounts_in_higher', 0),
            row.get('n_accounts_in_lower', 0),
            row.get('status_ead_ncy', 'No Change'),
        ])

    # Add the grand totals at the bottom
    ws.append([
        'Grand Total',
        grand_totals.get('n_exposure_at_default_ncy_higher', 0),
        grand_totals.get('n_exposure_at_default_rcy_higher', 0),
        grand_totals.get('n_12m_ecl_rcy_higher', 0),
        grand_totals.get('n_lifetime_ecl_rcy_higher', 0),
        grand_totals.get('n_exposure_at_default_ncy_lower', 0),
        grand_totals.get('n_exposure_at_default_rcy_lower', 0),
        grand_totals.get('n_12m_ecl_rcy_lower', 0),
        grand_totals.get('n_lifetime_ecl_rcy_lower', 0),
        grand_totals.get('difference_ead_rcy', 0),
        grand_totals.get('difference_12m_ecl', 0),
        grand_totals.get('difference_lifetime_ecl', 0),
        grand_totals.get('n_accounts_in_higher', 0),
        grand_totals.get('n_accounts_in_lower', 0),
        'No Change'
    ])

    # Apply styling to the header row (first row)
    header_fill = PatternFill(start_color="2d5c8e", end_color="2d5c8e", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    alignment = Alignment(horizontal="center", vertical="center")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = alignment

    # Apply styling to the data rows (zebra striping)
    light_fill = PatternFill(start_color="d1e7dd", end_color="d1e7dd", fill_type="solid")
    for row in ws.iter_rows(min_row=2, max_row=len(grouped_data) + 2, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.fill = light_fill

    # Apply bold font for the grand total row
    for cell in ws[len(grouped_data) + 2]:
        cell.font = Font(bold=True)

    # Adjust the column widths
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells if not isinstance(cell, openpyxl.cell.MergedCell))
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

    # Create an HTTP response with an Excel attachment
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ecl_reconciliation_report.xlsx"'

    # Save the workbook to the response
    wb.save(response)
    return response
