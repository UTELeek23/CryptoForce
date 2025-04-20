from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum, Case, When, IntegerField, F
from django.http import HttpResponseForbidden, JsonResponse
from .forms import LoginForm, RegisterForm, EditProfileForm, ProblemForm, HintForm, SubmissionForm
from .models import User, Contest, Problem, Rank, Submission, EloHistory, Hint

def home_view(request):
    """View for the home page"""
    # Get upcoming contests
    upcoming_contests = Contest.objects.filter(status='UPCOMING').order_by('start_time')[:5]
    
    # Get top users by ELO
    top_users = User.objects.order_by('-elo')[:10]
    
    # Get recent problems
    recent_problems = Problem.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    context = {
        'upcoming_contests': upcoming_contests,
        'top_users': top_users,
        'recent_problems': recent_problems,
    }
    
    return render(request, 'home/index.html', context)

def login_view(request):
    """View for user login"""
    if request.user.is_authenticated:
        return redirect(reverse('crypto_force_app:home'))
        
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect to the page the user was trying to access, or home
                next_page = request.GET.get('next', reverse('crypto_force_app:home'))
                return redirect(next_page)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
        
    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    """View for user registration"""
    if request.user.is_authenticated:
        return redirect(reverse('crypto_force_app:home'))
        
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Log the user in after registration
            login(request, user)
            messages.success(request, f"Welcome to CryptoForce, {user.username}! Your account has been created successfully.")
            return redirect(reverse('crypto_force_app:home'))
    else:
        form = RegisterForm()
        
    return render(request, 'accounts/register.html', {'form': form})

def logout_view(request):
    """View for user logout"""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect(reverse('crypto_force_app:login'))

@login_required
def profile_view(request, username=None):
    """View for user profile"""
    # If no username is provided, show the current user's profile
    if username is None:
        user = request.user
    else:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect(reverse('crypto_force_app:home'))
    
    # Get user's ELO history for chart
    elo_chart_data = user.get_elo_chart_data()
    
    # Get user's recent submissions
    recent_submissions = user.submissions.order_by('-submission_time')[:10]
    
    # Get user's participating contests
    user_contests = user.contests.all().order_by('-start_time')
    
    # Get solved problems with solving date
    solved_problems_data = []
    for problem in user.solved_problems.all()[:5]:
        # Get the first correct submission for this problem
        submission = Submission.objects.filter(
            user=user,
            problem=problem,
            is_correct=True
        ).order_by('submission_time').first()
        
        solved_date = submission.submission_time if submission else None
        
        solved_problems_data.append({
            'problem': problem,
            'solved_date': solved_date
        })
    
    # Get contest participations with ELO changes
    contest_participations = []
    for contest in user_contests[:5]:
        try:
            participation = contest.usercontestparticipation_set.get(user=user)
            elo_change = None
            if participation.ending_elo is not None and participation.starting_elo is not None:
                elo_change = participation.ending_elo - participation.starting_elo
            
            contest_participations.append({
                'contest': contest,
                'participation': participation,
                'elo_change': elo_change
            })
        except:
            pass
    
    context = {
        'profile_user': user,
        'elo_chart_data': elo_chart_data,
        'recent_submissions': recent_submissions,
        'user_contests': user_contests,
        'solved_problems_data': solved_problems_data,
        'contest_participations': contest_participations,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile_view(request):
    """View for editing user profile"""
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # Check if current password is required
            if form.has_changed():
                current_password = form.cleaned_data.get('current_password')
                if current_password:
                    # Password provided and form is valid, save changes
                    form.save()
                    messages.success(request, "Your profile has been updated successfully.")
                    return redirect(reverse('crypto_force_app:profile'))
                else:
                    # Password required but not provided
                    messages.error(request, "Please enter your current password to save changes.")
            else:
                # No changes were made
                messages.info(request, "No changes were made to your profile.")
                return redirect(reverse('crypto_force_app:profile'))
    else:
        form = EditProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

@login_required
def change_password_view(request):
    """View for changing user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Update the session to prevent the user from being logged out
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect(reverse('crypto_force_app:profile'))
    else:
        form = PasswordChangeForm(user=request.user)
    
    # Add Bootstrap classes to form inputs
    for field_name, field in form.fields.items():
        field.widget.attrs['class'] = 'form-control'
        field.widget.attrs['placeholder'] = field.label
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def problem_list_view(request):
    """View for listing all problems with filtering options"""
    # Get all problems
    problems = Problem.objects.filter(is_active=True)
    
    # Get all unique categories
    all_categories = Problem.objects.values_list('category', flat=True).distinct()
    
    # Get filter parameters from GET request
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    difficulty_filter = request.GET.get('difficulty', '')
    solved_filter = request.GET.get('solved', '')
    
    # Apply filters
    if search_query:
        problems = problems.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    if category_filter:
        problems = problems.filter(category=category_filter)
    
    if difficulty_filter:
        problems = problems.filter(difficulty_level=difficulty_filter)
    
    if solved_filter and request.user.is_authenticated:
        if solved_filter == 'true':
            problems = problems.filter(id__in=request.user.solved_problems.all())
        elif solved_filter == 'false':
            problems = problems.exclude(id__in=request.user.solved_problems.all())
    
    # Get total problems count
    total_problems = Problem.objects.filter(is_active=True).count()
    
    # Calculate unsolved count for authenticated users
    unsolved_count = 0
    user_progress_percentage = 0
    user_rank = None
    user_activity_streak = 0
    
    if request.user.is_authenticated:
        unsolved_count = total_problems - request.user.solved_problems.count()
        if total_problems > 0:
            user_progress_percentage = (request.user.solved_problems.count() / total_problems) * 100
        user_rank = request.user.rank.name if request.user.rank else "Unranked"
        # In a real app, you would calculate the streak here
    
    # Paginate problems
    paginator = Paginator(problems, 12)  # Show 12 problems per page
    page_number = request.GET.get('page', 1)
    problems = paginator.get_page(page_number)
    
    context = {
        'problems': problems,
        'all_categories': all_categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'difficulty_filter': difficulty_filter,
        'solved_filter': solved_filter,
        'total_problems': total_problems,
        'unsolved_count': unsolved_count,
        'user_progress_percentage': user_progress_percentage,
        'user_rank': user_rank,
        'user_activity_streak': user_activity_streak,
    }
    
    return render(request, 'problems/problem_list.html', context)

@login_required
def problem_detail_view(request, problem_id):
    """View for displaying problem details and accepting submissions"""
    problem = get_object_or_404(Problem, id=problem_id, is_active=True)
    
    # Get user submissions for this problem
    user_submissions = None
    if request.user.is_authenticated:
        user_submissions = Submission.objects.filter(
            user=request.user, 
            problem=problem
        ).order_by('-submission_time')
    
    # Get first solvers (first 5 users who solved the problem)
    first_solvers = Submission.objects.filter(
        problem=problem,
        is_correct=True
    ).order_by('submission_time')[:5]
    
    # Calculate solve percentage
    total_attempts = Submission.objects.filter(problem=problem).count()
    correct_attempts = Submission.objects.filter(problem=problem, is_correct=True).count()
    solve_percentage = 0
    if total_attempts > 0:
        solve_percentage = (correct_attempts / total_attempts) * 100
    
    # Check if problem is part of an ongoing contest
    contest = None
    active_contests = Contest.objects.filter(
        problems=problem,
        status='ONGOING'
    ).first()
    
    # Get hints for the problem
    hints = Hint.objects.filter(problem=problem)
    
    # Add info about which hints are unlocked by the current user
    processed_hints = []
    for hint in hints:
        unlocked = request.user in hint.unlocked_by.all()
        processed_hints.append({
            'id': hint.id,
            'content': hint.content,
            'cost': hint.cost,
            'is_unlocked': unlocked
        })
    
    # Create submission form
    form = SubmissionForm()
    
    context = {
        'problem': problem,
        'user_submissions': user_submissions,
        'first_solvers': first_solvers,
        'solve_percentage': solve_percentage,
        'contest': contest,
        'hints': processed_hints,
        'form': form,
    }
    
    return render(request, 'problems/problem_detail.html', context)

@login_required
def submit_solution_view(request, problem_id):
    """View for handling problem solution submissions"""
    problem = get_object_or_404(Problem, id=problem_id, is_active=True)
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            submitted_flag = form.cleaned_data['submitted_flag']
            
            # Create submission
            submission = Submission(
                user=request.user,
                problem=problem,
                submitted_flag=submitted_flag
            )
            
            # Save will handle flag verification and ELO updates
            submission.save()
            
            if submission.is_correct:
                if submission.elo_change > 0:  # First time solving
                    messages.success(
                        request, 
                        f"Correct flag! You earned {problem.points} points and {submission.elo_change} ELO."
                    )
                else:  # Already solved before
                    messages.info(
                        request,
                        "Correct flag! You already solved this problem before."
                    )
            else:
                messages.error(request, "Incorrect flag. Try again!")
            
            return redirect('crypto_force_app:problem_detail', problem_id=problem.id)
    
    return redirect('crypto_force_app:problem_detail', problem_id=problem.id)

@login_required
def unlock_hint_view(request, hint_id):
    """View for unlocking problem hints"""
    hint = get_object_or_404(Hint, id=hint_id)
    problem = hint.problem
    
    # Check if hint is already unlocked
    if request.user in hint.unlocked_by.all():
        messages.info(request, "You've already unlocked this hint.")
        return redirect('crypto_force_app:problem_detail', problem_id=problem.id)
    
    # In a real application, you'd check if the user has enough points and subtract them
    # For now, just unlock the hint
    hint.unlocked_by.add(request.user)
    messages.success(request, f"Hint unlocked! You spent {hint.cost} points.")
    
    return redirect('crypto_force_app:problem_detail', problem_id=problem.id)

@login_required
def create_problem_view(request):
    """View for creating a new problem (staff or problem setter only)"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES)
        if form.is_valid():
            problem = form.save()
            messages.success(request, f"Problem '{problem.title}' created successfully!")
            return redirect('crypto_force_app:problem_detail', problem_id=problem.id)
    else:
        form = ProblemForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'problems/create_problem.html', context)

@login_required
def edit_problem_view(request, problem_id):
    """View for editing an existing problem (staff or problem setter only)"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES, instance=problem)
        if form.is_valid():
            form.save()
            messages.success(request, f"Problem '{problem.title}' updated successfully!")
            return redirect('crypto_force_app:problem_detail', problem_id=problem.id)
    else:
        form = ProblemForm(instance=problem)
    
    context = {
        'form': form,
        'problem': problem,
        'action': 'Edit',
    }
    
    return render(request, 'problems/create_problem.html', context)

@login_required
def delete_problem_view(request, problem_id):
    """View for deleting a problem (staff or problem setter only)"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        problem_title = problem.title
        problem.delete()
        messages.success(request, f"Problem '{problem_title}' deleted successfully!")
        return redirect('crypto_force_app:problem_list')
    
    return redirect('crypto_force_app:problem_detail', problem_id=problem_id)

@login_required
def leaderboard_view(request):
    """View for displaying the leaderboard of users by ELO rating"""
    # Start with all users
    users_query = User.objects.order_by('-elo')
    
    # Exclude admin/staff users from leaderboard
    users_query = users_query.filter(is_staff=False)
    
    # Get filter parameters
    country_filter = request.GET.get('country', '')
    username_filter = request.GET.get('username', '')
    category_filter = request.GET.get('category', '')
    sort_by = request.GET.get('sort_by', 'ELO')
    time_range = request.GET.get('time_range', 'All Time')
    
    # Apply filters
    if country_filter:
        users_query = users_query.filter(country=country_filter)
    
    if username_filter:
        users_query = users_query.filter(username__icontains=username_filter)
    
    # Apply time range filter
    if time_range != 'All Time':
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if time_range == 'Today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # Filter submissions made today
            recent_submission_users = Submission.objects.filter(
                submission_time__gte=start_date
            ).values_list('user', flat=True).distinct()
            users_query = users_query.filter(id__in=recent_submission_users)
            
        elif time_range == 'This Week':
            start_date = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
            # Filter submissions made this week
            recent_submission_users = Submission.objects.filter(
                submission_time__gte=start_date
            ).values_list('user', flat=True).distinct()
            users_query = users_query.filter(id__in=recent_submission_users)
            
        elif time_range == 'This Month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Filter submissions made this month
            recent_submission_users = Submission.objects.filter(
                submission_time__gte=start_date
            ).values_list('user', flat=True).distinct()
            users_query = users_query.filter(id__in=recent_submission_users)
    
    # Apply sorting
    if sort_by == 'Problems Solved':
        # Annotate with solved problems count and sort
        users_query = users_query.annotate(solved_count=Count('solved_problems')).order_by('-solved_count', '-elo')
    elif sort_by == 'Points':
        # Sort by points (assuming points is sum of solved problem points)
        users_query = users_query.annotate(
            points=Sum(
                Case(
                    When(solved_problems__isnull=False, then='solved_problems__points'),
                    default=0,
                    output_field=IntegerField()
                )
            )
        ).order_by('-points', '-elo')
    else:  # Default sort by ELO
        users_query = users_query.order_by('-elo')
    
    # Get all unique problem categories
    categories = Problem.objects.values('id', 'category').distinct()
    
    # Add additional user information
    users_with_data = users_query.annotate(
        solved_count=Count('solved_problems', distinct=True),
        points=Sum(
            Case(
                When(solved_problems__isnull=False, then='solved_problems__points'),
                default=0,
                output_field=IntegerField()
            )
        )
    )
    
    # Paginate users
    paginator = Paginator(users_with_data, 20)  # Show 20 users per page
    page_number = request.GET.get('page', 1)
    users = paginator.get_page(page_number)
    
    # Get unique countries for filter dropdown
    countries = []
    for country_name in User.objects.values_list('country', flat=True).distinct():
        if country_name:  # Skip empty country names
            countries.append((country_name, country_name))
    
    context = {
        'users': users,  # Paginated users with additional data
        'categories': categories,
        'countries': countries,
        'country_filter': country_filter,
        'username': username_filter,
        'category': category_filter,
        'sort_by': sort_by,
        'time_range': time_range,
    }
    
    return render(request, 'problems/leaderboard.html', context)

@login_required
def admin_user_management(request):
    """View for admin to manage users (admin only)"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get all users, sorted by username
    users = User.objects.all().order_by('username')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    is_active_filter = request.GET.get('is_active', '')
    is_staff_filter = request.GET.get('is_staff', '')
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if is_active_filter:
        is_active = is_active_filter == 'true'
        users = users.filter(is_active=is_active)
        
    if is_staff_filter:
        is_staff = is_staff_filter == 'true'
        users = users.filter(is_staff=is_staff)
    
    # Paginate users
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page', 1)
    users = paginator.get_page(page_number)
    
    context = {
        'users': users,
        'search_query': search_query,
        'is_active_filter': is_active_filter,
        'is_staff_filter': is_staff_filter,
    }
    
    return render(request, 'admin/user_management.html', context)

@login_required
def admin_toggle_user_status(request, user_id):
    """View for admin to toggle user status (active/inactive)"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    user = get_object_or_404(User, id=user_id)
    
    # Don't allow admins to deactivate themselves
    if user == request.user:
        messages.error(request, "You cannot change your own status.")
        return redirect('crypto_force_app:admin_user_management')
    
    # Toggle user status
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' has been {status}.")
    
    return redirect('crypto_force_app:admin_user_management')

@login_required
def admin_toggle_user_staff(request, user_id):
    """View for admin to toggle user staff status"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    user = get_object_or_404(User, id=user_id)
    
    # Don't allow admins to remove their own staff status
    if user == request.user:
        messages.error(request, "You cannot change your own staff status.")
        return redirect('crypto_force_app:admin_user_management')
    
    # Toggle user staff status
    user.is_staff = not user.is_staff
    user.save()
    
    status = "granted staff privileges" if user.is_staff else "removed staff privileges from"
    messages.success(request, f"User '{user.username}' has been {status}.")
    
    return redirect('crypto_force_app:admin_user_management')

@login_required
def admin_toggle_problem_setter(request, user_id):
    """View for admin to toggle user problem setter status"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    user = get_object_or_404(User, id=user_id)
    
    # Toggle user problem setter status
    user.is_problem_setter = not user.is_problem_setter
    user.save()
    
    status = "granted problem setter privileges" if user.is_problem_setter else "removed problem setter privileges from"
    messages.success(request, f"User '{user.username}' has been {status}.")
    
    return redirect('crypto_force_app:admin_user_management')

@login_required
def admin_toggle_contest_manager(request, user_id):
    """View for admin to toggle user contest manager status"""
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    user = get_object_or_404(User, id=user_id)
    
    # Toggle user contest manager status
    user.is_contest_manager = not user.is_contest_manager
    user.save()
    
    status = "granted contest manager privileges" if user.is_contest_manager else "removed contest manager privileges from"
    messages.success(request, f"User '{user.username}' has been {status}.")
    
    return redirect('crypto_force_app:admin_user_management')

@login_required
def manage_hint_view(request, problem_id):
    """View for managing hints for a problem"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    problem = get_object_or_404(Problem, id=problem_id)
    
    if request.method == 'POST':
        form = HintForm(request.POST)
        if form.is_valid():
            hint = Hint.objects.create(
                problem=problem,
                content=form.cleaned_data['content'],
                cost=form.cleaned_data['cost']
            )
            return JsonResponse({
                'status': 'success', 
                'id': hint.id,
                'content': hint.content,
                'cost': hint.cost
            })
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    elif request.method == 'GET':
        hints = Hint.objects.filter(problem=problem)
        return JsonResponse({
            'status': 'success',
            'hints': list(hints.values('id', 'content', 'cost'))
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def update_hint_view(request, hint_id):
    """View for updating a hint"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    hint = get_object_or_404(Hint, id=hint_id)
    
    if request.method == 'POST':
        form = HintForm(request.POST)
        if form.is_valid():
            hint.content = form.cleaned_data['content']
            hint.cost = form.cleaned_data['cost']
            hint.save()
            return JsonResponse({
                'status': 'success', 
                'id': hint.id,
                'content': hint.content,
                'cost': hint.cost
            })
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def delete_hint_view(request, hint_id):
    """View for deleting a hint"""
    if not (request.user.is_staff or request.user.is_problem_setter):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    hint = get_object_or_404(Hint, id=hint_id)
    
    if request.method == 'POST':
        hint.delete()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
