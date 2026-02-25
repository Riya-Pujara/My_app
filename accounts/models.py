from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    is_seeker = models.BooleanField(default=False)
    is_employer = models.BooleanField(default=False)
    
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return self.username


class seekerdb(models.Model):
    WORK_TYPES = (
        ('Remote', 'Remote'),
        ('On-site', 'On-site'),
        ('Hybrid', 'Hybrid'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seeker_profile')
    full_name = models.CharField(max_length=255)
    experience_years = models.IntegerField(default=0)
    work_type = models.CharField(max_length=20, choices=WORK_TYPES, default='Remote')
    skills = models.TextField(help_text="Enter skills separated by commas")
    
    # Resume Management
    resume = models.FileField(
        upload_to='resumes/', 
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])],
        null=True, blank=True
    )
    resume_updated_at = models.DateTimeField(auto_now=True)
    
    profile_views = models.IntegerField(default=0)

    def __str__(self):
        return self.full_name

class employerdb(models.Model):
    INDUSTRIES = (
        ('IT', 'Information Technology'),
        ('Finance', 'Finance & Banking'),
        ('Healthcare', 'Healthcare'),
        ('Marketing', 'Marketing'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255)
    company_reg_no = models.CharField(max_length=100)
    industry = models.CharField(max_length=50, choices=INDUSTRIES)
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    is_verified = models.BooleanField(default=False) 

    def __str__(self):
        return self.company_name

class Job(models.Model):
    employer = models.ForeignKey(
        employerdb,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    contact = models.CharField(max_length=15)
    email = models.EmailField()
    job_role = models.CharField(max_length=200)
    experience = models.CharField(max_length=100)
    skills = models.TextField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Application(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Shortlisted', 'Shortlisted'),
        ('Rejected', 'Rejected'),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applicants')
    seeker = models.ForeignKey(seekerdb, on_delete=models.CASCADE, related_name='my_applications')
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    match_score = models.IntegerField(default=0)

    class Meta:
        unique_together = ('job', 'seeker') 

    def __str__(self):
        return f"{self.seeker.full_name} -> {self.job.title}"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender_name = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"