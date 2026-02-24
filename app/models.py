from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.utils.html import mark_safe
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import tempfile
import os
from io import BytesIO
from xhtml2pdf import pisa
from django.utils import timezone
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from django.conf import settings
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

ORDER_TYPE = (
    ("Digitizing" , "Digitizing"),
    ("Vector Conversion" , "Vector Conversion"),
    ("Embroidery Patches" , "Embroidery Patches"),
)


FILE_STATUS = (
    ('original', 'Original Upload'),          # Files uploaded when the order was first placed
    ('after_edit', 'Uploaded After Edit'),  # Files uploaded after the order was edited
)


UNIT_CHOICE = (
    ("inches" , "inches"),
    ("mm" , "mm"),
    ("cm" , "cm"),
)

YES_OR_NO = (
    ("Yes" , "Yes"),
    ("No" , "No"),
)

YES_OR_NO_OR_NOT_SURE = (
    ("Yes" , "Yes"),
    ("No" , "No"),
    ("Not Sure" , "Not Sure"),
)

PAID_UNPAID = (
    ("PAID" , "PAID"),
    ("UNPAID" , "UNPAID"),
)

NOTIFICATION_TYPE = (
    ("success" , "Success"),
    ("danger" , "Error"),
    ("info" , "Info"),
)

PAYMENT_STATUS = (
    ("Pending Payment" , "Pending Payment"),
    ("Success Payment" , "Success Payment"),
)

ORDER_STATUS = (
    # ("Pending" , "Pending"),
    ("On Progress" , "On Progress"),
    ("Delivered" , "Delivered"),
    ("Edited" , "Edited"),
)

ESTIMATE_STATUS = (
    ("On Progress" , "On Progress"),
    ("Delivered" , "Delivered"),
    ("Edited" , "Edited"),
)

# class Coupon(models.Model):
#     code = models.CharField(max_length=50, unique=True)
#     discount_type = models.CharField(max_length=10, choices=[('amount', 'Fixed Amount'), ('percent', 'Percentage')])
#     discount_value = models.DecimalField(max_digits=10, decimal_places=2)
#     active = models.BooleanField(default=True)
#     valid_from = models.DateTimeField()
#     valid_to = models.DateTimeField()
#     usage_limit = models.PositiveIntegerField(default=1)
#     used_count = models.PositiveIntegerField(default=0)

#     def is_valid(self):
#         now = timezone.now()
#         return self.active and self.valid_from <= now <= self.valid_to and self.used_count < self.usage_limit

#     def __str__(self):
#         return self.code

#     class Meta:
#         verbose_name_plural = "20 Coupon Codes" 



# class CouponUsage(models.Model):
#     coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE)
#     ip_address = models.GenericIPAddressField()
#     used_at = models.DateTimeField(auto_now_add=True)
#     success = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.coupon.code} used by IP {self.ip_address}"


# class Contact(models.Model):
#     name = models.CharField(max_length=255)
#     phone = models.CharField(max_length=255)
#     organization_name = models.CharField(max_length=255)
#     email = models.CharField(max_length=255)
#     message = models.TextField()
    
#     def __str__(self):
#         return self.name
    
#     class Meta:
#         verbose_name_plural = "01 Contact"

# class BorderEdge(models.Model):
#     name = models.CharField(max_length=50)
#     image = models.ImageField(upload_to='app/images', max_length=1000)

#     def __str__(self):
#         return self.name
    
#     class Meta:
#         verbose_name_plural = "01 Border Edge"

# class Embroidery(models.Model):
#     title = models.CharField(max_length=50)
#     image = models.ImageField(upload_to='app/images', max_length=1000)

#     def __str__(self):
#         return self.title
    
#     class Meta:
#         verbose_name_plural = "02 Embroidery"


# class Package(models.Model):
#     name = models.CharField(max_length=100)  # e.g., "Package 1"
#     price = models.IntegerField(default=0)  # e.g., 150.00
#     width = models.FloatField()  # e.g., 2
#     height = models.FloatField()  # e.g., 2
#     quantity = models.IntegerField()  # e.g., 100
#     fabric = models.CharField(max_length=100)  # e.g., "Twill Fabric"
#     backing = models.CharField(max_length=100)  # e.g., "Iron-on Backing"

#     def __str__(self):
#         return self.name    
    
#     class Meta:
#         verbose_name_plural = "03 Package"

# class BaseMaterial(models.Model):
#     title = models.CharField(max_length=50)
#     image = models.ImageField(upload_to='app/images', max_length=1000)

#     def __str__(self):
#         return self.title
    
#     class Meta:
#         verbose_name_plural = "04 Base Material"

# class BackingMaterial(models.Model):
#     title = models.CharField(max_length=50)
#     image = models.ImageField(upload_to='app/images', max_length=1000)

#     def __str__(self):
#         return self.title
    
#     class Meta:
#         verbose_name_plural = "05 Backing Material"


# class Pricing(models.Model):
#     PRICING_CHOICES = [
#         ('STITCH', 'Stitch Based Pricing'),
#         ('FLAT', 'Flat Rate Pricing'),
#     ]
    
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     pricing_type = models.CharField(max_length=10, choices=PRICING_CHOICES)
#     selected_at = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return f"{self.get_pricing_type_display()}"

#     class Meta:
#         verbose_name_plural = "16 Pricing"

class DigitizingOrder(models.Model):
    order_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Digitizing')
    design_name = models.CharField(max_length=255, blank=True, null=True)
    po_no = models.CharField(max_length=255 , default='' , blank=True, null=True)
    number_of_colors = models.CharField(max_length=255, default='', blank=True, null=True)
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE)
    type = models.CharField(max_length=255, verbose_name="Fabric")
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    placement = models.CharField(max_length=255)
    required_blending = models.CharField(max_length=255, verbose_name="Do You Required Blending", choices=YES_OR_NO_OR_NOT_SURE, default="")
    Sew_Out_Sample = models.CharField(max_length=255, default='', verbose_name="Real Sew out", choices=YES_OR_NO)
    design_format = models.CharField(max_length=255 , verbose_name="Required Format")
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    addtitoanl_instructions_quote_to_order = models.TextField(default='' ,blank=True , null=True, verbose_name="Additional Instructions When Converting Quote to Order")
    # artwork = models.FileField(upload_to='app/artwork', max_length=1000 , default='', blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    number_of_stitches = models.CharField(max_length=255 , default='', blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Comment")
    width_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Width")
    height_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Height")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    is_free = models.BooleanField(default=False, blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)

    edit_remarks = models.TextField(default='' , blank=True, null=True)
    # coupon = models.ForeignKey('Coupon', on_delete=models.SET_DEFAULT, default=None, blank=True, null=True)
    # discount = models.CharField( max_length=250, default='', blank=True, null=True)
    # total = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True)


    def save(self, *args, **kwargs):
        creating = self.pk is None  # check if this is a new object
        super().save(*args, **kwargs)
        if not self.order_id:
            self.order_id = f"DO-{self.pk}"
            super().save(update_fields=['order_id'])

# Signal to send email when a new order is created
# @receiver(post_save, sender=DigitizingOrder)
# def send_order_email(sender, instance, created, **kwargs):
#     if created:  # only when new order is created
#         email_context = {
#             "order": instance,
#             "user": instance.user,
#             "site_url": "https://portal.highfivedigitizing.com/",
#         }

#         email_subject = f"Your Digitizing Order Received ({instance.order_id}) {instance.design_name} Logo"
#         email_body = render_to_string("app/emails/order_placed_email.html", email_context)

#         email_msg = EmailMessage(
#             subject=email_subject,
#             body=email_body,
#             to=[instance.user.email, 'info@highfivedigitizing.com']
#         )
#         email_msg.content_subtype = "html"

#         # attach order files if you store them in related model
#         for file in instance.artworks.all():
#             email_msg.attach(file.file.name, file.file.read(), file.file.file.content_type)

#         email_msg.send()
            
    def Profile_IMAGE(self):
        if self.thumbnail_image.url:
            
            return mark_safe(f'<img class="main_profile_listdis_img" src="{self.thumbnail_image.url}" width=auto height=100 />')
        else:
           return mark_safe(f'<img  class="main_profile_listdis_img" src="/static/app/assets/images/no-thumbnail.jpg" width=auto height=100 />') 
        
    def Profile_perview(self):
        if self.thumbnail_image:
            return mark_safe(f'<label id="preview_label_id" for="id_image"> <img  class="main_profile_perv" id="main_profile_view" src="{self.thumbnail_image.url}"/></label>') 
        else:
            return mark_safe(f'<label id="preview_label_id" for="id_image"> <img  class="main_profile_perv" id="main_profile_view" src="/static/app/assets/images/no-thumbnail.jpg"/></label>') 
        

    def Crop_perview(self):
            return mark_safe(f'<div id="crop_container"> <img  class="crop_image" style="display:none;position: absolute;left: 0;opacity: 0;" height="300px" width="100%" id="crop_image_id" src="/static/app/assets/images/no-thumbnail.jpg" /> <div class="upload_btn"> <button id="cropButton" type="button" style="padding: 7px 17px;border: none;background: #f39237;color: white;border-radius: 5px;font-size: 17px; cursor:pointer; "><i class="fa fa-upload" aria-hidden="true"></i> Upload</button></div> </div>')
    

        
        


    def __str__(self):
        return self.design_name
    
    class Meta:
        verbose_name_plural = "01 Digitizing Orders"

class VectorOrder(models.Model):
    order_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Vector Conversion')
    design_name = models.CharField(max_length=255)
    number_of_colors = models.CharField(max_length=255, default='', blank=True, null=True)
    po_no = models.CharField(max_length=255 , default='' , blank=True, null=True)
    # name_of_colors = models.CharField(max_length=255)
    # height = models.CharField(max_length=255, default='', blank=True, null=True)
    # width = models.CharField(max_length=255, default='', blank=True, null=True)
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE , default='')
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00)
    design_format = models.CharField(max_length=255)
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    addtitoanl_instructions_quote_to_order = models.TextField(default='' ,blank=True , null=True, verbose_name="Additional Instructions When Converting Quote to Order")
    color_separation = models.CharField(max_length=255, default='', verbose_name="Do You Required Color Separation?", choices=YES_OR_NO)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    
    number_of_stitches = models.CharField(max_length=255 , default='', blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Comment")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    is_free = models.BooleanField(default=False, blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)

    edit_remarks = models.TextField(default='' , blank=True, null=True)

    def save(self, *args, **kwargs):
    #     send_email = False

    # # If order already exists, check if amount has changed
    #     if self.pk:
    #         old_order = VectorOrder.objects.get(pk=self.pk)
    #         if old_order.amount == 0 and self.amount > 0:
    #             send_email = True

    #     # Send email only if amount changed from 0 to some value
    #     if send_email:
    #         subject = 'Order Completed - High Five Digitizing'
    #         to_email = self.user.email
    #         context = {
    #             'user': self.user,
    #             'order': self,
    #             'order_type': self.order_type,
    #             'amount': self.amount,
    #             'instructions': self.instructions_for_user,
    #             'order_link': f"https://digitizing.pythonanywhere.com/"  # Replace with your frontend order URL
    #         }
    #         message = render_to_string('app/emails/order_completed.html', context)
    #         email = EmailMessage(subject, message, to=[to_email])
    #         email.content_subtype = 'html'
    #         email.send()

        super().save(*args, **kwargs)
        if not self.order_id:
            self.order_id = f"VO-{self.pk}"
            super().save(update_fields=['order_id'])

    def __str__(self):
        return self.design_name
    
    class Meta:
        verbose_name_plural = "02 Vector Orders"

class PatchesOrder(models.Model):
    order_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Embroidery Patches')
    design_name = models.CharField(max_length=255)
    po_no = models.CharField(max_length=255 , default='', blank=True, null=True)
    number_of_colors = models.CharField(max_length=255)
    number_of_patches = models.CharField(max_length=255)
    patch_type = models.CharField(max_length=255 , default='')
    patch_backing = models.CharField(max_length=255 , default='')
    border = models.CharField(max_length=255 , default='')
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE, default='')
    delivery_address = models.CharField(max_length=255 , verbose_name="Shipping Address", default='', blank=True, null=True)
    
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    addtitoanl_instructions_quote_to_order = models.TextField(default='' ,blank=True , null=True, verbose_name="Additional Instructions When Converting Quote to Order")
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    number_of_colors_for_admin = models.CharField(max_length=255 , default='', blank=True, null=True, verbose_name="Number Of Colors")
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Instructions")
    shipping_address = models.TextField(default='' ,blank=True , null=True , verbose_name="Shipping Address")
    width_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Width")
    height_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Height")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    is_free = models.BooleanField(default=False, blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)

    edit_remarks = models.TextField(default='' , blank=True, null=True)

    def save(self, *args, **kwargs):
    #     send_email = False

    # # If order already exists, check if amount has changed
    #     if self.pk:
    #         old_order = PatchesOrder.objects.get(pk=self.pk)
    #         if old_order.amount == 0 and self.amount > 0:
    #             send_email = True

    #     # Send email only if amount changed from 0 to some value
    #     if send_email:
    #         subject = 'Order Complated - High Five Digitizing'
    #         to_email = self.user.email
    #         context = {
    #             'user': self.user,
    #             'order': self,
    #             'amount': self.amount,
    #             'order_type': self.order_type,
    #             'instructions': self.instructions_for_user,
    #             'order_link': f"https://digitizing.pythonanywhere.com/"  # Replace with your frontend order URL
    #         }
    #         message = render_to_string('app/emails/order_completed.html', context)
    #         email = EmailMessage(subject, message, to=[to_email])
    #         email.content_subtype = 'html'
    #         email.send()

        super().save(*args, **kwargs)
        if not self.order_id:
            self.order_id = f"PO-{self.pk}"
            super().save(update_fields=['order_id'])

    def __str__(self):
        return self.design_name
    
    class Meta:
        verbose_name_plural = "03 Patches Orders"

class DigitizingEstimate(models.Model):
    estimate_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Digitizing')
    design_name = models.CharField(max_length=255)
    po_no = models.CharField(max_length=255 , default='' , blank=True, null=True)
    number_of_colors = models.CharField(max_length=255, default='', blank=True, null=True)
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE)
    type = models.CharField(max_length=255, verbose_name="Fabric")
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    placement = models.CharField(max_length=255)
    required_blending = models.CharField(max_length=255, verbose_name="Do You Required Blending", choices=YES_OR_NO_OR_NOT_SURE, default="")
    Sew_Out_Sample = models.CharField(max_length=255, default='', verbose_name="Real Sew out", choices=YES_OR_NO)
    design_format = models.CharField(max_length=255 , verbose_name="Required Format")
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    # artwork = models.FileField(upload_to='app/artwork', max_length=1000 , default='', blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    number_of_stitches = models.CharField(max_length=255 , default='', blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Comment")
    width_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Width")
    height_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Height")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)
    edit_remarks = models.TextField(default='' , blank=True, null=True)

    converted_to_order = models.BooleanField(default=False, blank=True, null=True)

    def save(self, *args, **kwargs):
    #     send_email = False

    # # If order already exists, check if amount has changed
    #     if self.pk:
    #         old_order = DigitizingEstimate.objects.get(pk=self.pk)
    #         if old_order.amount == 0 and self.amount > 0:
    #             send_email = True

    #     # Send email only if amount changed from 0 to some value
    #     if send_email:
    #         subject = 'Estimate Completed - High Five Digitizing'
    #         to_email = self.user.email
    #         context = {
    #             'user': self.user,
    #             'design_name': self.design_name,
    #             'estimate': self,
    #             'amount': self.amount,
    #             'order_type': self.order_type,
    #             'instructions': self.instructions_for_user,
    #             'order_link': f"https://digitizing.pythonanywhere.com/"  # Replace with your frontend order URL
    #         }
    #         message = render_to_string('app/emails/estimate_completed.html', context)
    #         email = EmailMessage(subject, message, to=[to_email])
    #         email.content_subtype = 'html'
    #         email.send()

        super().save(*args, **kwargs)
        if not self.estimate_id:
            self.estimate_id = f"DQ-{self.pk}"
            super().save(update_fields=['estimate_id'])

    def __str__(self):
        return self.design_name
    
    class Meta:
        verbose_name_plural = "04 Digitizing Quotes"

class VectorEstimate(models.Model):
    estimate_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Vector Conversion')
    design_name = models.CharField(max_length=255)
    number_of_colors = models.CharField(max_length=255, default='', blank=True, null=True)
    po_no = models.CharField(max_length=255 , default='' , blank=True, null=True)
    # name_of_colors = models.CharField(max_length=255)
    # height = models.CharField(max_length=255, default='', blank=True, null=True)
    # width = models.CharField(max_length=255, default='', blank=True, null=True)
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE , default='')
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00)
    design_format = models.CharField(max_length=255)
    color_separation = models.CharField(max_length=255, default='', verbose_name="Do You Required Color Separation?", choices=YES_OR_NO)
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)
    
    number_of_stitches = models.CharField(max_length=255 , default='', blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Comment")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)
    edit_remarks = models.TextField(default='' , blank=True, null=True)
    converted_to_order = models.BooleanField(default=False, blank=True, null=True)

    def save(self, *args, **kwargs):
    #     send_email = False

    # # If order already exists, check if amount has changed
    #     if self.pk:
    #         old_order = VectorEstimate.objects.get(pk=self.pk)
    #         if old_order.amount == 0 and self.amount > 0:
    #             send_email = True

    #     # Send email only if amount changed from 0 to some value
    #     if send_email:
    #         subject = 'Your Estimate Has Been Updated'
    #         to_email = self.user.email
    #         context = {
    #             'user': self.user,
    #             'design_name': self.design_name,
    #             'amount': self.amount,
    #             'order_type': self.order_type,
    #             'instructions': self.instructions_for_user,
    #             'order_link': f"https://digitizing.pythonanywhere.com/"  # Replace with your frontend order URL
    #         }
    #         message = render_to_string('app/emails/estimate_completed.html', context)
    #         email = EmailMessage(subject, message, to=[to_email])
    #         email.content_subtype = 'html'
    #         email.send()

        super().save(*args, **kwargs)
        if not self.estimate_id:
            self.estimate_id = f"VQ-{self.pk}"
            super().save(update_fields=['estimate_id'])

    def __str__(self): 
        return self.design_name
    
    class Meta:
        verbose_name_plural = "05 Vector Quotes"

class PatchesEstimates(models.Model):
    estimate_id = models.CharField(max_length=250, default='', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=255 , choices=ORDER_TYPE, default='Embroidery Patches')
    design_name = models.CharField(max_length=255)
    po_no = models.CharField(max_length=255 , default='', blank=True, null=True)
    number_of_colors = models.CharField(max_length=255)
    number_of_patches = models.CharField(max_length=255)
    patch_type = models.CharField(max_length=255 , default='')
    patch_backing = models.CharField(max_length=255 , default='')
    border = models.CharField(max_length=255 , default='')
    payment_status = models.CharField(max_length=250 , choices=PAYMENT_STATUS , default='')
    order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
    height = models.CharField(max_length=255, default='', blank=True, null=True)
    width = models.CharField(max_length=255, default='', blank=True, null=True)
    unit = models.CharField(max_length=255 , choices=UNIT_CHOICE , default='')
    delivery_address = models.CharField(max_length=255 , verbose_name="Shipping Address", default='', blank=True, null=True)
    addtitoanl_instructions = models.TextField(default='' ,blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    number_of_colors_for_admin = models.CharField(max_length=255 , default='', blank=True, null=True, verbose_name="Number Of Colors")
    amount = models.DecimalField(max_digits=10, decimal_places=2 , default=0.00, blank=True, null=True, verbose_name="Total Price")
    instructions_for_user = models.TextField(default='' ,blank=True , null=True , verbose_name="Designer Instructions")
    shipping_address = models.TextField(default='' ,blank=True , null=True , verbose_name="Shipping Address")
    width_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Width")
    height_for_admin = models.CharField(max_length=255 ,default='', blank=True, null=True, verbose_name="Height")
    # file = models.FileField(upload_to="app/files", max_length=1000, default='', blank=True, null=True)
    thumbnail_image = models.ImageField(upload_to='app/images', max_length=1000, default='', blank=True, null=True)
    edit_remarks = models.TextField(default='' , blank=True, null=True)
    converted_to_order = models.BooleanField(default=False, blank=True, null=True)

    def save(self, *args, **kwargs):
    #     send_email = False

    # # If order already exists, check if amount has changed
    #     if self.pk:
    #         old_order = PatchesEstimates.objects.get(pk=self.pk)
    #         if old_order.amount == 0 and self.amount > 0:
    #             send_email = True

    #     # Send email only if amount changed from 0 to some value
    #     if send_email:
    #         subject = 'Your Estimate Has Been Updated'
    #         to_email = self.user.email
    #         context = {
    #             'user': self.user,
    #             'design_name': self.design_name,
    #             'amount': self.amount,
    #             'order_type': self.order_type,
    #             'instructions': self.instructions_for_user,
    #             'order_link': f"https://digitizing.pythonanywhere.com/"  # Replace with your frontend order URL
    #         }
    #         message = render_to_string('app/emails/estimate_completed.html', context)
    #         email = EmailMessage(subject, message, to=[to_email])
    #         email.content_subtype = 'html'
    #         email.send()

        super().save(*args, **kwargs)
        if not self.estimate_id:
            self.estimate_id = f"PQ-{self.pk}"
            super().save(update_fields=['estimate_id'])

    def __str__(self):
        return self.design_name
    
    class Meta:
        verbose_name_plural = "06 Patches Quotes"

# class Edits(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     # Design_Name_Order_ID = models.CharField(max_length=255 , verbose_name="Design Name/Order ID")
#     design_digitizing = models.ForeignKey('DigitizingOrder', on_delete=models.CASCADE, null=True, blank=True)
#     design_vector = models.ForeignKey('VectorOrder', on_delete=models.CASCADE, null=True, blank=True)
#     design_patches = models.ForeignKey('PatchesOrder', on_delete=models.CASCADE, null=True, blank=True)
#     order_status = models.CharField(max_length=250 , choices=ORDER_STATUS , default='')
#     edit_instructions = models.TextField(default='' ,blank=True , null=True)
#     artwork = models.FileField(upload_to='app/artwork', max_length=1000 , default='', blank=True , null=True)
#     created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

#     def __str__(self):
#         return f"{self.user}:{self.edit_instructions}"
    
#     class Meta:
#         verbose_name_plural = "12 Edits"

# class Notification(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE , default=None)
#     title = models.CharField(max_length=255)
#     message = models.TextField(default='')
#     notification_type = models.CharField(max_length=255 , choices=NOTIFICATION_TYPE , default='')
#     for_home = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

#     def __str__(self):
#         return self.title
    
#     class Meta:
#         verbose_name_plural = "13 Notifications"
        

# class OpenTicket(models.Model):
#     PRIORITY_CHOICES = [
#         ('High', 'High'),
#         ('Medium', 'Medium'),
#         ('Low', 'Low'),
#     ]
#     TICKET_STATUS = [
#         ('Pending', 'Pending'),
#         ('Answered', 'Answered'),
#         ('Closed', 'Closed'),
#     ]
#     user = models.ForeignKey(User, on_delete=models.CASCADE , default=None)
#     subject = models.CharField(max_length=255)
#     design_digitizing = models.ForeignKey('DigitizingOrder', on_delete=models.CASCADE, null=True, blank=True)
#     design_vector = models.ForeignKey('VectorOrder', on_delete=models.CASCADE, null=True, blank=True)
#     design_patches = models.ForeignKey('PatchesOrder', on_delete=models.CASCADE, null=True, blank=True)
#     priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
#     ticket_status = models.CharField(max_length=10, choices=TICKET_STATUS , default="Pending")
#     status = models.BooleanField(default=False , blank=True, null=True , verbose_name="Active")
#     message = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user} - {self.ticket_status}"

#     class Meta:
#         verbose_name_plural = "14 Open Tickets"    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile_no = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=100, blank=True)
    business_phone_no = models.CharField(max_length=100, blank=True, verbose_name="Office No")
    city = models.CharField(max_length=100, blank=True)

    # Additional fields based on the form
    website = models.URLField(max_length=200, blank=True)
    invoice_email = models.EmailField(blank=True)
    reference = models.CharField(max_length=50, blank=True, choices=[
        ('search_engine', 'Search Engine'),
        ('customer_reference', 'Customer Reference'),
        ('salesman', 'Salesman'),
        ('other', 'Other'),
    ])
    state = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.first_name}'s Profile"
    
    class Meta:
        verbose_name_plural = "08 Profiles" 

class Invoice(models.Model):
    invoice_id = models.CharField(max_length=100, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    payment_status = models.CharField(max_length=20, choices=PAID_UNPAID, default='UNPAID')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preview_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    invoice_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.user:
            return f"{self.user}'s Invoice"
        return f"Invoice #{self.pk}"
    
    def InvoicePreview(self):
        return mark_safe(f"<div class='invoice_preview_button'><a href=/invoice_preview/?token={self.preview_token} class='btn btn-primary'>Preview</a></div>")

        
    class Meta:
        verbose_name_plural = "07 Invoice" 


    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if this is a new invoice before saving

        old_payment_status = None
        if not is_new:
            old_payment_status = Invoice.objects.get(pk=self.pk).payment_status

        super().save(*args, **kwargs)  # Save initially to get pk for new objects

        # Assign invoice_id if new
        if is_new and not self.invoice_id:
            self.invoice_id = f"INV-{self.pk}"
            super().save(update_fields=['invoice_id'])

        # Generate secure token if not set
        if not self.preview_token:
            self.preview_token = uuid.uuid4().hex
            super().save(update_fields=['preview_token'])

        # If payment status changed from UNPAID to PAID, update order payment_status
        if old_payment_status != 'PAID' and self.payment_status == 'PAID':
            self.update_order_payments()
        
    def update_order_payments(self):
        for item in self.items.all():
            order_number = item.order_number

            # Try to update DigitizingOrder
            digitizing = DigitizingOrder.objects.filter(order_id=order_number).first()
            if digitizing and digitizing.payment_status == "Pending Payment":
                digitizing.payment_status = "Success Payment"
                digitizing.save()
                continue

            # Try to update VectorOrder
            vector = VectorOrder.objects.filter(order_id=order_number).first()
            if vector and vector.payment_status == "Pending Payment":
                vector.payment_status = "Success Payment"
                vector.save()
                continue

            # Try to update PatchesOrder
            patches = PatchesOrder.objects.filter(order_id=order_number).first()
            if patches and patches.payment_status == "Pending Payment":
                patches.payment_status = "Success Payment"
                patches.save()
                continue

            # Send invoice email only after invoice_id is set
            # if self.user and self.user.email:
            #     # Get invoice items
            #     invoice_items = InvoiceItem.objects.filter(invoice=self)
            #     print("items", invoice_items)
                
            #     # Generate PDF
            #     pdf_file = self.generate_pdf(invoice_items)
                
            #     # Send email with PDF attachment
            #     subject = "Your Invoice is Ready"
            #     to_email = self.user.email
            #     payment_url = f"http://192.168.18.81:8888/invoice/{self.id}"  # Replace with production URL

            #     context = {
            #         'user': self.user,
            #         'invoice': self,
            #         'payment_url': payment_url,
            #     }

            #     message = render_to_string('app/emails/invoice_email.html', context)
            #     email = EmailMessage(subject, message, to=[to_email])
            #     email.content_subtype = 'html'
                
            #     # Attach the PDF
            #     email.attach(f'Invoice-{self.invoice_id}.pdf', pdf_file, 'application/pdf')
            #     email.send()

    def generate_pdf(self, invoice_items):
        

        context = {
            'invoice': self,
            'items': invoice_items,
            'user': self.user,
            'company_name': 'New Digitizing',
            'company_address': 'Your Company Address',
            'company_phone': '031434343',
            'company_email': 'highfivedigitizing@gmail.com',
            'company_website': 'www.highfivedigitizing.com',
            # 'logo_url': f"/static/app/assets/images/high_five_FINALLL__1_-removebg-preview.png",
        }

        html_string = render_to_string('app/pdf/invoice_pdf.html', context)
        result = BytesIO()
        pdf_status = pisa.CreatePDF(src=html_string, dest=result)
        if not pdf_status.err:
            return result.getvalue()
        return None

    def generate_styled_invoice_pdf(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        styles = getSampleStyleSheet()

        # Custom styles
        company_style = ParagraphStyle('CompanyStyle', parent=styles['Title'], fontSize=28, textColor=colors.HexColor('#4285f4'), fontName='Helvetica-Bold', alignment=TA_LEFT)
        invoice_title_style = ParagraphStyle('InvoiceTitleStyle', parent=styles['Title'], fontSize=36, textColor=colors.HexColor('#4285f4'), fontName='Helvetica-Bold', alignment=TA_RIGHT)

        story = []

        # Logo
        image_path = os.path.join(settings.BASE_DIR, 'static/app/assets/images/high_five_FINALLL__1_-removebg-preview.png')
        logo = Image(image_path, width=2.2 * inch, height=2 * inch)

        right_column = Paragraph(f'''
            <para align="right">
                <font size="36" color="#4285f4"><b>INVOICE</b></font><br/>
                <font size="10" color="#333333">
                    <b>INVOICE NO:</b> {self.invoice_id}<br/>
                    <b>INVOICE DATE:</b> {self.invoice_date.strftime('%d %b %Y')}<br/>
                    <b>EXPIRY DATE:</b> {self.due_date.strftime('%d %b %Y') if self.due_date else 'N/A'}
                </font>
            </para>
        ''', styles['Normal'])

        header_data = [[logo, right_column]]
        header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        story.append(header_table)

        # Blue line
        line_table = Table([['']], colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 3, colors.HexColor('#4285f4')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(line_table)

        # Status
        status_color = '#dc3545' if self.payment_status == 'UNPAID' else '#28a745'
        status_data = [[Paragraph(f'<para align="center"><font color="white"><b>{self.payment_status}</b></font></para>', styles['Normal'])]]
        status_table = Table(status_data, colWidths=[7*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(status_color)),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 20))

        # Customer Info
        user = self.user
        customer_info = f'''
            <para>
                <font size="10" color="#666666"><b>INVOICE TO</b></font><br/>
                <font size="14" color="#333333"><b>{user.get_full_name() or user.first_name}</b></font><br/>
                <font size="11" color="#666666">{user.email}</font>
            </para>
        '''
        customer_table = Table([[Paragraph(customer_info, styles['Normal'])]], colWidths=[7*inch])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(customer_table)
        story.append(Spacer(1, 25))

        # Table Headers
        table_data = [['S.NO', 'ORDER NO', 'PO NUMBER', 'DESIGN NAME', 'ORDER DATE', 'TYPE', 'PRICE']]
        for i, item in enumerate(self.items.all(), 1):
            table_data.append([
                str(i),
                item.order_number or '-',
                item.po_no or '-',
                item.item_name,
                item.order_date.strftime('%d %b %Y') if item.order_date else '-',
                item.item_type,
                f"${item.total:.2f}"
            ])

        table = Table(table_data, colWidths=[0.5*inch, 1*inch, 1*inch, 2*inch, 1*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4285f4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        story.append(table)
        story.append(Spacer(1, 25))

        # Totals
        totals_data = [['', '', 'Subtotal:', f"${self.total:.2f}"]]
        if hasattr(self, 'tax_amount') and self.tax_amount > 0:
            totals_data.append(['', '', 'Tax:', f"${self.tax_amount:.2f}"])
        totals_data.append(['', '', 'TOTAL AMOUNT:', f"${self.total:.2f} USD"])

        totals_table = Table(totals_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (2, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 0), (-1, -2), 11),
            ('FONTSIZE', (2, -1), (-1, -1), 14),
            ('TEXTCOLOR', (2, -1), (-1, -1), colors.HexColor('#4285f4')),
            ('LINEABOVE', (2, -1), (-1, -1), 2, colors.HexColor('#4285f4')),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 40))

        # Footer
        footer_text = '''
            <para align="center">
                <font size="11" color="#4285f4"><b>High Five Digitizing</b></font><br/>
                Thank you for your business!
            </para>
        '''
        footer_table = Table([[Paragraph(footer_text, styles['Normal'])]], colWidths=[7*inch])
        footer_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ]))
        story.append(footer_table)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def send_invoice_email(self):
        print("okkkk")
        from django.template.loader import render_to_string
        from django.core.mail import EmailMessage

        if self.user and self.user.email:
            invoice_items = self.items.all()
            if not invoice_items.exists():
                return  # Don't send if no items

            pdf_file = self.generate_styled_invoice_pdf()

            subject = f"Your Invoice is Ready {self.invoice_id}"
            get_pro = self.user.profile
            if get_pro.invoice_email:
                to_email = get_pro.invoice_email
                print("if", to_email)
            else:
                to_email = self.user.email
                print("else", to_email)
            payment_url = f"https://portal.highfivedigitizing.com/invoice_preview?token={self.preview_token}"
            # payment_url = f"https://portal.highfivedigitizing.com/invoice_preview/{self.id}"

            context = {
                'user': self.user,
                'invoice': self,
                'payment_url': payment_url,
                "site_url":"https://portal.highfivedigitizing.com/"
            }

            message = render_to_string('app/emails/invoice_email.html', context)
            email = EmailMessage(subject, message, to=[to_email])
            email.content_subtype = 'html'
            email.attach(f'Invoice-{self.invoice_id}.pdf', pdf_file, 'application/pdf')
            email.send()



class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255, default='')
    po_no = models.CharField(max_length=255, default='', blank=True, null=True)
    item_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'Digitizing', 'Vector'
    order_number = models.CharField(max_length=100, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    # def save(self, *args, **kwargs):
    #     self.total = self.quantity * self.unit_price
    #     super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.invoice.invoice_id}"

    class Meta:
        verbose_name_plural = "18 invoice Items" 

class CustomOffer(models.Model):
    title = models.CharField(max_length=250)
    detail = models.TextField(verbose_name="Message")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "18 Custom Offers" 




class InvoiceForPortalUser(models.Model):
    invoice_id = models.CharField(max_length=250, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Design_Name_Order_ID = models.CharField(max_length=255 , verbose_name="Design Name/Order ID")
    order_digitizing = models.ForeignKey('DigitizingOrder', on_delete=models.CASCADE, null=True, blank=True)
    order_vector = models.ForeignKey('VectorOrder', on_delete=models.CASCADE, null=True, blank=True)
    order_patches = models.ForeignKey('PatchesOrder', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=250, choices=PAID_UNPAID)
    created_at = models.DateTimeField(auto_now_add=True , blank=True, null=True)

    def __str__(self):
        if self.user:
            return f"{self.user.first_name}'s Invoice"
        
    class Meta:
        verbose_name_plural = "19 Invoice For Portal" 

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if this is a new invoice before saving

        super().save(*args, **kwargs)  # Save initially to get primary key (pk)

        # Assign invoice_id if new
        if is_new and not self.invoice_id:
            self.invoice_id = f"INV-{self.pk}"
            super().save(update_fields=['invoice_id'])


FILE_TYPE_CHOICES = [
    ('placing_edit', 'Submitted during placing edit'),
    ('quote_to_order', 'Submitted during quote-to-order conversion'),
]


class DigitizingEstimateArtwork(models.Model):

    estimate = models.ForeignKey(DigitizingEstimate, on_delete=models.CASCADE, related_name='artworks')
    # is_edited = models.BooleanField(default=False)
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class VectorEstimateArtwork(models.Model):

    estimate = models.ForeignKey(VectorEstimate, on_delete=models.CASCADE, related_name='artworks')
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PatchEstimateArtwork(models.Model):

    estimate = models.ForeignKey(PatchesEstimates, on_delete=models.CASCADE, related_name='artworks')
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class DigitizingOrderArtwork(models.Model):
    order = models.ForeignKey(DigitizingOrder, on_delete=models.CASCADE, related_name='artworks')
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)




class VectorOrderArtwork(models.Model):
    order = models.ForeignKey(VectorOrder, on_delete=models.CASCADE, related_name='artworks')
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PatchOrderArtwork(models.Model):
    order = models.ForeignKey(PatchesOrder, on_delete=models.CASCADE, related_name='artworks')
    order_file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)

def send_order_email(order, prefix="Order", site_url="https://portal.highfivedigitizing.com/"):
    """
    Generic email sender for any order type.
    order: order instance
    prefix: string like 'Digitizing', 'Vector', 'Patch', etc.
    """
    # Ensure order_id exists
    if not getattr(order, "order_id", None):
        order.order_id = f"{prefix[:1].upper()}O-{order.pk}"
        order.save(update_fields=['order_id'])

    email_context = {
        "order": order,
        "user": order.user,
        "site_url": site_url,
    }

    email_subject = f"Your {prefix} Order Received ({order.order_id}) {order.design_name} Logo"
    email_body = render_to_string("app/emails/order_placed_email.html", email_context)

    email_msg = EmailMessage(
        subject=email_subject,
        body=email_body,
        to=[order.user.email, 'info@highfivedigitizing.com']
    )
    email_msg.content_subtype = "html"

    # Attach all artworks if any
    if hasattr(order, 'artworks'):
        for artwork in order.artworks.all():
            with artwork.file.open("rb") as f:
                email_msg.attach(artwork.file.name, f.read(), "application/octet-stream")

    email_msg.send()

# --- Signals for DigitizingOrder ---
# @receiver(post_save, sender=DigitizingOrder)
# def digitizing_order_created(sender, instance, created, **kwargs):
#     if created:
#         send_order_email(instance, prefix="Digitizing")

# @receiver(post_save, sender=DigitizingOrderArtwork)
# def digitizing_artwork_created(sender, instance, created, **kwargs):
#     if created and instance.order:
#         send_order_email(instance.order, prefix="Digitizing")


# # --- Signals for VectorOrder ---
# @receiver(post_save, sender=VectorOrder)
# def vector_order_created(sender, instance, created, **kwargs):
#     if created:
#         send_order_email(instance, prefix="Vector")

# @receiver(post_save, sender=VectorOrderArtwork)
# def vector_artwork_created(sender, instance, created, **kwargs):
#     if created and instance.order:
#         send_order_email(instance.order, prefix="Vector")


# # --- Signals for PatchesOrder ---
# @receiver(post_save, sender=PatchesOrder)
# def patch_order_created(sender, instance, created, **kwargs):
#     if created:
#         send_order_email(instance, prefix="Patch")

# @receiver(post_save, sender=PatchOrderArtwork)
# def patch_artwork_created(sender, instance, created, **kwargs):
#     if created and instance.order:
#         send_order_email(instance.order, prefix="Patch")

class DigitizingEstimateFile(models.Model):
    estimate = models.ForeignKey(DigitizingEstimate, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/files', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class VectorEstimateFile(models.Model):
    estimate = models.ForeignKey(VectorEstimate, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/files', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PatchEstimateFile(models.Model):
    estimate = models.ForeignKey(PatchesEstimates, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/files', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class DigitizingOrderFile(models.Model):
    order = models.ForeignKey(DigitizingOrder, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/artwork', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class VectorOrderFile(models.Model):
    order = models.ForeignKey(VectorOrder, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/files', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PatchOrderFile(models.Model):
    order = models.ForeignKey(PatchesOrder, on_delete=models.CASCADE, related_name='files')
    is_visible = models.BooleanField(default=True)
    file_status = models.CharField(max_length=250, default='', choices=FILE_STATUS)
    file = models.FileField(upload_to='app/files', max_length=1000)
    uploaded_at = models.DateTimeField(auto_now_add=True)