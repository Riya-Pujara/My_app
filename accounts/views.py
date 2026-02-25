from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from datetime import datetime, timedelta
from .models import User, seekerdb,employerdb, Job, Application, Notification
from django.contrib import messages

def login_view(request):
    if request.user.is_authenticated:
        return redirect('homepage')

    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('homepage')   # changed
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html')

    return render(request, 'login.html')

def home(request):
    """Home page showing featured companies and search"""
    return render(request, 'index.html')

def registration(request):
    """Handles Multi-step registration for both Seekers and Employers"""
    if request.method == 'POST':
        role = request.POST.get('role')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('password_confirm')
        full_name = request.POST.get('full_name')

        # Check password match
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('registration')

        # Check if user already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, "User already exists.")
            return redirect('registration')

        user = User.objects.create_user(username=email, email=email, password=password)

        if role == 'Seeker':
            user.is_seeker = True
            user.save()
            seekerdb.objects.create(
                user=user,
                full_name=full_name,
                experience_years=request.POST.get('experience', 0),
                work_type=request.POST.get('work_type'),
                skills=request.POST.get('skills')
            )
        elif role == 'Employer':
            user.is_employer = True
            user.save()
            employerdb.objects.create(
                user=user,
                company_name=request.POST.get('company_name'),
                company_reg_no=request.POST.get('company_id'),
                industry=request.POST.get('industry')
            )

        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'registration.html')

# --- 2. THE ROUTER (Crucial for settings.py LOGIN_REDIRECT_URL) ---

@login_required
def dashboard_redirect(request):
    """Redirects user to the correct dashboard based on their role"""
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    elif request.user.is_employer:
        return redirect('employer_dashboard')
    else:
        return redirect('job_seeker_dashboard')

# --- 3. SEEKER VIEWS ---

@login_required
def job_seeker_dashboard(request):
    """Dashboard logic for Job Seekers"""
    if not request.user.is_seeker:
        return redirect('homepage')
        
    profile = request.user.seeker_profile
    apps = Application.objects.filter(seeker=profile)
    
    # Calculate stats
    stats = {
        'applied_count': apps.count(),
        'weekly_applied': apps.filter(applied_at__gte=datetime.now()-timedelta(days=7)).count(),
        'interview_count': apps.filter(status='Shortlisted').count(),
        # 'view_count': profile.profile_views
    }
    
    # Get recommended jobs (simple logic: matching any skill)
    recommended = Job.objects.filter(is_active=True).order_by('-created_at')[:2]
    
    context = {
        'stats': stats,
        'resume': {
            'filename': profile.resume.name.split('/')[-1] if profile.resume else None,
            'updated_at': profile.resume_updated_at,
            'file': profile.resume
        },
        'recommended_jobs': recommended
    }
    return render(request, 'job_seeker_dashboard.html', context)

@login_required
def update_resume(request):
    """Handles resume upload from dashboard"""
    if request.method == 'POST' and request.FILES.get('resume_file'):
        profile = request.user.seeker_profile
        profile.resume = request.FILES['resume_file']
        profile.save()
    return redirect('job_seeker_dashboard')

# --- 4. EMPLOYER VIEWS ---

@login_required
def employer_dashboard(request):
    
    if not request.user.is_employer:
        return redirect('homepage')

    employer = request.user.employer_profile
    my_jobs = Job.objects.filter(employer=employer)
    applicants = Application.objects.filter(job__employer=employer).order_by('-applied_at')
    
    stats = {
        'active_jobs': my_jobs.filter(is_active=True).count(),
        'total_applicants': applicants.count(),
        'new_today': applicants.filter(applied_at__date=datetime.today()).count(),
        'shortlisted': applicants.filter(status='Shortlisted').count()
    }

    context = {
        'stats': stats,
        'applicants': applicants,
        'active_jobs_list': my_jobs
    }
    return render(request, 'employer_dashboard.html', context)

@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_dashboard(request):
    """Dashboard logic for Platform Administrators"""
    search = request.GET.get('search')
    users = User.objects.all()
    # Filtering logic
    profiles = []
    all_users = User.objects.exclude(is_superuser=True)
    
    if request.GET.get('search'):
        all_users = all_users.filter(Q(username__icontains=request.GET.get('search')) | Q(email__icontains=request.GET.get('search')))

    for u in all_users:
        profiles.append({
            'user': u,
            'role': 'Seeker' if u.is_seeker else 'Employer'
        })

    stats = {
        'total_users': all_users.count(),
        'seekers_count': User.objects.filter(is_seeker=True).count(),
        'employers_count': User.objects.filter(is_employer=True).count(),
        'active_jobs': Job.objects.filter(is_active=True).count(),
        'jobs_today': Job.objects.filter(created_at__date=datetime.today()).count(),
        'pending_verifications':employerdb.objects.filter(is_verified=False).count()
    }

    return render(request, 'admin_dashboard.html', {'profiles': profiles, 'stats': stats})

# --- 6. MISC ACTIONS ---

def logout_view(request):
    logout(request)
    return redirect('homepage')

def job_search(request):
    """Search logic for the home page search bar"""
    query = request.GET.get('q')
    # logic to filter Job model and return results page
    return render(request, 'index.html') # Placeholder

@login_required
def shortlist_candidate(request, applicant_id):
    if request.method == "POST":
        # 1. Fetch the application
        application = get_object_or_404(Application, id=applicant_id)
        
        # 2. Security Check: Ensure the logged-in user is the owner of the job
        if application.job.employer != request.user:
            messages.error(request, "Unauthorized access.")
            return redirect('employer_dashboard')

        # 3. Update Status
        application.status = 'shortlisted' # Ensure 'shortlisted' is in your Model choices
        application.save()
        
        messages.success(request, f"{application.user.get_full_name()} has been shortlisted!")
    
    return redirect('employer_dashboard')


@login_required
def send_notification(request):
    if request.method == "POST":
        applicant_id = request.POST.get('applicant_id')
        message_text = request.POST.get('message')
        
        # 1. Fetch Application
        application = get_object_or_404(Application, id=applicant_id)
        candidate = application.user
        
        # 2. Security Check
        if application.job.employer != request.user:
            messages.error(request, "Unauthorized.")
            return redirect('employer_dashboard')

        # 3. Save Notification to Database (Optional but recommended)
        Notification.objects.create(
            recipient=candidate,
            sender=request.user,
            message=message_text,
            application=application
        )

        # 4. Send Real Email (Optional)
        try:
            subject = f"Update on your application for {application.job.title}"
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [candidate.email]
            
            send_mail(subject, message_text, email_from, recipient_list)
            messages.success(request, f"Notification sent to {candidate.get_full_name()} successfully!")
        except Exception as e:
            messages.warning(request, "Notification saved, but email failed to send.")

    return redirect('employer_dashboard')
@login_required
def post_job(request):
    if not request.user.is_employer:
        return redirect("homepage")

    employer = request.user.employer_profile

    if request.method == "POST":
        Job.objects.create(
            employer=employer,   
            company_name=request.POST.get("company_name"),
            location=request.POST.get("location"),
            contact=request.POST.get("contact"),
            email=request.POST.get("email"),
            job_role=request.POST.get("job_role"),
            experience=request.POST.get("experience"),
            skills=request.POST.get("skills"),
        )

        return redirect('employer_dashboard')

    return render(request, "post_job.html")

