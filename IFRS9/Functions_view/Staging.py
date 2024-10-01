from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
import matplotlib.pyplot as plt
import io
import  base64
from ..models import *
from ..forms import *
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction





def configure_stages(request):
    title = "Stage Determination and Classification Configurations"
    return render(request, 'staging/staging_options.html', {'title': title})

def staging_using_ratings(request):
    title = "Staging Using Ratings"
    # Additional logic for staging using ratings
    return render(request, 'staging/staging_using_ratings.html', {'title': title})

def staging_using_delinquent_days(request):
    title = "Staging Using Delinquent Days"
    # Additional logic for staging using delinquent days
    return render(request, 'staging/staging_using_delinquent_days.html', {'title': title})

def stage_reassignment(request):
    title = "Stage Reassignment"
    # Additional logic for stage reassignment can go here
    return render(request, 'staging/stage_reassignment.html', {'title': title})


# List View for all credit ratings
class CreditRatingStageListView(ListView):
    model = FSI_CreditRating_Stage
    template_name = 'staging/staging_using_ratings.html'  # Points to your template
    context_object_name = 'ratings'  # This will be used in the template
    paginate_by = 10  # You can adjust or remove pagination if not needed

    def get_queryset(self):
        queryset = FSI_CreditRating_Stage.objects.all()
        return queryset


# Create View for adding a new credit rating
class CreditRatingStageCreateView(CreateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')

    def form_valid(self, form):
        # Add success message
        messages.success(self.request, "Credit rating successfully added!")
        return super().form_valid(form)

# Update View for editing a credit rating
class CreditRatingStageUpdateView(UpdateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')
    def form_valid(self, form):
        # Add success message
        messages.success(self.request, "Credit rating successfully updated!")
        return super().form_valid(form)

# Delete View for deleting a credit rating
class CreditRatingStageDeleteView(DeleteView):
    model = FSI_CreditRating_Stage
    template_name = 'staging/creditrating_stage_confirm_delete.html'
    success_url = reverse_lazy('creditrating_stage_list')

    def delete(self, request, *args, **kwargs):
        # Add success message
        messages.success(self.request, "Credit rating successfully deleted!")
        return super().delete(request, *args, **kwargs)


##DPD staging

class DPDStageMappingListView(ListView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_list.html'
    context_object_name = 'dpd_mappings'
    paginate_by = 10

class DPDStageMappingCreateView(CreateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, "DPD Stage Mapping successfully added!")
        return super().form_valid(form)

class DPDStageMappingUpdateView(UpdateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, "DPD Stage Mapping successfully updated!")
        return super().form_valid(form)

class DPDStageMappingDeleteView(DeleteView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_confirm_delete.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "DPD Stage Mapping successfully deleted!")
        return super().delete(request, *args, **kwargs)


#CoolingPeriodDefinition

class CoolingPeriodDefinitionListView(ListView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_list.html'
    context_object_name = 'cooling_periods'
    paginate_by = 10

class CoolingPeriodDefinitionCreateView(CreateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def form_valid(self, form):
        messages.success(self.request, "Cooling period definition successfully added!")
        return super().form_valid(form)

class CoolingPeriodDefinitionUpdateView(UpdateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def form_valid(self, form):
        messages.success(self.request, "Cooling period definition successfully updated!")
        return super().form_valid(form)

class CoolingPeriodDefinitionDeleteView(DeleteView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_confirm_delete.html'
    success_url = reverse_lazy('cooling_period_definitions')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cooling period definition successfully deleted!")
        return super().delete(request, *args, **kwargs)
    
class DimDelinquencyBandListView(ListView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dim_delinquency_band_list.html'
    context_object_name = 'delinquency_bands'
    paginate_by = 10

class DimDelinquencyBandCreateView(CreateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def form_valid(self, form):
        messages.success(self.request, "Delinquency band successfully added!")
        return super().form_valid(form)

class DimDelinquencyBandUpdateView(UpdateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def form_valid(self, form):
        messages.success(self.request, "Delinquency band successfully updated!")
        return super().form_valid(form)

class DimDelinquencyBandDeleteView(DeleteView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dim_delinquency_band_confirm_delete.html'
    success_url = reverse_lazy('dim_delinquency_band_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Delinquency band successfully deleted!")
        return super().delete(request, *args, **kwargs)
    
class CreditRatingCodeBandListView(ListView):
    model = Credit_Rating_Code_Band
    template_name = 'staging/credit_rating_code_band_list.html'
    context_object_name = 'rating_codes'
    paginate_by = 10

class CreditRatingCodeBandCreateView(CreateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')

    def form_valid(self, form):
        messages.success(self.request, "Credit rating code successfully added!")
        return super().form_valid(form)

class CreditRatingCodeBandUpdateView(UpdateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')

    def form_valid(self, form):
        messages.success(self.request, "Credit rating code successfully updated!")
        return super().form_valid(form)

class CreditRatingCodeBandDeleteView(DeleteView):
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

def stage_reassignment(request):
    filter_form = StageReassignmentFilterForm(request.GET or None)
    records = None

    try:
        if filter_form.is_valid():
            fic_mis_date = filter_form.cleaned_data.get('fic_mis_date')
            n_cust_ref_code = filter_form.cleaned_data.get('n_cust_ref_code')
            n_party_type = filter_form.cleaned_data.get('n_party_type')
            n_account_number = filter_form.cleaned_data.get('n_account_number')
            n_partner_name = filter_form.cleaned_data.get('n_partner_name')

            # Filter logic
            records = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
            if n_cust_ref_code:
                records = records.filter(n_cust_ref_code=n_cust_ref_code)
            if n_party_type:
                records = records.filter(n_party_type=n_party_type)
            if n_account_number:
                records = records.filter(n_account_number=n_account_number)
            if n_partner_name:
                records = records.filter(n_partner_name=n_partner_name)

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
        'stage_form': StageReassignmentForm()
    })
