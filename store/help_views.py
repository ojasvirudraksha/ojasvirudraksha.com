from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import InformationPage, NewsletterSubscriber, SupportEnquiry

HELP_LINKS = [('refund-policy', 'Refund Policy'), ('privacy-policy', 'Privacy Policy'),
              ('shipping-policy', 'Shipping Policy'), ('cancellation-policy', 'Cancellation Policy'),
              ('terms-of-services', 'Terms of Service'), ('faqs', 'FAQs')]

class ContactForm(forms.ModelForm):
    class Meta:
        model = SupportEnquiry
        fields = ('name', 'email', 'subject', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 6, 'maxlength': 5000})}
    def clean_message(self):
        value = self.cleaned_data['message']
        if len(value) > 5000:
            raise forms.ValidationError('Please keep your message under 5,000 characters.')
        return value

class NewsletterForm(forms.Form):
    email = forms.EmailField(max_length=254)
    consent = forms.BooleanField()


def page(request, slug):
    return render(request, 'store/information_page.html', {'info': get_object_or_404(InformationPage, slug=slug)})


def contact(request):
    form = ContactForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your enquiry has been saved for the OJASVIRUDRAKSHA team to review.')
        return redirect('contact_us')
    return render(request, 'store/contact.html', {'form': form})


@require_POST
def subscribe(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        NewsletterSubscriber.objects.update_or_create(email=form.cleaned_data['email'].lower(), defaults={'active': True})
        messages.success(request, 'Thank you — your newsletter signup has been saved.')
        return redirect('newsletter')
    return render(request, 'store/newsletter.html', {'form': form}, status=400)


def newsletter(request):
    return render(request, 'store/newsletter.html', {'form': NewsletterForm()})


def footer_context(request):
    from .models import StoreContact
    return {'help_links': HELP_LINKS, 'store_contact': StoreContact.objects.first()}
