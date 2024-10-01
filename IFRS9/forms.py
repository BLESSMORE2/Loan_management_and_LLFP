from django import forms
from .models import *

class UploadFileForm(forms.Form):
    file = forms.FileField(label='Select a file', widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

class ColumnSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        columns = kwargs.pop('columns', [])
        super(ColumnSelectionForm, self).__init__(*args, **kwargs)
        
        # Dynamically generate a MultipleChoiceField for selecting columns
        self.fields['selected_columns'] = forms.MultipleChoiceField(
            choices=[(col, col) for col in columns],
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            label='Select Columns to Include',
            initial=columns  # By default, select all columns
        )

class ColumnMappingForm(forms.Form):
    def __init__(self, *args, selected_columns=None, model_fields=None, **kwargs):
        super(ColumnMappingForm, self).__init__(*args, **kwargs)

        if selected_columns and model_fields:
            for column in selected_columns:
                self.fields[column] = forms.ChoiceField(
                    choices=[(field, field) for field in model_fields] + [('unmapped', 'Unmapped')],
                    required=False
                )
                # Set the initial value for each field if provided in kwargs['initial']
                if 'initial' in kwargs and 'column_mappings' in kwargs['initial']:
                    if column in kwargs['initial']['column_mappings']:
                        self.fields[column].initial = kwargs['initial']['column_mappings'][column]

                        
    def clean(self):
        cleaned_data = super().clean()
        column_mappings = {key.replace('column_mapping_', ''): value for key, value in cleaned_data.items()}
        return {'column_mappings': column_mappings}



##########################################################
class TableSelectForm(forms.Form):
    table_name = forms.ModelChoiceField(queryset=TableMetadata.objects.filter(table_type='STG'), label="Select Table")


def generate_filter_form(model_class):
    """
    Dynamically generate a filter form based on the model's fields.
    """
    class FilterForm(forms.Form):
        pass

    for field in model_class._meta.fields:
        if isinstance(field, forms.CharField):
            FilterForm.base_fields[field.name] = forms.CharField(
                required=False,
                label=field.verbose_name,
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
        elif isinstance(field, forms.DateField):
            FilterForm.base_fields[field.name] = forms.DateField(
                required=False,
                label=field.verbose_name,
                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
            )
        elif isinstance(field, forms.IntegerField):
            FilterForm.base_fields[field.name] = forms.IntegerField(
                required=False,
                label=field.verbose_name,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
        elif isinstance(field, forms.FloatField):
            FilterForm.base_fields[field.name] = forms.FloatField(
                required=False,
                label=field.verbose_name,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
        # Add other field types as needed

    return FilterForm

class FilterForm(forms.Form):
    filter_column = forms.CharField(widget=forms.HiddenInput())
    filter_value = forms.CharField(widget=forms.HiddenInput())

    ######################

class FSIProductSegmentForm(forms.ModelForm):
    class Meta:
        model = FSI_Product_Segment
        fields = ['v_prod_segment', 'v_prod_type', 'v_prod_desc']

    def __init__(self, *args, **kwargs):
        super(FSIProductSegmentForm, self).__init__(*args, **kwargs)

        # Fetch distinct values from Ldn_Bank_Product_Info and set choices for the form fields
        self.fields['v_prod_segment'] = forms.ChoiceField(choices=[
            (seg, seg) for seg in Ldn_Bank_Product_Info.objects.values_list('v_prod_segment', flat=True).distinct()
        ])
        
        self.fields['v_prod_type'] = forms.ChoiceField(choices=[
            (ptype, ptype) for ptype in Ldn_Bank_Product_Info.objects.values_list('v_prod_type', flat=True).distinct()
        ])
        
        self.fields['v_prod_desc'] = forms.ChoiceField(choices=[
            (pdesc, pdesc) for pdesc in Ldn_Bank_Product_Info.objects.values_list('v_prod_desc', flat=True).distinct()
        ])


#staging forms
class CreditRatingStageForm(forms.ModelForm):
    class Meta:
        model = FSI_CreditRating_Stage
        fields = ['credit_rating', 'stage']
        widgets = {
            'credit_rating': forms.TextInput(attrs={'class': 'form-control'}),
            'stage': forms.Select(attrs={'class': 'form-control'}),
        }


class DPDStageMappingForm(forms.ModelForm):
    class Meta:
        model = FSI_DPD_Stage_Mapping
        fields = ['payment_frequency', 'stage_1_threshold', 'stage_2_threshold', 'stage_3_threshold']
        widgets = {
            'payment_frequency': forms.Select(attrs={'class': 'form-control'}),
            'stage_1_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'stage_2_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'stage_3_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CoolingPeriodDefinitionForm(forms.ModelForm):
    class Meta:
        model = CoolingPeriodDefinition
        fields = ['v_amrt_term_unit', 'n_cooling_period_days']
        widgets = {
            'v_amrt_term_unit': forms.Select(attrs={'class': 'form-control'}),
            'n_cooling_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class DimDelinquencyBandForm(forms.ModelForm):
    class Meta:
        model = Dim_Delinquency_Band
        fields = ['n_delq_band_code', 'v_delq_band_desc', 'n_delq_lower_value', 'n_delq_upper_value', 'v_amrt_term_unit']
        widgets = {
            'n_delq_band_code': forms.TextInput(attrs={'class': 'form-control'}),
            'v_delq_band_desc': forms.TextInput(attrs={'class': 'form-control'}),
            'n_delq_lower_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'n_delq_upper_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'v_amrt_term_unit': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CreditRatingCodeBandForm(forms.ModelForm):
    class Meta:
        model = Credit_Rating_Code_Band
        fields = ['v_rating_code', 'v_rating_desc']
        widgets = {
            'v_rating_code': forms.TextInput(attrs={'class': 'form-control'}),
            'v_rating_desc': forms.TextInput(attrs={'class': 'form-control'}),
        }


STAGE_CHOICES = [
    (1, 'Stage 1'),
    (2, 'Stage 2'),
    (3, 'Stage 3'),
]

class StageReassignmentFilterForm(forms.Form):
    fic_mis_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'dd/mm/yyyy'}), required=True)
    n_cust_ref_code = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    n_party_type = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    n_account_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    n_partner_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
class StageReassignmentForm(forms.ModelForm):
    class Meta:
        model = FCT_Stage_Determination
        fields = ['n_curr_ifrs_stage_skey']

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        # Set the stage description based on the current IFRS stage key
        stage_mapping = {
            1: 'Stage 1',
            2: 'Stage 2',
            3: 'Stage 3'
        }
        instance.n_stage_descr = stage_mapping.get(instance.n_curr_ifrs_stage_skey, 'Unknown Stage')
        instance.save()
        return instance
    
#cashflow interest method
class InterestMethodForm(forms.ModelForm):
    class Meta:
        model = Fsi_Interest_Method
        fields = ['v_interest_method', 'description']
        widgets = {
            'v_interest_method': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
