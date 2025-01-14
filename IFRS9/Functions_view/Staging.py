from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
import matplotlib.pyplot as plt
import io
import  base64
from ..models import *
from ..forms import *
from Users.models import AuditTrail  # Import AuditTrail model
from django.utils.timezone import now  # For timestamping
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required

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
class CreditRatingStageCreateView(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')
    permission_required = 'IFRS9.add_credit_rating_stage'

    def form_valid(self, form):
        try:
            # Set the created_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()

            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_CreditRating_Stage',
                action='create',
                object_id=instance.pk,
                change_description=f"Created Credit Rating Stage: Credit Rating - {instance.credit_rating}, Stage - {instance.stage}",
                timestamp=now(),
            )
            
            messages.success(self.request, "Credit rating successfully added!")
            return super().form_valid(form)
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
class CreditRatingStageUpdateView(LoginRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = FSI_CreditRating_Stage
    form_class = CreditRatingStageForm
    template_name = 'staging/creditrating_stage_form.html'
    success_url = reverse_lazy('creditrating_stage_list')
    permission_required = 'IFRS9.change_credit_rating_stage'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_CreditRating_Stage',
                action='update',
                object_id=instance.pk,
                change_description=f"Updated Credit Rating Stage: Credit Rating - {instance.credit_rating}, Stage - {instance.stage}",
                timestamp=now(),
            )

            messages.success(self.request, "Credit rating successfully updated!")
            return super().form_valid(form)
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
# Delete View for deleting a credit rating
class CreditRatingStageDeleteView(LoginRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = FSI_CreditRating_Stage
    template_name = 'staging/creditrating_stage_confirm_delete.html'
    success_url = reverse_lazy('creditrating_stage_list')
    permission_required = 'IFRS9.delete_credit_rating_stage'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_CreditRating_Stage',
                action='delete',
                object_id=instance.pk,
                change_description=f"Deleted Credit Rating Stage: Credit Rating - {instance.credit_rating}, Stage - {instance.stage}",
                timestamp=now(),
            )

            messages.success(self.request, "Credit rating successfully deleted!")
        except Exception as e:
            messages.error(self.request, f"Error logging deletion: {e}")

        return super().delete(request, *args, **kwargs)

##DPD staging

class DPDStageMappingListView(LoginRequiredMixin,ListView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_list.html'
    context_object_name = 'dpd_mappings'
    paginate_by = 10

class DPDStageMappingCreateView(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')
    permission_required = 'IFRS9.add_dpd_stage_mapping'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()
            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_DPD_Stage_Mapping',
                action='create',
                object_id=instance.pk,
                change_description=(
                    f"Created DPD Stage Mapping: Payment Frequency - {instance.payment_frequency}, "
                    f"Stage 1 Threshold - {instance.stage_1_threshold}, "
                    f"Stage 2 Threshold - {instance.stage_2_threshold}, "
                    f"Stage 3 Threshold - {instance.stage_3_threshold}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "DPD Stage Mapping successfully added!")
            return super().form_valid(form)
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

class DPDStageMappingUpdateView(LoginRequiredMixin,PermissionRequiredMixin, UpdateView):
    model = FSI_DPD_Stage_Mapping
    fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
    template_name = 'staging/dpd_stage_mapping_form.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')
    permission_required = 'IFRS9.change_dpd_stage_mapping'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_DPD_Stage_Mapping',
                action='update',
                object_id=instance.pk,
                change_description=(
                    f"Updated DPD Stage Mapping: Payment Frequency - {instance.payment_frequency}, "
                    f"Stage 1 Threshold - {instance.stage_1_threshold}, "
                    f"Stage 2 Threshold - {instance.stage_2_threshold}, "
                    f"Stage 3 Threshold - {instance.stage_3_threshold}"
                ),
                timestamp=now(),
            )
            messages.success(self.request, "DPD Stage Mapping successfully updated!")
            return super().form_valid(form)
        
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

class DPDStageMappingDeleteView(LoginRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = FSI_DPD_Stage_Mapping
    template_name = 'staging/dpd_stage_mapping_confirm_delete.html'
    success_url = reverse_lazy('dpd_stage_mapping_list')
    permission_required = 'IFRS9.delete_dpd_stage_mapping'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='FSI_DPD_Stage_Mapping',
                action='delete',
                object_id=instance.pk,
                change_description=(
                    f"Deleted DPD Stage Mapping: Payment Frequency - {instance.payment_frequency}, "
                    f"Stage 1 Threshold - {instance.stage_1_threshold}, "
                    f"Stage 2 Threshold - {instance.stage_2_threshold}, "
                    f"Stage 3 Threshold - {instance.stage_3_threshold}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "DPD Stage Mapping successfully deleted!")
        except Exception as e:
            messages.error(self.request, f"Error logging deletion: {e}")

        return super().delete(request, *args, **kwargs)

#CoolingPeriodDefinition

class CoolingPeriodDefinitionListView(LoginRequiredMixin,ListView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_list.html'
    context_object_name = 'cooling_periods'
    paginate_by = 10

class CoolingPeriodDefinitionCreateView(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')
    permission_required = 'IFRS9.add_coolingperioddefinition'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()

            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='CoolingPeriodDefinition',
                action='create',
                object_id=instance.pk,
                change_description=(
                    f"Created Cooling Period Definition: Term Unit - {instance.v_amrt_term_unit}, "
                    f"Cooling Period Days - {instance.n_cooling_period_days}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Cooling period definition successfully added!")
            return super().form_valid(form)
        
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

class CoolingPeriodDefinitionUpdateView(LoginRequiredMixin, PermissionRequiredMixin,UpdateView):
    model = CoolingPeriodDefinition
    form_class = CoolingPeriodDefinitionForm
    template_name = 'staging/cooling_period_definition_form.html'
    success_url = reverse_lazy('cooling_period_definitions')
    permission_required = 'IFRS9.change_coolingperioddefinition'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='CoolingPeriodDefinition',
                action='update',
                object_id=instance.pk,
                change_description=(
                    f"Updated Cooling Period Definition: Term Unit - {instance.v_amrt_term_unit}, "
                    f"Cooling Period Days - {instance.n_cooling_period_days}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Cooling period definition successfully updated!")
            return super().form_valid(form)
        
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

class CoolingPeriodDefinitionDeleteView(LoginRequiredMixin, PermissionRequiredMixin,DeleteView):
    model = CoolingPeriodDefinition
    template_name = 'staging/cooling_period_definition_confirm_delete.html'
    success_url = reverse_lazy('cooling_period_definitions')
    permission_required = 'IFRS9.delete_coolingperioddefinition'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='CoolingPeriodDefinition',
                action='delete',
                object_id=instance.pk,
                change_description=(
                    f"Deleted Cooling Period Definition: Term Unit - {instance.v_amrt_term_unit}, "
                    f"Cooling Period Days - {instance.n_cooling_period_days}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Cooling period definition successfully deleted!")
        except Exception as e:
            messages.error(self.request, f"Error logging deletion: {e}")

        return super().delete(request, *args, **kwargs)
    
class DimDelinquencyBandListView(LoginRequiredMixin,ListView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dim_delinquency_band_list.html'
    context_object_name = 'delinquency_bands'
    paginate_by = 10

class DimDelinquencyBandCreateView(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')
    permission_required = 'IFRS9.add_dimdelinquencyband'

    def form_valid(self, form):
        try:

            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()

            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Dim_Delinquency_Band',
                action='create',
                object_id=instance.n_delq_band_code,
                change_description=(
                    f"Created Delinquency Band: Code - {instance.n_delq_band_code}, "
                    f"Description - {instance.v_delq_band_desc}, "
                    f"Lower Value - {instance.n_delq_lower_value}, "
                    f"Upper Value - {instance.n_delq_upper_value}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Delinquency band successfully added!")
            return super().form_valid(form)
        
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

class DimDelinquencyBandUpdateView(LoginRequiredMixin, PermissionRequiredMixin,UpdateView):
    model = Dim_Delinquency_Band
    form_class = DimDelinquencyBandForm
    template_name = 'staging/dim_delinquency_band_form.html'
    success_url = reverse_lazy('dim_delinquency_band_list')
    permission_required = 'IFRS9.change_dimdelinquencyband'

    def form_valid(self, form):
        try:

            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()

            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Dim_Delinquency_Band',
                action='update',
                object_id=instance.n_delq_band_code,
                change_description=(
                    f"Updated Delinquency Band: Code - {instance.n_delq_band_code}, "
                    f"Description - {instance.v_delq_band_desc}, "
                    f"Lower Value - {instance.n_delq_lower_value}, "
                    f"Upper Value - {instance.n_delq_upper_value}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Delinquency band successfully updated!")
            return super().form_valid(form)
        
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

class DimDelinquencyBandDeleteView(LoginRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Dim_Delinquency_Band
    template_name = 'staging/dpd_stage_mapping_confirm_delete.html'
    success_url = reverse_lazy('dim_delinquency_band_list')
    permission_required = 'IFRS9.delete_dimdelinquencyband'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Dim_Delinquency_Band',
                action='delete',
                object_id=instance.n_delq_band_code,
                change_description=(
                    f"Deleted Delinquency Band: Code - {instance.n_delq_band_code}, "
                    f"Description - {instance.v_delq_band_desc}, "
                    f"Lower Value - {instance.n_delq_lower_value}, "
                    f"Upper Value - {instance.n_delq_upper_value}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Delinquency band successfully deleted!")
        except Exception as e:
            messages.error(self.request, f"Error logging deletion: {e}")

        return super().delete(request, *args, **kwargs)
class CreditRatingCodeBandListView(LoginRequiredMixin,ListView):
    model = Credit_Rating_Code_Band
    template_name = 'staging/credit_rating_code_band_list.html'
    context_object_name = 'rating_codes'
    paginate_by = 10

class CreditRatingCodeBandCreateView(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')
    permission_required = 'IFRS9.add_credit_rating_code_band'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()

            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Credit_Rating_Code_Band',
                action='create',
                object_id=instance.v_rating_code,
                change_description=(
                    f"Created Credit Rating Code Band: Code - {instance.v_rating_code}, "
                    f"Description - {instance.v_rating_desc}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Credit rating code successfully added!")
            return super().form_valid(form)
        
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

class CreditRatingCodeBandUpdateView(LoginRequiredMixin, PermissionRequiredMixin,UpdateView):
    model = Credit_Rating_Code_Band
    form_class = CreditRatingCodeBandForm
    template_name = 'staging/credit_rating_code_band_form.html'
    success_url = reverse_lazy('credit_rating_code_band_list')
    permission_required = 'IFRS9.change_credit_rating_code_band'

    def form_valid(self, form):
        try:
            # Set the updated_by field to the currently logged-in user
            instance = form.save(commit=False)
            instance.created_by = self.request.user
            instance.save()
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Credit_Rating_Code_Band',
                action='update',
                object_id=instance.v_rating_code,
                change_description=(
                    f"Updated Credit Rating Code Band: Code - {instance.v_rating_code}, "
                    f"Description - {instance.v_rating_desc}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "redit rating code successfully updated!")
            return super().form_valid(form)
        
        except IntegrityError as e:
            # Handle database integrity errors, like duplicate entries
            messages.error(self.request, f"Integrity error: {e}")
            return self.form_invalid(form)
        except Exception as e:
            # Handle any other exceptions
            messages.error(self.request, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

class CreditRatingCodeBandDeleteView(LoginRequiredMixin,PermissionRequiredMixin, DeleteView):
    model = Credit_Rating_Code_Band
    template_name = 'staging/credit_rating_code_band_confirm_delete.html'
    success_url = reverse_lazy('credit_rating_code_band_list')
    permission_required = 'IFRS9.delete_credit_rating_code_band'
    

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=self.request.user,
                model_name='Credit_Rating_Code_Band',
                action='delete',
                object_id=instance.v_rating_code,
                change_description=(
                    f"Deleted Credit Rating Code Band: Code - {instance.v_rating_code}, "
                    f"Description - {instance.v_rating_desc}"
                ),
                timestamp=now(),
            )

            messages.success(self.request, "Credit rating code successfully deleted!")
        except Exception as e:
            messages.error(self.request, f"Error logging deletion: {e}")

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
@permission_required('IFRS9.change_fc_t_stage_determination', raise_exception=True)
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
                            previous_stage = record.n_stage_descr
                            record.n_curr_ifrs_stage_skey = int(stage_key)
                            record.n_stage_descr = STAGE_DESCRIPTION_MAP.get(int(stage_key))
                            record.save()
                            # Log the stage reassignment in the AuditTrail
                            AuditTrail.objects.create(
                                user=request.user,
                                model_name='FCT_Reporting_Lines',
                                action='update',
                                object_id=record.n_account_number,
                                change_description=(
                                    f"Reassigned stage for account {record.n_account_number}: "
                                    f"From Stage - {previous_stage}, To Stage - {record.n_stage_descr}"
                                ),
                                timestamp=now(),
                            )

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
