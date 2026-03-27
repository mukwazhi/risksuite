from django import forms
from django.forms import inlineformset_factory
from .models import Risk, RiskIndicator, RiskAssessment, Mitigation, MitigationProgressLog, RiskOwner, PeriodicMeasurementSchedule, IndicatorMeasurement, IndicatorAssessment, RiskCategoryImpact, Control


class RiskBasicInfoForm(forms.ModelForm):
    """Stage 1: Basic risk information without inherent assessment"""
    class Meta:
        model = Risk
        fields = [
            'department',
            'category',
            'title',
            'description',
            'cause',
            'impact_description',
            'risk_owner',
            'linked_kpi',
            'park_risk',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a concise risk title'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe the risk...\n\nTip: Use bullet points (-, *, •) or numbered lists (1., 2., 3.) for better formatting.\nUse blank lines to separate paragraphs.'
            }),
            'cause': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'What causes this risk?\n\nTip: You can list multiple causes:\n- Cause 1\n- Cause 2'
            }),
            'impact_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Describe the potential impact...\n\nTip: List different impact areas:\n1. Financial impact\n2. Operational impact\n3. Reputational impact'
            }),
            'risk_owner': forms.Select(attrs={'class': 'form-select'}),
            'linked_kpi': forms.Select(attrs={'class': 'form-select'}),
            'park_risk': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'linked_kpi': 'Primary KPI',
            'park_risk': 'Save as Draft (Park Risk)',
        }
        help_texts = {
            'park_risk': 'Check this to save as a draft without submitting for approval',
            'linked_kpi': 'Select the primary KPI that this risk is linked to (optional)',
        }


class RiskInherentAssessmentForm(forms.ModelForm):
    """Stage 2: Inherent risk assessment (without controls)"""
    class Meta:
        model = Risk
        fields = [
            'inherent_likelihood',
            'inherent_impact',
        ]
        widgets = {
            'inherent_likelihood': forms.Select(
                choices=[(i, f'{i} - {label}') for i, label in [
                    (1, 'Very Low'),
                    (2, 'Low'),
                    (3, 'Medium'),
                    (4, 'High'),
                    (5, 'Very High')
                ]],
                attrs={'class': 'form-select'}
            ),
            'inherent_impact': forms.Select(
                choices=[(i, f'{i} - {label}') for i, label in [
                    (1, 'Negligible'),
                    (2, 'Minor'),
                    (3, 'Moderate'),
                    (4, 'Major'),
                    (5, 'Catastrophic')
                ]],
                attrs={'class': 'form-select'}
            ),
        }
        labels = {
            'inherent_likelihood': 'Inherent Likelihood (Without Controls)',
            'inherent_impact': 'Inherent Impact (Without Controls)',
        }
        help_texts = {
            'inherent_likelihood': 'Rate the likelihood of this risk occurring WITHOUT any controls in place (1=Very Low, 5=Very High)',
            'inherent_impact': 'Rate the impact if this risk occurs WITHOUT any controls in place (1=Negligible, 5=Catastrophic)',
        }


class RiskForm(forms.ModelForm):
    """Full form (backward compatibility) - combines all fields"""
    class Meta:
        model = Risk
        fields = [
            'department',
            'category',
            'title',
            'description',
            'cause',
            'impact_description',
            'inherent_likelihood',
            'inherent_impact',
            'risk_owner',
            'linked_kpi',
            'park_risk',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a concise risk title'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe the risk...\n\nTip: Use bullet points (-, *, •) or numbered lists (1., 2., 3.) for better formatting.\nUse blank lines to separate paragraphs.'
            }),
            'cause': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'What causes this risk?\n\nTip: You can list multiple causes:\n- Cause 1\n- Cause 2'
            }),
            'impact_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Describe the potential impact...\n\nTip: List different impact areas:\n1. Financial impact\n2. Operational impact\n3. Reputational impact'
            }),
            'inherent_likelihood': forms.Select(
                choices=[(i, f'{i} - {label}') for i, label in [
                    (1, 'Very Low'),
                    (2, 'Low'),
                    (3, 'Medium'),
                    (4, 'High'),
                    (5, 'Very High')
                ]],
                attrs={'class': 'form-select'}
            ),
            'inherent_impact': forms.Select(
                choices=[(i, f'{i} - {label}') for i, label in [
                    (1, 'Negligible'),
                    (2, 'Minor'),
                    (3, 'Moderate'),
                    (4, 'Major'),
                    (5, 'Catastrophic')
                ]],
                attrs={'class': 'form-select'}
            ),
            'risk_owner': forms.Select(attrs={'class': 'form-select'}),
            'linked_kpi': forms.Select(attrs={'class': 'form-select'}),
            'park_risk': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'inherent_likelihood': 'Inherent Likelihood (Without Controls)',
            'inherent_impact': 'Inherent Impact (Without Controls)',
            'linked_kpi': 'Primary KPI',
            'park_risk': 'Save as Draft (Park Risk)',
        }
        help_texts = {
            'park_risk': 'Check this to save as a draft without submitting for approval',
            'title': 'Risk rating will be calculated based on inherent risk and controls',
            'linked_kpi': 'Select the primary KPI that this risk is linked to (optional)',
            'inherent_likelihood': 'Rate the likelihood of this risk occurring WITHOUT any controls in place (1=Very Low, 5=Very High)',
            'inherent_impact': 'Rate the impact if this risk occurs WITHOUT any controls in place (1=Negligible, 5=Catastrophic)',
        }


class ControlForm(forms.ModelForm):
    """Form for adding/editing internal controls with weighted effectiveness."""
    
    class Meta:
        model = Control
        fields = [
            'name',
            'description',
            'control_type',
            'effectiveness',
            'weight',
            'weight_rationale',
            'control_owner',
            'frequency',
            'last_tested_date',
            'test_results',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Monthly reconciliation, Access control review'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe how this control works...'
            }),
            'control_type': forms.Select(attrs={'class': 'form-select'}),
            'effectiveness': forms.NumberInput(attrs={
                'class': 'form-control',
                'type': 'range',
                'min': '0',
                'max': '100',
                'step': '1',
                'oninput': 'this.nextElementSibling.value = this.value + \"%\"'
            }),
            'weight': forms.Select(attrs={'class': 'form-select'}),
            'weight_rationale': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Why is this control weighted at this level?'
            }),
            'control_owner': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Daily, Weekly, Continuous, Quarterly'
            }),
            'last_tested_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'test_results': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Results from the most recent test...'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Control Name',
            'description': 'Control Description',
            'control_type': 'Control Type',
            'effectiveness': 'Control Effectiveness (%)',
            'weight': 'Control Weight (Importance)',
            'weight_rationale': 'Weight Justification',
            'control_owner': 'Control Owner',
            'frequency': 'Frequency of Execution',
            'last_tested_date': 'Last Tested Date',
            'test_results': 'Test Results',
            'is_active': 'Active',
        }
        help_texts = {
            'effectiveness': 'How effective is this control at mitigating the risk? (0-100%)',
            'weight': 'How important is this control relative to others? (1=Minimal, 10=Critical)',
            'control_type': 'The type determines how the control reduces risk (likelihood vs impact)',
            'is_active': 'Uncheck to temporarily disable this control from calculations',
        }


# Formset for managing multiple controls
ControlFormSet = inlineformset_factory(
    Risk,
    Control,
    form=ControlForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)

class RiskIndicatorForm(forms.ModelForm):
    class Meta:
        model = RiskIndicator
        fields = [
            'appetite_level',
            'appetite_tolerance_pct',
            'preferred_kpi',
            'preferred_kpi_name',
            'unit',
            'data_source',
            'aggregation_method',
            'measurement_period',
            'direction',
            'trigger_threshold',
            'trigger_operator',
            'breach_threshold',
            'breach_operator',
            'notes',
            'active',
        ]
        widgets = {
            'appetite_level': forms.Select(attrs={'class': 'form-select'}),
            'appetite_tolerance_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': 'e.g., 10.00'}),
            'preferred_kpi': forms.Select(attrs={'class': 'form-select'}),
            'preferred_kpi_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Or enter custom KPI name'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., minutes, percentage, count'}),
            'data_source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Where to collect the measurement'}),
            'aggregation_method': forms.Select(attrs={'class': 'form-select'}),
            'measurement_period': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., monthly, weekly'}),
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'trigger_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Caution threshold value'}),
            'trigger_operator': forms.Select(attrs={'class': 'form-select'}),
            'breach_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Breach threshold value'}),
            'breach_operator': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes about this indicator...'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'appetite_level': 'Risk Appetite Level',
            'appetite_tolerance_pct': 'Tolerance Percentage',
            'preferred_kpi': 'Preferred KPI for Evaluation',
            'preferred_kpi_name': 'Custom KPI Name',
            'unit': 'Unit of Measurement',
            'data_source': 'Data Source',
            'aggregation_method': 'Aggregation Method',
            'measurement_period': 'Measurement Period',
            'direction': 'Direction',
            'trigger_threshold': 'Trigger Threshold (Caution)',
            'trigger_operator': 'Trigger Operator',
            'breach_threshold': 'Breach Threshold (Critical)',
            'breach_operator': 'Breach Operator',
            'notes': 'Evaluation Notes',
            'active': 'Active',
        }
        help_texts = {
            'appetite_tolerance_pct': 'Acceptable deviation percentage (0-100)',
            'preferred_kpi_name': 'Only if custom KPI not in dropdown',
            'trigger_threshold': 'When measurement reaches this value, trigger caution status',
            'breach_threshold': 'When measurement reaches this value, trigger breach status',
            'active': 'Uncheck to deactivate this indicator',
        }

    def save(self, commit=True):
        # RiskIndicator instances don't have `risk_number` or `department`.
        # The view assigns `indicator.risk` before saving, so just delegate
        # to the parent save implementation.
        return super().save(commit=commit)

class RiskAssessmentForm(forms.ModelForm):
    """
    Form for adding supplementary notes to auto-generated risk assessments.
    Likelihood and Impact are automatically calculated from indicator assessments.
    """
    class Meta:
        model = RiskAssessment
        fields = [
            'assessment_type',
            'rationale',
            'changes_since_last',
            'evidence',
            'recommendations',
        ]
        widgets = {
            'assessment_type': forms.Select(attrs={'class': 'form-select'}),
            'rationale': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add additional rationale or context (optional - auto-generated text will be included)...'
            }),
            'changes_since_last': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What has changed since the last assessment?'
            }),
            'evidence': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Supporting evidence for this assessment...'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Recommended actions based on this assessment...'
            }),
        }
        labels = {
            'assessment_type': 'Assessment Type',
            'rationale': 'Additional Notes',
            'changes_since_last': 'Changes Since Last Assessment',
            'evidence': 'Supporting Evidence',
            'recommendations': 'Recommendations',
        }
        help_texts = {
            'assessment_type': 'Select the type of assessment',
            'rationale': 'Likelihood and Impact are automatically calculated from Key Risk Indicator assessments. Use this field to add additional context or notes.',
        }


class ManualRiskAssessmentForm(forms.ModelForm):
    """Form to allow manual entry of likelihood and impact after indicator assessments."""
    class Meta:
        model = RiskAssessment
        fields = [
            'assessment_type',
            'assessment_date',
            'likelihood',
            'impact',
            'rationale',
            'changes_since_last',
            'evidence',
            'recommendations',
        ]
        widgets = {
            'assessment_type': forms.Select(attrs={'class': 'form-select'}),
            'assessment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'likelihood': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'impact': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'rationale': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'changes_since_last': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'evidence': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'assessment_type': 'Assessment Type',
            'assessment_date': 'Assessment Date',
            'likelihood': 'Likelihood (1-5)',
            'impact': 'Impact (1-5)',
        }


class MitigationForm(forms.ModelForm):
    class Meta:
        model = Mitigation
        fields = [
            'strategy',
            'action',
            'due_date',
            'responsible_person',
            'status',
            'evidence',
        ]
        widgets = {
            'strategy': forms.Select(attrs={'class': 'form-select'}),
            'action': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the mitigation action in detail...'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'responsible_person': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'strategy': 'Mitigation Strategy',
            'action': 'Mitigation Action',
            'due_date': 'Due Date',
            'responsible_person': 'Responsible Person',
            'status': 'Status',
            'evidence': 'Evidence Document (Optional)',
        }
        help_texts = {
            'strategy': 'Select the risk treatment strategy',
            'action': 'Provide detailed steps for this mitigation action',
            'evidence': 'Upload supporting documentation (PDF, Word, Excel, etc.)',
        }


class ScheduleUpdateForm(forms.ModelForm):
    """Form for updating periodic measurement schedules"""
    
    # Optional field to record measurement when completing schedule
    measurement_value = forms.DecimalField(
        max_digits=18,
        decimal_places=6,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.000001',
            'placeholder': 'Enter measurement value'
        }),
        label='Measurement Value',
        help_text='Enter the measurement value if completing this schedule'
    )
    
    measurement_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add notes about this measurement...'
        }),
        label='Measurement Notes',
        help_text='Optional notes about the measurement'
    )
    
    class Meta:
        model = PeriodicMeasurementSchedule
        fields = [
            'status',
            'notes',
            'reminder_sent',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add notes about this scheduled measurement...'
            }),
            'reminder_sent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'status': 'Schedule Status',
            'notes': 'Schedule Notes',
            'reminder_sent': 'Reminder Sent',
        }
        help_texts = {
            'status': 'Update the status of this scheduled measurement',
            'notes': 'Add any relevant notes or context',
            'reminder_sent': 'Check if reminder has been sent for this measurement',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If status is being changed to completed, make measurement_value required
        if self.data.get('status') == 'completed':
            self.fields['measurement_value'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        measurement_value = cleaned_data.get('measurement_value')
        
        # If status is completed, measurement_value should be provided
        if status == 'completed' and measurement_value is None:
            raise forms.ValidationError(
                "Please provide a measurement value when marking schedule as completed."
            )
        
        return cleaned_data


class IndicatorAssessmentForm(forms.ModelForm):
    """Form for recording comprehensive indicator assessments"""
    
    class Meta:
        model = IndicatorAssessment
        fields = [
            'assessment_date',
            'measured_value',
            'is_financial',
            'currency_code',
            'assessment_notes',
            'analysis',
            'corrective_actions',
            'evidence_documents',
        ]
        widgets = {
            'assessment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'measured_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Enter measured value'
            }),
            'is_financial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.Select(attrs={'class': 'form-select'},
                choices=[
                    ('USD', 'US Dollar ($)'),
                    ('ZWL', 'Zimbabwe Dollar (ZWL$)'),
                    ('EUR', 'Euro (€)'),
                    ('GBP', 'British Pound (£)'),
                    ('ZAR', 'South African Rand (R)'),
                    ('BWP', 'Botswana Pula (P)'),
                ]
            ),
            'assessment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed notes about this assessment period...'
            }),
            'analysis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Analysis of results, trends, and variances...'
            }),
            'corrective_actions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any corrective actions taken or recommended...'
            }),
            'evidence_documents': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'assessment_date': 'Assessment Date',
            'measured_value': 'Measured Value',
            'is_financial': 'Financial Indicator',
            'currency_code': 'Currency',
            'assessment_notes': 'Assessment Notes',
            'analysis': 'Analysis & Findings',
            'corrective_actions': 'Corrective Actions',
            'evidence_documents': 'Supporting Evidence (Optional)',
        }
        help_texts = {
            'assessment_date': 'Date this assessment was conducted',
            'measured_value': 'The actual measured value for this period',
            'is_financial': 'Check if this indicator measures financial/monetary values',
            'currency_code': 'Select the currency if this is a financial indicator',
            'assessment_notes': 'Provide context and details about the measurement',
            'analysis': 'Analyze the results against targets and previous periods',
            'corrective_actions': 'Document actions taken to address issues',
            'evidence_documents': 'Upload supporting documents (reports, screenshots, etc.)',
        }
    
    def __init__(self, *args, **kwargs):
        self.indicator = kwargs.pop('indicator', None)
        self.schedule = kwargs.pop('schedule', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate financial fields if indicator unit suggests currency
        if self.indicator and self.indicator.unit:
            unit_upper = self.indicator.unit.upper()
            if any(curr in unit_upper for curr in ['USD', 'ZWL', 'EUR', 'GBP', '$', '€', '£']):
                self.fields['is_financial'].initial = True
                if 'ZWL' in unit_upper:
                    self.fields['currency_code'].initial = 'ZWL'
                elif 'EUR' in unit_upper or '€' in self.indicator.unit:
                    self.fields['currency_code'].initial = 'EUR'
                elif 'GBP' in unit_upper or '£' in self.indicator.unit:
                    self.fields['currency_code'].initial = 'GBP'
        
        # If linked to schedule, pre-populate the assessment date
        if self.schedule:
            self.fields['assessment_date'].initial = self.schedule.scheduled_date
    
    def clean_measured_value(self):
        value = self.cleaned_data.get('measured_value')
        if value is None:
            raise forms.ValidationError("Please provide a measured value for the assessment.")
        return value
    
    def clean(self):
        cleaned_data = super().clean()
        is_financial = cleaned_data.get('is_financial')
        currency_code = cleaned_data.get('currency_code')
        
        # If financial indicator, currency code is required
        if is_financial and not currency_code:
            raise forms.ValidationError(
                "Please select a currency code for financial indicators."
            )
        
        return cleaned_data


# AssessmentDecisionForm removed together with model; see migration/data purge instructions


class RiskCategoryImpactForm(forms.ModelForm):
    class Meta:
        model = RiskCategoryImpact
        fields = ['category', 'impact', 'likelihood', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'impact': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'likelihood': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


RiskCategoryImpactFormSet = inlineformset_factory(
    Risk,
    RiskCategoryImpact,
    form=RiskCategoryImpactForm,
    extra=1,
    can_delete=True
)


class MitigationUpdateForm(forms.ModelForm):
    """Form for updating mitigation status and progress"""
    progress_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe the progress made on this mitigation action...'
        }),
        required=False,
        label='Progress Notes',
        help_text='Document any progress, challenges, or updates'
    )
    
    postponement_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this mitigation is being postponed...'
        }),
        required=False,
        label='Postponement Reason',
        help_text='Required if changing status to Postponed'
    )
    
    failure_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this mitigation was not achieved...'
        }),
        required=False,
        label='Reason for Not Achieving',
        help_text='Required if changing status to Not Achieved'
    )
    
    lessons_learned = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Document lessons learned from this experience...'
        }),
        required=False,
        label='Lessons Learned',
        help_text='What can be learned from this outcome?'
    )
    
    trigger_reassessment = forms.BooleanField(
        required=False,
        initial=False,
        label='Trigger Risk Reassessment',
        help_text='Check this if the mitigation progress warrants a risk reassessment',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Mitigation
        fields = ['status', 'completion_percentage', 'due_date', 'evidence', 'responsible_person']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'completion_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 5,
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
            'responsible_person': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'status': 'Mitigation Status',
            'completion_percentage': 'Completion Percentage',
            'due_date': 'Due Date',
            'evidence': 'Evidence Document',
            'responsible_person': 'Responsible Person',
        }
        help_texts = {
            'status': 'Update the current status of this mitigation action',
            'completion_percentage': 'Enter percentage completed (0-100)',
            'evidence': 'Upload evidence of completion or progress (optional)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        postponement_reason = cleaned_data.get('postponement_reason')
        failure_reason = cleaned_data.get('failure_reason')
        completion_percentage = cleaned_data.get('completion_percentage', 0)
        
        # Validate postponement reason
        if status == 'postponed' and not postponement_reason:
            self.add_error('postponement_reason', 'Please provide a reason for postponement')
        
        # Validate failure reason
        if status == 'not_achieved' and not failure_reason:
            self.add_error('failure_reason', 'Please explain why the mitigation was not achieved')
        
        # Validate completion percentage for certain statuses
        if status == 'complete' and completion_percentage < 100:
            cleaned_data['completion_percentage'] = 100
        elif status == 'pending' and completion_percentage > 0:
            self.add_error('completion_percentage', 'Pending mitigations should have 0% completion')
        elif status == 'partially_implemented' and completion_percentage == 0:
            self.add_error('completion_percentage', 'Partially implemented mitigations must have > 0% completion')
        
        return cleaned_data


# Notification forms removed along with models. If you need to reintroduce
# notification-related forms, re-add `NotificationRuleForm` and
# `NotificationPreferenceForm` here when the models exist.


from django import forms
from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            'enable_email_notifications',
            'enable_pending_assessments', 'enable_upcoming_assessments', 'enable_overdue_assessments', 'upcoming_days_assessment',
            'enable_pending_mitigations', 'enable_upcoming_mitigations', 'enable_overdue_mitigations', 'upcoming_days_mitigation',
            'frequency', 'notify_time',
        ]
        widgets = {
            'notify_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control form-control-sm'}),
            'upcoming_days_assessment': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
            'upcoming_days_mitigation': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
            'frequency': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'enable_email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_pending_assessments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_upcoming_assessments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_overdue_assessments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_pending_mitigations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_upcoming_mitigations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_overdue_mitigations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'enable_email_notifications': 'Enable Email Notifications',
            'enable_pending_assessments': 'Pending Assessments',
            'enable_upcoming_assessments': 'Upcoming Assessments',
            'enable_overdue_assessments': 'Overdue Assessments',
            'upcoming_days_assessment': 'Upcoming (days)',
            'enable_pending_mitigations': 'Pending Mitigations',
            'enable_upcoming_mitigations': 'Upcoming Mitigations',
            'enable_overdue_mitigations': 'Overdue Mitigations',
            'upcoming_days_mitigation': 'Upcoming (days)',
            'notify_time': 'Preferred Notification Time',
            'frequency': 'Delivery Frequency',
        }
        help_texts = {
            'upcoming_days_assessment': 'How many days ahead to include as "upcoming" for assessments',
            'upcoming_days_mitigation': 'How many days ahead to include as "upcoming" for mitigations',
            'notify_time': 'Preferred local time to receive notifications (optional)',
            'frequency': 'How often you want to receive notification digests',
        }


class AdminNotificationPreferenceForm(NotificationPreferenceForm):
    class Meta(NotificationPreferenceForm.Meta):
        fields = NotificationPreferenceForm.Meta.fields + ['minimum_risk_level']
        widgets = dict(NotificationPreferenceForm.Meta.widgets)
        widgets.update({'minimum_risk_level': forms.Select(attrs={'class': 'form-select form-select-sm'})})
