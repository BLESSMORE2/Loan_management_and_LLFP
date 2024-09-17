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
from .Functions.pd_interpolation import *
from .Functions.populate_stg_determination import *
from datetime import datetime




def dashboard_view(request):
    # Example data for financial graphs
    mis_date = '2024-08-31'  # Input date in 'YYYY-MM-DD' format
    
    status = perform_interpolation(mis_date)
    print(status)  # Should print '1' for success or '0' for failure

    # Insert records into FCT_Stage_Determination with the numeric date
    insert_fct_stage(mis_date)

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