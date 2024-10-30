from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ..models import Fsi_Interest_Method
from ..forms import InterestMethodForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin


@login_required
def cashflow_projections(request):
    # This view will render the page that shows two options: Documentation and Interest Method
    context = {
        'title': 'Cashflow Projections',
        # No need to pass the URLs from the view, as they're now hardcoded in the HTML
    }
    return render(request, 'cashflow_projections/index.html', context)

@login_required
def cashflow_projections_documentation(request):
    # You can pass any context data if needed
    context = {
        'title': 'Cash Flow Generation Issues and Solutions',
    }
    return render(request, 'cashflow_projections/cash_flow_generation_issues.html', context)



# List View

class InterestMethodListView(LoginRequiredMixin,ListView):
    model = Fsi_Interest_Method
    template_name = 'cashflow_projections/interest_method_list.html'
    context_object_name = 'methods'

# Create View
class InterestMethodCreateView(LoginRequiredMixin,CreateView):
    model = Fsi_Interest_Method
    form_class = InterestMethodForm
    template_name = 'cashflow_projections/interest_method_form.html'
    success_url = reverse_lazy('interest_method_list')

    def form_valid(self, form):
        messages.success(self.request, "Interest method added successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error adding the interest method. Please try again.")
        return super().form_invalid(form)

# Update View
class InterestMethodUpdateView(LoginRequiredMixin,UpdateView):
    model = Fsi_Interest_Method
    form_class = InterestMethodForm
    template_name = 'cashflow_projections/interest_method_form.html'
    success_url = reverse_lazy('interest_method_list')

    def form_valid(self, form):
        messages.success(self.request, "Interest method updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the interest method. Please try again.")
        return super().form_invalid(form)

# Delete View
class InterestMethodDeleteView(LoginRequiredMixin,DeleteView):
    model = Fsi_Interest_Method
    template_name = 'cashflow_projections/interest_method_confirm_delete.html'
    success_url = reverse_lazy('interest_method_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Interest method deleted successfully!")
        return super().delete(request, *args, **kwargs)