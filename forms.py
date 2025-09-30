from django import forms
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.utils.text import format_lazy

from submission.models import Article, Licence, Section, FieldAnswer, Field
from review.logic import render_choices
from utils.forms import KeywordModelForm
from core.models import Account
from core.model_utils import DateTimePickerInput


class DepositAgreementForm(forms.Form):
    deposit_agreement = forms.BooleanField(
        help_text=format_lazy("The author(s) of this article have signed a PDF, clicked through a form, or otherwise documented agreement to the journal's copyright agreement, which grants the journal permission to publish this article. (The agreement should match the one on file with eScholarship staff, which you can <a href='{}'>view here</a>. If you have questions please <a href='https://help.escholarship.org/support/tickets/new'>contact eScholarship</a>.)",  reverse_lazy('journal_submissions'))
    )

class PublicationInfo(forms.ModelForm):
    class Meta:
        model = Article
        fields = (
            'date_accepted',
            'date_published',
            'page_numbers',
            'primary_issue',
            'peer_reviewed',
            'render_galley',
        )
        help_texts = {
            'render_galley': 'Render Galleys are displayed on the Article page',
            'page_numbers': 'Tis is a free text field, generally page numbers'
                            ' look like 10 or 10-16',
            'peer_reviewed': 'If this article has been peer reviewed prior to'
                             'being loaded into Janeway check this box.'
        }
        widgets = {
            'date_accepted': DateTimePickerInput,
        }

    def __init__(self, *args, **kwargs):
        super(PublicationInfo, self).__init__(*args, **kwargs)
        self.fields['date_published'].required = True
        self.fields['primary_issue'].required = True
        if 'instance' in kwargs:
            article = kwargs['instance']
            self.fields['primary_issue'].queryset = article.journal.issue_set.all()
            self.fields['render_galley'].queryset = article.galley_set.all()


class RemoteArticle(forms.ModelForm):
    class Meta:
        model = Article
        fields = ('is_remote', 'remote_url')


class RemoteParse(forms.Form):
    url = forms.CharField(required=True, label="Enter a URL or a DOI.")
    mode = forms.ChoiceField(required=True, choices=(('url', 'URL'), ('doi', 'DOI')))

class ArticleInfo(KeywordModelForm):

    class Meta:
        model = Article
        fields = (
            'title',
            'subtitle',
            'abstract',
            'language',
            'section',
            'license',
            'page_numbers',
        )
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('Title')}),
        }

    def __init__(self, *args, **kwargs):
        elements = kwargs.pop('additional_fields', None)
        submission_summary = kwargs.pop('submission_summary', None)
        journal = kwargs.pop('journal', None)

        if 'instance' in kwargs:
            article = kwargs['instance']
            journal = article.journal
        else:
            article = None

        super(ArticleInfo, self).__init__(*args, **kwargs)
        if journal:
            self.fields['section'].queryset = Section.objects.filter(
                journal=journal,
            )
            self.fields['section'].required = True
            self.fields['license'].queryset = Licence.objects.filter(
                journal=journal,
                available_for_submission=True,
            )
            self.fields['license'].required = True

            abstracts_required = journal.get_setting(
                'general',
                'abstract_required',
            )
            if abstracts_required:
                self.fields['abstract'].required = True

            if not journal.submissionconfiguration.subtitle:
                self.fields.pop('subtitle')

            if not journal.submissionconfiguration.abstract:
                self.fields.pop('abstract')

            if not journal.submissionconfiguration.language:
                self.fields.pop('language')
            else:
                self.fields['language'].initial = journal.submissionconfiguration.default_language

            if not journal.submissionconfiguration.license:
                self.fields.pop('license')
            else:
                self.fields['license'].initial = journal.submissionconfiguration.default_license

            if not journal.submissionconfiguration.keywords:
                self.fields.pop('keywords')

            if not journal.submissionconfiguration.section:
                self.fields.pop('section')
            else:
                self.fields['section'].initial = journal.submissionconfiguration.default_section

        if submission_summary:
            self.fields['non_specialist_summary'].required = True

        if elements:
            for element in elements:
                if element.kind == 'text':
                    self.fields[element.name] = forms.CharField(
                        widget=forms.TextInput(attrs={'div_class': element.width}),
                        required=element.required)
                elif element.kind == 'textarea':
                    self.fields[element.name] = forms.CharField(widget=forms.Textarea,
                                                                required=element.required)
                elif element.kind == 'date':
                    self.fields[element.name] = forms.CharField(
                        widget=forms.DateInput(attrs={'class': 'datepicker', 'div_class': element.width}),
                        required=element.required)

                elif element.kind == 'select':
                    choices = render_choices(element.choices)
                    self.fields[element.name] = forms.ChoiceField(
                        widget=forms.Select(attrs={'div_class': element.width}), choices=choices,
                        required=element.required)

                elif element.kind == 'email':
                    self.fields[element.name] = forms.EmailField(
                        widget=forms.TextInput(attrs={'div_class': element.width}),
                        required=element.required)
                elif element.kind == 'check':
                    self.fields[element.name] = forms.BooleanField(
                        widget=forms.CheckboxInput(attrs={'is_checkbox': True}),
                        required=element.required)

                self.fields[element.name].help_text = element.help_text
                self.fields[element.name].label = element.name

                if article:
                    try:
                        check_for_answer = FieldAnswer.objects.get(field=element, article=article)
                        self.fields[element.name].initial = check_for_answer.answer
                    except FieldAnswer.DoesNotExist:
                        pass

    def save(self, commit=True, request=None):
        article = super(ArticleInfo, self).save(commit=commit)

        if request:
            additional_fields = Field.objects.filter(journal=request.journal)

            for field in additional_fields:
                answer = request.POST.get(field.name, None)
                if answer:
                    try:
                        field_answer = FieldAnswer.objects.get(article=article, field=field)
                        field_answer.answer = answer
                        field_answer.save()
                    except FieldAnswer.DoesNotExist:
                        field_answer = FieldAnswer.objects.create(article=article, field=field, answer=answer)

            request.journal.submissionconfiguration.handle_defaults(article)

        return article


class ExistingAuthor(forms.Form):
    author = forms.ModelChoiceField(
        queryset=Account.objects.all()
    )
