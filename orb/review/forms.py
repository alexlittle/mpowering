"""
Forms for resources - primarily for content review
"""

from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from orb.models import UserProfile
from crispy_forms.layout import Div, Layout, Submit
from django import forms
from django.utils.translation import ugettext as _
from django.utils.functional import cached_property

from orb.models import Resource, ResourceCriteria, ReviewerRole
from .models import ContentReview
from django.forms import inlineformset_factory




class ReviewForm(forms.Form):
    """
    Form for allowing a reviewer to enter a resource review
    """
    approved = forms.BooleanField(required=False)
    reason = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(ReviewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'reason',
        )

    def clean(self):
        data = self.cleaned_data
        if not data.get('approved') and not data.get('reason'):
            raise forms.ValidationError(_("Please provide a reason for rejecting this content."))
        return data


class RejectionForm(forms.ModelForm):
    """
    Form class for capturing the explanation for rejecting a submitted resource
    """
    criteria = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=ResourceCriteria.objects.all().order_by('category_order_by', 'order_by'),
        required=False,
    )
    notes = forms.CharField(
        widget=forms.Textarea,
        required=True,
        error_messages={'required': _(
            'Please enter a reason as to why the resource has been rejected')},
        help_text=_(
            'The text you enter here will be included in the email to the submitter of the '
            'resource, so please bear this in mind when explaining your reasoning.'),
        label=_(u"Reason for rejection")
    )

    class Meta:
        model = ContentReview
        fields = ('criteria', 'notes')

    def __init__(self, *args, **kwargs):
        super(RejectionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'criteria',
            'notes',
            Div(
                Submit('submit', _(u'Submit'),
                       css_class='btn btn-default'),
                css_class='col-lg-offset-2 col-lg-8',
            ),
        )


class AssignmentForm(forms.Form):
    """
    Form class for assigning reviews
    """
    def __init__(self, *args, **kwargs):
        self.resource = kwargs.pop('resource')
        for role in self.roles:
            self.declared_fields[role.name] = forms.ModelChoiceField(
                queryset=UserProfile.objects.filter(reviewer_role=role),
                required=False,
            )
            self.declared_fields[role.name].initial = self.assignments.get(role.name)

        super(AssignmentForm, self).__init__(*args, **kwargs)

        for role in self.roles:
            self.fields[role.name] = forms.ModelChoiceField(
                queryset=UserProfile.objects.filter(reviewer_role=role),
                required=False,
            )
            self.declared_fields[role.name] = self.fields[role.name]
            self.initial[role.name] = self.assignments.get(role.name)
            self.fields[role.name].initial = self.assignments.get(role.name)
            self.declared_fields[role.name].initial = self.fields[role.name].initial

        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(*self.layout_fields())

    def layout_fields(self):
        """
        Yields the fields for the layout.

        This allows indeterminate fields to be added while maintaining a
        pre-defined ordering.
        """
        for role in self.roles:
            yield role.name
        yield Div(
            Submit('submit', _(u'Assign'),
                   css_class='btn btn-default'),
            css_class='col-lg-offset-2 col-lg-8',
        )

    @cached_property
    def roles(self):
        return ReviewerRole.objects.all()

    @cached_property
    def assignments(self):
        x = {
            review.role.name: review.reviewer.userprofile
            for review in ContentReview.objects.filter(resource=self.resource)
        }
        return x

    def clean(self):
        data = self.cleaned_data
        complete_reviews = self.resource.content_reviews.complete()
        for review in complete_reviews:
            if data[review.role.name] != review.reviewer.userprofile:
                self.add_error(review.role.name, _("Cannot reassign a completed review."))
        return data

    def save(self):
        for role in self.roles:
            assigned = self.cleaned_data.get(role.name)
            if assigned:
                review, created = ContentReview.objects.get_or_create(
                    resource=self.resource,
                    role=role,
                    defaults={
                        'reviewer': assigned.user,
                    }
                )
                if not created:
                    review.reassign(assigned.user)
                    review.save()

AssignmentFormSet = inlineformset_factory(
    Resource,
    ContentReview,
    can_delete=False,
    extra=0,
    fields=('reviewer', 'role'),
)
