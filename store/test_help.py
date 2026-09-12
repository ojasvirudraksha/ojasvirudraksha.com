from django.test import TestCase, Client
from store.help_views import HELP_LINKS
from store.models import SupportEnquiry, NewsletterSubscriber, InformationPage

class HelpTests(TestCase):
    def test_every_help_page_and_footer_link(self):
        for slug, title in HELP_LINKS:
            response=self.client.get('/pages/'+slug+'/')
            self.assertContains(response, '<h1>'+title+'</h1>', html=True)
            self.assertContains(self.client.get('/'), '/pages/'+slug+'/')
        self.assertEqual(self.client.get('/pages/missing/').status_code,404)

    def test_contact_validation_and_storage(self):
        self.client.post('/contact/',{'name':'Test'})
        self.assertFalse(SupportEnquiry.objects.exists())
        response=self.client.post('/contact/',{'name':'Visitor','email':'test@example.com','subject':'Product question','message':'Which size should I choose?'})
        self.assertRedirects(response,'/contact/')
        self.assertEqual(SupportEnquiry.objects.get().subject,'Product question')
        self.assertEqual(Client(enforce_csrf_checks=True).post('/contact/',{}).status_code,403)

    def test_newsletter_consent_and_duplicate(self):
        self.assertEqual(self.client.post('/newsletter/subscribe/',{'email':'test@example.com'}).status_code,400)
        self.assertFalse(NewsletterSubscriber.objects.exists())
        for email in ('Test@example.com','test@example.com'):
            self.assertRedirects(self.client.post('/newsletter/subscribe/',{'email':email,'consent':'on'}),'/newsletter/')
        self.assertEqual(NewsletterSubscriber.objects.count(),1)
        self.assertEqual(self.client.get('/newsletter/subscribe/').status_code,405)

    def test_admin_page_content_remains_escaped(self):
        page=InformationPage.objects.get(slug='faqs')
        page.body='A question\n<script>alert(1)</script>'
        page.save()
        response=self.client.get('/pages/faqs/')
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
