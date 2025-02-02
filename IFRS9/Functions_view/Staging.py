from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
import matplotlib.pyplot as plt
import io
import  base64
from ..models import *
from ..forms import *
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin





@login_required
def configure_stages(request):
    title = "Stage Determination and Classification Configurations"
    return render(request, 'staging/staging_options.html', {'title': title})

@login_required
def staging_using_ratings(request):
    title = "Staging Using Ratings"
    # Additional logic for staging using ratings
    return render(request, 'staging/staging_using_ratings.html', {'title': title})

@login_required
def staging_using_delinquent_days(request):
    title = "Staging Using Delinquent Days"
    # Additional logic for staging using delinquent days
    return render(request, 'staging/staging_using_delinquent_days.html', {'title': title})


def stage_reassignment(request):
    title = "Stage Reassignment"
    # Additional logic for stage reassignment can go here
    return render(request, 'staging/stage_reassignment.html', {'title': title})


# List View for all credit ratings
class CreditRatingStageListView(LoginRequiredMixin,ListView):
    model = FSI_CreditRating_Stage
    template_name = 'staging/staging_using_ratings.html'  # Points to your template
    context_object_name = 'ratings'  # This will be used in the template
    paginate_by = 10  # You can adjust or remove pagination if not needed

    def get_queryset(self):
        queryset = FSI_CreditRating_Stage.objects.all()
        return queryset


# Create View for adding a new credit rating
class CreditRatingStageCreateView(LoginRequiredMixin, CreateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Credit rating successfully added!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

# Update View for editing a credit rating
class CreditRatingStageUpdateView(LoginRequiredMixin, UpdateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Credit rating successfully updated!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

# Delete View for deleting a credit rating
class CreditRatingStageDeleteView(LoginRequiredMixin,DeleteView):
    model = FSI_CreditRating_Stage
    template_name = 'staging/creditrating_stage_confirm_delete.html'
    success_url = reverse_lazy('creditrating_stage_list')

    def delete(self, request, *args, **kwargs):
        # Add success message
        messages.success(self.request, "Credit rating successfully deleted!")
        return super().delete(request, *args, **kwargs)


##DPD staging

class DPDStageMappingListView(LoginRequiredMixin,ListView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_list.html'
    context_object_name = 'dpd_mappings'
    paginate_by = 10

class DPDStageMappingCreateView(LoginRequiredMixin, CreateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "DPD Stage Mapping successfully added!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class DPDStageMappingUpdateView(LoginRequiredMixin, UpdateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "DPD Stage Mapping successfully updated!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class DPDStageMappingDeleteView(LoginRequiredMixin,DeleteView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_confirm_delete.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "DPD Stage Mapping successfully deleted!")
        return super().delete(request, *args, **kwargs)


#CoolingPeriodDefinition

class CoolingPeriodDefinitionListView(LoginRequiredMixin,ListView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_list.html'
    context_object_name = 'cooling_periods'
    paginate_by = 10

class CoolingPeriodDefinitionCreateView(LoginRequiredMixin, CreateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Cooling period definition successfully added!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class CoolingPeriodDefinitionUpdateView(LoginRequiredMixin, UpdateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Cooling period definition successfully updated!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class CoolingPeriodDefinitionDeleteView(LoginRequiredMixin,DeleteView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_confirm_delete.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cooling period definition successfully deleted!")
        return super().delete(request, *args, **kwargs)
    
class DimDelinquencyBandListView(LoginRequiredMixin,ListView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dim_delinquency_band_list.html'
    context_object_name = 'delinquency_bands'
    paginate_by = 10

class DimDelinquencyBandCreateView(LoginRequiredMixin, CreateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Delinquency band successfully added!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class DimDelinquencyBandUpdateView(LoginRequiredMixin, UpdateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Delinquency band successfully updated!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class DimDelinquencyBandDeleteView(LoginRequiredMixin,DeleteView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dim_delinquency_band_confirm_delete.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Delinquency band successfully deleted!")
        return super().delete(request, *args, **kwargs)
    
class CreditRatingCodeBandListView(LoginRequiredMixin,ListView):
    model = Credit_Rating_Code_Band
    template_name = 'staging/credit_rating_code_band_list.html'
    context_object_name = 'rating_codes'
    paginate_by = 10

class CreditRatingCodeBandCreateView(LoginRequiredMixin, CreateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Credit rating code successfully added!")
            return response
        except IntegrityError as e:
            # Handle unique constraint violations or other database integrity issues
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add a general error message for validation errors
        messages.error(self.request, "There were errors in the form. Please correct them below.")
        return super().form_invalid(form)

class CreditRatingCodeBandUpdateView(LoginRequiredMixin, UpdateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Credit rating code successfully updated!")
            return response
        except IntegrityError as e:
            # Handle database integrity errors, like duplicate entries
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other exceptions
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

class CreditRatingCodeBandDeleteView(LoginRequiredMixin,DeleteView):
    model = Credit_Rating_Code_Band
    template_name = 'staging/credit_rating_code_band_confirm_delete.html'
    success_url = reverse_lazy('credit_rating_code_band_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Credit rating code successfully deleted!")
        return super().delete(request, *args, **kwargs)
    


#stage reassignment
# Map for stage descriptions based on the selected stage key
# Map for stage descriptions based on the selected stage key
STAGE_DESCRIPTION_MAP = {
    1: 'Stage 1',
    2: 'Stage 2',
    3: 'Stage 3',
}



@login_required
def stage_reassignment(request): 
    filter_form = StageReassignmentFilterForm(request.GET or None)
    records = None

    # Fetch available Reporting Dates in descending order
    fic_mis_dates = FCT_Reporting_Lines.objects.values_list('fic_mis_date', flat=True).distinct().order_by('-fic_mis_date')

    try:
        if filter_form.is_valid():
            fic_mis_date = filter_form.cleaned_data.get('fic_mis_date')
            n_account_number = filter_form.cleaned_data.get('n_account_number')
            n_cust_ref_code = filter_form.cleaned_data.get('n_cust_ref_code')

            # Filter logic
            records = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date, n_account_number=n_account_number)
            if n_cust_ref_code:
                records = records.filter(n_cust_ref_code=n_cust_ref_code)

            # Check if records are empty and set an appropriate message
            if not records.exists():
                messages.warning(request, "No data records were retrieved. The query condition returned zero records.")

        if request.method == "POST":
            stage_form = StageReassignmentForm(request.POST)
            if stage_form.is_valid():
                with transaction.atomic():  # Use atomic transaction to ensure database integrity
                    # Loop through the records and update the stages
                    for record in records:
                        stage_key = request.POST.get(f"n_curr_ifrs_stage_skey_{record.n_account_number}")
                        if stage_key:
                            record.n_curr_ifrs_stage_skey = int(stage_key)
                            record.n_stage_descr = STAGE_DESCRIPTION_MAP.get(int(stage_key))
                            record.save()

                    messages.success(request, "Stages reassigned successfully!")
            else:
                messages.error(request, "Invalid data provided.")

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    # Use this check instead of is_ajax()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Return the partial HTML if the request is via AJAX
        return render(request, 'staging/partials/stage_reassignment_table.html', {
            'records': records,
            'filter_form': filter_form,
            'stage_form': StageReassignmentForm()
        })

    # For non-AJAX requests, return the full page
    return render(request, 'staging/stage_reassignment.html', {
        'records': records,
        'filter_form': filter_form,
        'stage_form': StageReassignmentForm(),
        'fic_mis_dates': fic_mis_dates
    })
