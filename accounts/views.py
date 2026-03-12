from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from .models import User, seekerdb, employerdb, Job, Application, Notification
from django.contrib import messages
from .forms import ResumeForm
from urllib.parse import quote

@login_required
def suspend_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    user.is_active = False
    user.save()

    return redirect('admin_dashboard')
    
from django.contrib import messages

def login_view(request):

    if request.method == "POST":

        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("homepage")

        else:
            messages.error(request, "Invalid email or password")
            return redirect("login")

    return render(request, "login.html")

def home(request):
    """Home page showing search and latest jobs."""
    latest_jobs = Job.objects.filter(is_active=True).order_by('-created_at')[:6]
    return render(request, 'index.html', {'latest_jobs': latest_jobs})

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


@login_required
def manage_resume(request):
    """Form-based resume upload/edit page"""
    if not request.user.is_seeker:
        return redirect('homepage')

    profile = request.user.seeker_profile

    if request.method == 'POST':
        form = ResumeForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('job_seeker_dashboard')
    else:
        form = ResumeForm(instance=profile)

    return render(request, 'manage_resume.html', {'form': form})


@login_required
def apply_job(request, job_id):
    """Create an Application record then redirect to email compose."""
    if not request.user.is_seeker:
        return redirect('homepage')

    job = get_object_or_404(Job, id=job_id, is_active=True)
    seeker_profile = request.user.seeker_profile

    application, created = Application.objects.get_or_create(
        job=job,
        seeker=seeker_profile,
    )

    if created:
        messages.success(request, f"You have applied for {job.job_role}.")
    else:
        messages.info(request, f"You have already applied for {job.job_role}.")

    subject = f"Application for {job.job_role}"
    body = (
        f"Hello {job.company_name}, I would like to apply for the "
        f"{job.job_role} position."
    )

    gmail_url = (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={quote(job.email)}"
        f"&su={quote(subject)}"
        f"&body={quote(body)}"
    )

    return redirect(gmail_url)
@login_required
def apply_job(request, job_id):
    if not request.user.is_seeker:
        return redirect('homepage')

    job = get_object_or_404(Job, id=job_id, is_active=True)
    seeker = request.user.seeker_profile

    # prevent duplicate applications
    application, created = Application.objects.get_or_create(
        job=job,
        seeker=seeker
    )

    if created:
        messages.success(request, "Application submitted successfully.")
    else:
        messages.info(request, "You already applied for this job.")

    return redirect('job_seeker_dashboard')
@login_required
def my_applications(request):
    if not request.user.is_seeker:
        return redirect('homepage')

    seeker = request.user.seeker_profile
    applications = Application.objects.filter(seeker=seeker).order_by('-applied_at')

    return render(request, 'my_applications.html', {
        'applications': applications
    })
# --- 4. EMPLOYER VIEWS ---

@login_required
def employer_dashboard(request):
    if not request.user.is_employer:
        return redirect('homepage')

    employer = request.user.employer_profile
    my_jobs = Job.objects.filter(employer=employer)
    applicants = Application.objects.filter(job__employer=employer).order_by('-applied_at')
    
    context = {
        'stats': {
            'active_jobs': my_jobs.filter(is_active=True).count(),
            'total_applicants': applicants.count(),
            'new_today': applicants.filter(applied_at__date=datetime.today()).count(),
            'shortlisted': applicants.filter(status='Shortlisted').count(),
        },
        'pending_count': applicants.filter(status='Pending').count(),
        'shortlisted_count': applicants.filter(status='Shortlisted').count(),
        'applicants': applicants,
        'active_jobs_list': my_jobs
    }
    return render(request, 'employer_dashboard.html', context)


@login_required
def my_profile(request):
    if not request.user.is_seeker:
        return redirect('homepage')

    profile = request.user.seeker_profile

    return render(request, 'my_profile.html', {'profile': profile})

@login_required
def employer_profile(request):
    if not request.user.is_employer:
        return redirect('homepage')

    profile = request.user.employer_profile

    return render(request, 'employer_profile.html', {'profile': profile})


@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_dashboard(request):

    profiles = seekerdb.objects.all()

    stats = {
        "total_users": profiles.count(),
        "seekers_count": seekerdb.objects.count(),
        "employers_count": employerdb.objects.count(),
        "active_jobs": 0,
        "jobs_today": 0,
        "pending_verifications": 0
    }

    return render(request, "admin_dashboard.html", {
        "profiles": profiles,
        "stats": stats
    })
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

    if request.method != "POST":
        return redirect('employer_dashboard')

    application = get_object_or_404(Application, id=applicant_id)

    # Security check (employer owns job)
    if not request.user.is_employer or application.job.employer.user != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('employer_dashboard')

    # Update status
    application.status = "Shortlisted"
    application.save()

    messages.success(request, "Candidate shortlisted successfully.")

    return redirect('employer_dashboard')


@login_required
def reject_candidate(request, applicant_id):

    if request.method != "POST":
        return redirect('employer_dashboard')

    application = get_object_or_404(Application, id=applicant_id)

    if not request.user.is_employer or application.job.employer.user != request.user:
        messages.error(request, "Unauthorized access.")
        return redirect('employer_dashboard')

    # Update status
    application.status = "Rejected"
    application.save()

    messages.success(request, "Candidate rejected successfully.")

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


@login_required
def view_all_jobs(request):
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'view_all_jobs.html', {'jobs': jobs})

@login_required
def delete_job(request, job_id):
    if not request.user.is_employer:
        return redirect('homepage')

    job = get_object_or_404(Job, id=job_id)

    # ensure employer owns this job
    if job.employer.user != request.user:
        return redirect('employer_dashboard')

    job.delete()   # permanently delete job

    messages.success(request, "Job removed successfully.")
    return redirect('employer_dashboard')

