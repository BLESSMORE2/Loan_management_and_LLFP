from django.shortcuts import render, get_object_or_404, redirect
from django.forms import inlineformset_factory
from django.db import transaction
import threading
from django.contrib import messages
from ..models import Process, RunProcess,Function,FunctionExecutionStatus
from ..forms import ProcessForm, RunProcessForm
from django.db import transaction
from django.db.models import Q
from django.db.models import Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Max
from django.db.models import Min
from datetime import datetime
from django.utils import timezone
from django.utils.module_loading import import_string  # Used for dynamic function calling
import sys
from ..Functions.cashflow import *
from ..Functions.calculate_cash_flows_ead import *
from ..Functions.pd_interpolation import *
from ..Functions.populate_stg_determination import *
from ..Functions.determine_stage import *
from ..Functions.cooling_period import *
from ..Functions.update_stage_determination import *
from ..Functions.assign_acc_pd_level import *
from ..Functions.assign_acc_pd_term_level import *
from ..Functions.populate_cashflows import *
from ..Functions.pd_cumulative_term_str import *
from ..Functions.calculate_fct_accrued_interest_and_ead import *
from ..Functions.calculate_eir import *
from ..Functions.update_fin_cashflw import *
from ..Functions.calculate_cash_flow_rate_and_amount1 import *
from ..Functions.cal_periodic_discount_Rate2 import *
from ..Functions.cal_exp_cash_n_cash_shortfall3 import *
from ..Functions.cal_forward_exposure4 import *
from ..Functions.calculate_marginal_pd import *
from ..Functions.populate_reporting_table import *
from ..Functions.calculate_ecl import *

def operations_view(request):
    return render(request, 'operations/operations.html')



# List all processes
def process_list(request):
    processes = Process.objects.all()
    return render(request, 'operations/process_list.html', {'processes': processes})

# View the details of a specific process, including its associated functions and execution order
def process_detail(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    run_processes = RunProcess.objects.filter(process=process).order_by('order')  # Fetch functions in order
    return render(request, 'operations/process_detail.html', {'process': process, 'run_processes': run_processes})

# Create or edit a process
def create_process(request, process_id=None):
    """
    View to add or edit a process and its corresponding run processes.
    If process_id is provided, it's an edit; otherwise, it's an add.
    """
    RunProcessFormSet = inlineformset_factory(Process, RunProcess, form=RunProcessForm, extra=1, can_delete=True)

    
    process = Process()
    form_title = 'Create Process'

    if request.method == 'POST':
        form = ProcessForm(request.POST, instance=process)
        formset = RunProcessFormSet(request.POST)

        # Print the formset POST data for debugging
        print("Formset POST Data:", request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    process = form.save(commit=False)
                    process.save()  # Save the parent process object
                    print(f"Process saved: {process}")

                    # Handle multiple function and order values
                    for form in formset.forms:
                        functions = request.POST.getlist(form.add_prefix('function'))  # Fetch as list
                        orders = request.POST.getlist(form.add_prefix('order'))  # Fetch as list

                        print(f"Processing form: functions={functions}, orders={orders}")

                        # Loop over the multiple values and save each pair separately
                        if len(functions) == len(orders):
                            for function_id, order in zip(functions, orders):
                                if function_id and order:
                                    # Convert the function_id to a Function instance
                                    function_instance = Function.objects.get(pk=function_id)
                                    
                                    RunProcess.objects.create(
                                        process=process,
                                        function=function_instance,  # Save the Function instance
                                        order=order
                                    )
                                    print(f"Saved: function={function_instance}, order={order}")
                        else:
                            # Handle single function and order values
                            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                                function_instance = form.cleaned_data.get('function')
                                RunProcess.objects.create(
                                    process=process,
                                    function=function_instance,  # Save the Function instance
                                    order=form.cleaned_data.get('order')
                                )
                                print(f"Saved single: function={form.cleaned_data.get('function')}, order={form.cleaned_data.get('order')}")

                    messages.success(request, f'Process {"created" if not process_id else "updated"} successfully.')
                    return redirect('process_list')
            except Exception as e:
                messages.error(request, f"Error saving process: {str(e)}")
                print(f"Error: {e}")
        else:
            print("Form Errors:", form.errors)
            print("Formset Errors:", formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProcessForm(instance=process)
        formset = RunProcessFormSet(instance=process)

    return render(request, 'operations/create_process.html', {
        'form': form,
        'formset': formset,
        'title': form_title,
    })



def delete_process(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    if request.method == 'POST':
        try:
            process.delete()
            messages.success(request, 'Process deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting process: {e}')
        return redirect('process_list')
    return render(request, 'operations/delete_process.html', {'process': process})
##############################################################################################3
# Display and search for processes
def execute_process_view(request):
    query = request.GET.get('search', '')
    processes = Process.objects.filter(Q(process_name__icontains=query))

    return render(request, 'operations/execute_process.html', {
        'processes': processes,
        'query': query,
    })

# Handle execution
# Function to generate the process run ID and count


def generate_process_run_id(process, execution_date):
    """
    Generate a process_run_id in the format 'process_id_execution_date_run_number'.
    """
    # Format the execution date as YYYYMMDD
    execution_date_str = execution_date.strftime('%Y%m%d')
    
    # Base run ID: process_id + execution_date
    base_run_id = f"{process.process_name}_{execution_date_str}"
    
    # Check the database for existing entries with the same base_run_id
    existing_runs = FunctionExecutionStatus.objects.filter(process_run_id__startswith=base_run_id).order_by('-run_count')
    
    # Determine the next run count
    if existing_runs.exists():
        last_run_count = existing_runs[0].run_count
        next_run_count = last_run_count + 1
    else:
        next_run_count = 1
    
    # Generate the full process_run_id with the next run count
    process_run_id = f"{base_run_id}_{next_run_count}"
    
    return process_run_id, next_run_count


# Background function for running the process
def execute_functions_in_background(function_status_entries, process_run_id, mis_date):
    for status_entry in function_status_entries:
        function_name = status_entry.function.function_name
        print(f"Preparing to execute function: {function_name}")

        # Set the function status to "Ongoing"
        status_entry.status = 'Ongoing'
        status_entry.save()
        print(f"Function {function_name} marked as Ongoing.")

        # Execute the function
        try:
            if function_name in globals():
                print(f"Executing function: {function_name} with date {mis_date}")
                result = globals()[function_name](mis_date)  # Execute the function and capture the return value
                
                # Update status based on the return value (1 = Success, 0 = Failed)
                if result == 1 or result == '1' :
                    status_entry.status = 'Success'
                    print(f"Function {function_name} executed successfully.")
                elif result == 0 or result == '0':
                    status_entry.status = 'Failed'
                    print(f"Function {function_name} execution failed.")
                    status_entry.save()
                    break  # Stop execution if the function returns 0 (failed)
                else:
                    status_entry.status = 'Failed'
                    print(f"Unexpected return value {result} from function {function_name}.")
                    status_entry.save()
                    break  # Stop execution for any unexpected result
            else:
                status_entry.status = 'Failed'
                print(f"Function {function_name} not found in the global scope.")
                status_entry.save()
                break  # Stop execution if the function is not found

        except Exception as e:
            status_entry.status = 'Failed'
            print(f"Error executing {function_name}: {e}")
            status_entry.save()
            break  # Stop execution if any function throws an exception

        # Save the final status (Success or Failed)
        status_entry.save()
        print(f"Updated FunctionExecutionStatus for {function_name} to {status_entry.status}")


def run_process_execution(request):
    if request.method == 'POST':
        process_id = request.POST.get('process_id')
        selected_function_ids = request.POST.getlist('selected_functions')
        
        # Parse the execution date
        mis_date = request.POST.get('execution_date')
        execution_date = datetime.strptime(mis_date, '%Y-%m-%d')
        print(f"Execution date received: {mis_date}")
        
        # Retrieve the selected process
        process = get_object_or_404(Process, id=process_id)
        print(f"Process selected: {process.process_name} (ID: {process.id})")
        
        # Fetch the RunProcess records in order of their execution (by 'order' field)
        run_processes = RunProcess.objects.filter(id__in=selected_function_ids).order_by('order')
        print(f"Number of selected functions to execute: {run_processes.count()}")

        # Generate the process_run_id and run_count
        process_run_id, run_count = generate_process_run_id(process, execution_date)
        print(f"Generated process_run_id: {process_run_id}, run_count: {run_count}")

        # Save all functions as "Pending"
        function_status_entries = []
        for run_process in run_processes:
            status_entry = FunctionExecutionStatus.objects.create(
                process=process,
                function=run_process.function,
                reporting_date=mis_date,  # Use the original string date for the execution status
                status='Pending',  # Initially marked as "Pending"
                process_run_id=process_run_id,
                run_count=run_count,
                execution_order=run_process.order
            )
            function_status_entries.append(status_entry)
            print(f"Function {run_process.function.function_name} marked as Pending.")

        # Redirect to the monitoring page so the user can see the function statuses
        response = redirect('monitor_specific_process', process_run_id=process_run_id)

        # Execute functions in the background (thread)
        execution_thread = threading.Thread(target=execute_functions_in_background, args=(function_status_entries, process_run_id, mis_date))
        execution_thread.start()

        return response  # Redirects immediately while the background task executes
        

def get_process_functions(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    functions_html = render_to_string('operations/_functions_list.html', {'run_processes': process.run_processes.all()})
    return JsonResponse({'html': functions_html})



# Monitor running process page
def monitor_running_process_view(request):
    # Fetch distinct reporting dates and order by date descending
    available_dates = FunctionExecutionStatus.objects.order_by('-reporting_date').values_list('reporting_date', flat=True).distinct()

    # Get the selected date from the request
    selected_date = request.GET.get('selected_date', '')

    # Filter processes based on the selected date and ensure uniqueness by using annotation
    processes = []
    if selected_date:
        processes = (
            FunctionExecutionStatus.objects.filter(reporting_date=selected_date)
            .values('process__process_name', 'process_run_id')
            .annotate(latest_run=Max('process_run_id'))  # Annotate with the latest run ID
        )

        # Calculate overall status for each process
        for process in processes:
            process_run_id = process['process_run_id']
            function_statuses = FunctionExecutionStatus.objects.filter(process_run_id=process_run_id)

            # Determine the overall status based on the function statuses
            if function_statuses.filter(status='Failed').exists():
                process['overall_status'] = 'Failed'
            elif function_statuses.filter(status='Ongoing').exists():
                process['overall_status'] = 'Ongoing'
            else:
                process['overall_status'] = 'Success'

    context = {
        'selected_date': selected_date,
        'processes': processes,
        'available_dates': available_dates,
    }
    return render(request, 'operations/monitor_running_process.html', context)



def monitor_specific_process(request, process_run_id):
    # Fetch the specific process run by its ID
    process_statuses = FunctionExecutionStatus.objects.filter(process_run_id=process_run_id)

    context = {
        'process_statuses': process_statuses,
        'process_run_id': process_run_id,
    }
    return render(request, 'operations/monitor_specific_process.html', context)

def get_updated_status_table(request):
    process_run_id = request.GET.get('process_run_id')
    
    # Get all statuses related to the process_run_id
    function_statuses = FunctionExecutionStatus.objects.filter(process_run_id=process_run_id) \
                            .select_related('process', 'function') \
                            .annotate(order=models.F('function__runprocess__order')) \
                            .order_by('order')

    # Return the partial template with the updated table
    return render(request, 'operations/status_table.html', {'function_statuses': function_statuses})


def get_process_function_status(request, process_run_id):
    run_processes = FunctionExecutionStatus.objects.filter(process_run_id=process_run_id).order_by('execution_order')  # ordering by execution order
    functions_html = render_to_string('operations/_function_status_list.html', {'run_processes': run_processes})
    return JsonResponse({'html': functions_html})
