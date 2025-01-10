from django import forms
from .models import *
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

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

class ReportingCurrencyForm(forms.ModelForm):
    class Meta:
        model = ReportingCurrency
        fields = ['currency_code']


class CurrencyCodeForm(forms.ModelForm):
    class Meta:
        model = CurrencyCode
        fields = ['code', 'description']  # Fields for Currency Code and Description

    def __init__(self, *args, **kwargs):
        super(CurrencyCodeForm, self).__init__(*args, **kwargs)
        # Customizing the widgets for better display
        self.fields['code'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Currency Code (e.g., USD)',
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Currency Description (e.g., United States Dollar)',
        })
        # Optional: Adding labels for user-friendly display
        self.fields['code'].label = "Currency Code"
        self.fields['description'].label = "Currency Description"

class ExchangeRateConfForm(forms.ModelForm):
    class Meta:
        model = DimExchangeRateConf
        fields = ['EXCHANGE_RATE_API_KEY', 'use_on_exchange_rates','use_latest_exchange_rates']
        labels = {
            'EXCHANGE_RATE_API_KEY': 'Exchange Rate API Key',
            'use_on_exchange_rates': 'Use on exchange rates',
            'use_latest_exchange_rates':'Use Latest Exchange Rates'
        }
        widgets = {
            'EXCHANGE_RATE_API_KEY': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter your Exchange Rate API Key',
                'required': True  # Making the API key field required
            }),
            'use_on_exchange_rates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'use_latest_exchange_rates': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EXCHANGE_RATE_API_KEY'].required = True

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

        # Fetch distinct values for Product Segment and Product Type
        segment_choices = [('', '---')] + [
            (seg, seg) for seg in Ldn_Bank_Product_Info.objects.values_list('v_prod_segment', flat=True).distinct()
        ]
        self.fields['v_prod_segment'] = forms.ChoiceField(choices=segment_choices)

        type_choices = [('', '---')] + [
            (ptype, ptype) for ptype in Ldn_Bank_Product_Info.objects.values_list('v_prod_type', flat=True).distinct()
        ]
        self.fields['v_prod_type'] = forms.ChoiceField(choices=type_choices)

        # Make Product Description read-only
        self.fields['v_prod_desc'].widget.attrs['disabled'] = True



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
    fic_mis_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control'}), required=True)
    n_cust_ref_code = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Customer ID'}), required=False)
    n_account_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Account Number'}), required=True)
class StageReassignmentForm(forms.ModelForm):
    class Meta:
        model = FCT_Reporting_Lines
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


#probability
#term structure

class PDTermStructureForm(forms.ModelForm):
    class Meta:
        model = Ldn_PD_Term_Structure
        fields = [
            'v_pd_term_structure_name', 'v_pd_term_frequency_unit', 
            'v_pd_term_structure_type',
            'fic_mis_date'
        ]

        # Define widgets for fields
        widgets = {
            'fic_mis_date': forms.DateInput(attrs={'type': 'date'}),  # Using DateInput with 'date' type
        }

    def __init__(self, *args, **kwargs):
        super(PDTermStructureForm, self).__init__(*args, **kwargs)

        # Customizing the display of the ForeignKey field 'v_pd_term_structure_name'
        self.fields['v_pd_term_structure_name'].queryset = FSI_Product_Segment.objects.all()
        self.fields['v_pd_term_structure_name'].label = "Term Structure Name"
        
        # Custom label for the fields
        self.fields['v_pd_term_frequency_unit'].label = "Term Frequency Unit"
        self.fields['v_pd_term_frequency_unit'].widget = forms.Select(choices=[
            ('M', 'Monthly'), ('Q', 'Quarterly'), ('H', 'Half Yearly'), ('Y', 'Yearly'), ('D', 'Daily')
        ])

        self.fields['v_pd_term_structure_type'].label = "Term Structure Type"
        self.fields['v_pd_term_structure_type'].widget = forms.Select(choices=[
             ('D', 'DPD'),('R', 'Rating')
        ])

        

        # Ensure 'fic_mis_date' displays as a date picker
        self.fields['fic_mis_date'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['fic_mis_date'].label = "Fic Mis Date"

class PDTermStructureDtlForm(forms.ModelForm):
    class Meta:
        model = Ldn_PD_Term_Structure_Dtl
        fields = ['v_pd_term_structure_id', 'fic_mis_date', 'v_credit_risk_basis_cd', 'n_pd_percent']

    def __init__(self, *args, **kwargs):
        super(PDTermStructureDtlForm, self).__init__(*args, **kwargs)
        
        # Filter Term Structure ID based on v_pd_term_structure_type
        self.fields['v_pd_term_structure_id'].queryset = Ldn_PD_Term_Structure.objects.filter(
            v_pd_term_structure_type='D'
        )

        # Populate v_credit_risk_basis_cd choices from Dim_Delinquency_Band
        delinquency_bands = Dim_Delinquency_Band.objects.values_list('n_delq_band_code', 'v_delq_band_desc')
        self.fields['v_credit_risk_basis_cd'] = forms.ChoiceField(choices=[
            (code, f"{desc}") for code, desc in delinquency_bands
        ])

class PDTermStructureDtlRatingForm(forms.ModelForm):
    class Meta:
        model = Ldn_PD_Term_Structure_Dtl
        fields = ['v_pd_term_structure_id', 'fic_mis_date', 'v_credit_risk_basis_cd', 'n_pd_percent']

    def __init__(self, *args, **kwargs):
        super(PDTermStructureDtlRatingForm, self).__init__(*args, **kwargs)
        
        # Filter Term Structure ID based on v_pd_term_structure_type
        self.fields['v_pd_term_structure_id'].queryset = Ldn_PD_Term_Structure.objects.filter(
            v_pd_term_structure_type='R'
        )
        
        # Set up Date Input for fic_mis_date
        self.fields['fic_mis_date'].widget = forms.DateInput(attrs={'type': 'date'})
        
        # Set up Rating Code dropdown from Credit_Rating_Code_Band
        self.fields['v_credit_risk_basis_cd'].queryset = Credit_Rating_Code_Band.objects.all()
        self.fields['v_credit_risk_basis_cd'].label = "Rating Code"
        self.fields['v_credit_risk_basis_cd'].widget = forms.Select(choices=[
            (rating.v_rating_code, f"{rating.v_rating_code}") 
            for rating in Credit_Rating_Code_Band.objects.all()
        ])

class LGDTermStructureForm(forms.ModelForm):
    class Meta:
        model = Ldn_LGD_Term_Structure
        fields = ['v_lgd_term_structure_name', 'n_lgd_percent', 'fic_mis_date']

        widgets = {
            'fic_mis_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(LGDTermStructureForm, self).__init__(*args, **kwargs)
        # Customize form labels if necessary
        self.fields['v_lgd_term_structure_name'].label = "LGD Term Structure Name"
        self.fields['n_lgd_percent'].label = "LGD Percent"
        self.fields['fic_mis_date'].label = "Reporting Date"

class CollateralLGDForm(forms.ModelForm):
    class Meta:
        model = CollateralLGD
        fields = ['can_calculate_lgd']
        labels = {
            'can_calculate_lgd': 'Can we calculate LGD using Collateral?',
        }
        widgets = {
            'can_calculate_lgd': forms.CheckboxInput(),
        }

class InterpolationMethodForm(forms.ModelForm):
    class Meta:
        model = FSI_LLFP_APP_PREFERENCES
        fields = [
            'pd_interpolation_method', 
            'n_pd_model_proj_cap', 
            'interpolation_level'
        ]
    
    def __init__(self, *args, **kwargs):
        super(InterpolationMethodForm, self).__init__(*args, **kwargs)
        self.fields['pd_interpolation_method'].label = "PD Interpolation Method"
        self.fields['n_pd_model_proj_cap'].label = "PD Model Projection Cap"
        self.fields['interpolation_level'].label = "Interpolation Level"


from .models import ECLMethod

class ECLMethodForm(forms.ModelForm):
    class Meta:
        model = ECLMethod
        fields = ['method_name', 'uses_discounting']

class ColumnMappingForm(forms.Form):
    def __init__(self, *args, selected_columns=None, model_fields=None, **kwargs):
        super(ColumnMappingForm, self).__init__(*args, **kwargs)

        # Create a field for each selected column, with options to map it to a model field or mark it as 'unmapped'
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
        # Construct a dictionary to map selected columns to their chosen model fields
        column_mappings = {key: value for key, value in cleaned_data.items() if value != 'unmapped'}
        return {'column_mappings': column_mappings}
    

# Form for Process
# Process Form
class ProcessForm(forms.ModelForm):
    class Meta:
        model = Process
        fields = ['process_name']
        widgets = {
            'process_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Process Name'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProcessForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Process'))

# RunProcess Form
class RunProcessForm(forms.ModelForm):
    class Meta:
        model = RunProcess
        fields = ['function', 'order']
        widgets = {
            'function': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Execution Order'}),
        }

    def __init__(self, *args, **kwargs):
        super(RunProcessForm, self).__init__(*args, **kwargs)
        self.fields['function'].empty_label = "Select Function"
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'

    # Custom validation (example)
    def clean(self):
        cleaned_data = super().clean()

        # Skip validation if the form is marked for deletion
        if self.cleaned_data.get('DELETE', False):
            return cleaned_data

        order = cleaned_data.get('order')

        # Validation: Order should be a positive number
        if order is None or order <= 0:
            raise forms.ValidationError("Order must be a positive number.")

        return cleaned_data
