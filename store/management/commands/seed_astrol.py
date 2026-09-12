from django.core.management.base import BaseCommand
from django.core.management import call_command
from store.models import Category, Product
from django.utils.text import slugify

CATS=[
("Rudraksha","rudraksha","Natural Rudraksha selections by Mukhi, origin and size."),
("Malas","malas","Prayer and meditation malas."),
("Bracelets","bracelets","Spiritual bracelets and Dhan Yog styles."),
("Gemstones","gemstones","Natural gemstone selections."),
("Rings","rings","Gemstone and spiritually inspired rings."),
("Pearls","pearls","Pearls and pearl jewelry."),
("Shankh","shankh","Conch shells for puja and traditional use."),
("Tulsi Mala","tulsi-mala","Tulsi malas for devotion and prayer."),
]

RUD=[
(1,"Nepali",18500),(2,"Nepali",5500),(3,"Indonesian",2800),(4,"Nepali",2200),
(5,"Indonesian",1200),(6,"Nepali",1800),(7,"Indonesian",2100),(8,"Nepali",3500),
(9,"Nepali",4200),(10,"Indonesian",4800),(11,"Nepali",6200),(12,"Nepali",7500),
(13,"Nepali",11000),(14,"Nepali",18000),
]

class Command(BaseCommand):
    help="Seed the approved Astrol Rudraksha catalog"
    def handle(self,*args,**kwargs):
        cats={}
        for name,slug,desc in CATS:
            cats[name],_=Category.objects.update_or_create(slug=slug,defaults={"name":name,"description":desc})
        for mukhi,origin,price in RUD:
            name=f"Astrol {mukhi} Mukhi Rudraksha"
            Product.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "category":cats["Rudraksha"],
                    "name":name,
                    "origin":origin,
                    "size":"",
                    "price":price,
                    "image":f"images/exact/rudraksha-{mukhi}.jpg",
                    "short_description":f"{mukhi} Mukhi Rudraksha in the approved Astrol catalog presentation.",
                    "description":"Prototype product listing for the local Astrol storefront.",
                    "featured":True,
                    "active":True,
                }
            )
        self.stdout.write(self.style.SUCCESS("Approved Astrol catalog seeded."))
        call_command('update_product_descriptions', stdout=self.stdout)
