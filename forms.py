from django import forms

from submission import models


class PublicationInfo(forms.ModelForm):
    class Meta:
        model = models.Article
        fields = ('date_accepted', 'date_published', 'page_numbers', 'primary_issue', 'peer_reviewed')

    def __init__(self, *args, **kwargs):
        super(PublicationInfo, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            article = kwargs['instance']
            self.fields['primary_issue'].queryset = article.journal.issue_set.all()
            self.fields['date_accepted'].widget.attrs['class'] = 'datepicker'
            self.fields['date_published'].widget.attrs['class'] = 'datepicker'