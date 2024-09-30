from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
import matplotlib.pyplot as plt
import io
import  base64
from .models import *
from .forms import *

from .Functions.data import *
from .Functions.cashflow import *
from .Functions.calculate_cash_flows_ead import *
from .Functions.pd_interpolation import *
from .Functions.populate_stg_determination import *
from .Functions.determine_stage import *
from .Functions.cooling_period import *
from .Functions.update_stage_determination import *
from .Functions.assign_acc_pd_level import *
from .Functions.assign_acc_pd_term_level import *
from .Functions.populate_cashflows import *
from .Functions.pd_cumulative_term_str import *
from .Functions.calculate_fct_accrued_interest_and_ead import *
from .Functions.calculate_eir import *
from .Functions.update_fin_cashflw import *
from .Functions.calculate_cash_flow_rate_and_amount1 import *
from .Functions.cal_periodic_discount_Rate2 import *
from .Functions.cal_exp_cash_n_cash_shortfall3 import *
from .Functions.cal_forward_exposure4 import *
from .Functions.calculate_marginal_pd import *


from datetime import datetime




def dashboard_view(request):
    # Example data for financial graphs
    mis_date = '2024-08-31'  # Input date in 'YYYY-MM-DD' format
    
    #status = perform_interpolation(mis_date)
    #print(status)  # Should print '1' for success or '0' for failure
    #project_cash_flows(mis_date)
    #update_cash_flows_with_ead(mis_date)
    #Insert records into FCT_Stage_Determination with the numeric date
    #insert_fct_stage(mis_date)

    #determine stage
    #update_stage(mis_date)
    #process_cooling_period_for_accounts(mis_date)
    #update_stage_determination(mis_date)
    #update_stage_determination_accrued_interest_and_ead(mis_date)
    #update_stage_determination_eir(mis_date)
    #calculate_pd_for_accounts(mis_date)
    #insert_cash_flow_data(mis_date)
    #update_financial_cash_flow(mis_date,42)
    #update_cash_flow_with_pd_buckets(mis_date,42)
    #update_marginal_pd(mis_date,42)
    #calculate_expected_cash_flow(mis_date,42)
    #calculate_discount_factors(mis_date,42)
    #calculate_cashflow_fields(mis_date,42)
    calculate_forward_loss_fields(mis_date,42)

    return render(request, 'dashboard.html')



def app_list_view(request):
    context = {
        'title': 'Available Applications',
        # You can pass any additional context if needed
    }
    return render(request, 'app_list.html', context)

def ifrs9_home_view(request):
    context = {
        'title': ' Home',
        # You can pass any additional context if needed
    }
    return render(request, 'ifrs9_home.html', context)


def credit_risk_models_view(request):
    context = {
        'title': 'Credit Risk Models',
    }
    return render(request, 'models/credit_risk_models.html', context)

def cash_flow_generation_issues(request):
    context = {
        'title': 'Cash Flow Generation Issues and Solutions',
    }
    return render(request, 'models/cash_flow_generation_issues.html', context)

#####################
def cashflow_projection_view(request):
    if request.method == 'POST':
        fic_mis_date = request.POST.get('fic_mis_date')
        
        # Trigger the projection
        project_cash_flows(fic_mis_date)
        
        # Redirect to a success page
        return HttpResponseRedirect(reverse('projection_success'))
    
    return render(request, 'cashflow_projection.html')