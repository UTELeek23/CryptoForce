from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
import math

class Rank(models.Model):
    name = models.CharField(max_length=50)
    min_elo = models.IntegerField()
    max_elo = models.IntegerField()
    color_code = models.CharField(max_length=20, default='#000000')
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    """
    Mở rộng model User mặc định với các trường bổ sung cho hệ thống CTF
    """
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    elo = models.IntegerField(default=500)
    solved_problems = models.ManyToManyField('Problem', blank=True, related_name='solved_by')
    country = models.CharField(max_length=100, default='Global')
    last_active = models.DateTimeField(auto_now=True)  # Tự động cập nhật khi user được lưu
    
    # Thêm các trường phân quyền
    is_problem_setter = models.BooleanField(default=False, help_text="Cho phép người dùng tạo và quản lý bài tập")
    is_contest_manager = models.BooleanField(default=False, help_text="Cho phép người dùng tạo và quản lý cuộc thi")
    
    @property
    def rank(self):
        return Rank.objects.filter(min_elo__lte=self.elo, max_elo__gte=self.elo).first()
    
    def calculate_elo_change(self, problem_difficulty, solved):
        """
        Calculate ELO change when a user attempts a problem
        
        Args:
            problem_difficulty: The difficulty rating of the problem
            solved: Boolean indicating whether the problem was solved
        
        Returns:
            The ELO change (positive or negative)
        """
        # Expected score based on ELO difference
        # Using the logistic curve from the ELO rating system
        elo_diff = problem_difficulty - self.elo
        expected_score = 1 / (1 + math.pow(10, elo_diff / 400))
        
        # Actual score (1 if solved, 0 if not)
        actual_score = 1 if solved else 0
        
        # Base K-factor (how much ELO can change)
        # Lower K-factor for higher-rated users, higher for beginners
        if self.elo < 1200:
            k_factor = 40  # Beginners gain/lose more points
        elif self.elo < 2000:
            k_factor = 30  # Intermediate users
        elif self.elo < 2400:
            k_factor = 20  # Advanced users
        else:
            k_factor = 10  # Experts gain/lose fewer points
        
        # Calculate ELO change
        elo_change = k_factor * (actual_score - expected_score)
        return round(elo_change)
    
    def update_elo(self, problem, solved):
        """Update user's ELO based on problem submission"""
        elo_change = self.calculate_elo_change(problem.difficulty, solved)
        
        # Create ELO history entry before updating current ELO
        EloHistory.objects.create(
            user=self,
            elo_before=self.elo,
            elo_after=self.elo + elo_change,
            change=elo_change,
            change_type='PROBLEM_SUBMISSION',
            related_problem=problem
        )
        
        # Update current ELO
        self.elo += elo_change
        self.save()
        
        return elo_change
    
    def get_elo_history(self, limit=30):
        """Get recent ELO history for the user, limited to a certain number of entries"""
        return self.elo_history.order_by('-timestamp')[:limit]
    
    def get_elo_chart_data(self):
        """Get data for ELO chart in user profile"""
        history = self.elo_history.order_by('timestamp')
        return {
            'timestamps': [entry.timestamp.strftime('%Y-%m-%d %H:%M') for entry in history],
            'elo_values': [entry.elo_after for entry in history]
        }
    
    def __str__(self):
        return f"{self.username} (ELO: {self.elo})"

class EloHistory(models.Model):
    """Model to track historical ELO changes for users"""
    CHANGE_TYPES = (
        ('PROBLEM_SUBMISSION', 'Problem Submission'),
        ('CONTEST_PARTICIPATION', 'Contest Participation'),
        ('ADMIN_ADJUSTMENT', 'Admin Adjustment'),
        ('INITIAL', 'Initial ELO'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elo_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    elo_before = models.IntegerField()
    elo_after = models.IntegerField()
    change = models.IntegerField()  # Can be positive or negative
    change_type = models.CharField(max_length=50, choices=CHANGE_TYPES)
    related_problem = models.ForeignKey('Problem', on_delete=models.SET_NULL, null=True, blank=True, related_name='elo_changes')
    related_contest = models.ForeignKey('Contest', on_delete=models.SET_NULL, null=True, blank=True, related_name='elo_changes')
    description = models.CharField(max_length=255, blank=True, null=True)  # Optional description
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'ELO Histories'
    
    def __str__(self):
        if self.change >= 0:
            change_str = f"+{self.change}"
        else:
            change_str = str(self.change)
        
        return f"{self.user.username}'s ELO: {self.elo_before} → {self.elo_after} ({change_str})"

class Contest(models.Model):
    CONTEST_TYPES = (
        ('STANDARD', 'Standard Contest'),
        ('TEAM', 'Team Contest'),
        ('EDUCATIONAL', 'Educational Contest'),
    )
    
    CONTEST_STATUS = (
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('FINISHED', 'Finished'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    contest_type = models.CharField(max_length=20, choices=CONTEST_TYPES, default='STANDARD')
    status = models.CharField(max_length=20, choices=CONTEST_STATUS, default='UPCOMING')
    problems = models.ManyToManyField('Problem', related_name='contests')
    is_rated = models.BooleanField(default=True)
    participants = models.ManyToManyField(User, through='UserContestParticipation', related_name='contests')
    
    def update_status(self):
        now = datetime.now()
        if now < self.start_time:
            self.status = 'UPCOMING'
        elif now >= self.start_time and now <= self.end_time:
            self.status = 'ONGOING'
        else:
            self.status = 'FINISHED'
        self.save()
    
    def __str__(self):
        return self.title

class Problem(models.Model):
    DIFFICULTY_CHOICES = (
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
        ('EXPERT', 'Expert'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.IntegerField(default=1500)  # Base ELO rating for the problem
    difficulty_level = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='MEDIUM')
    points = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    solution = models.TextField(blank=True, null=True)  # Admin solution or writeup
    flag = models.CharField(max_length=255)  # The answer/flag for the problem
    category = models.CharField(max_length=100)  # e.g., Cryptography, Web Exploitation, etc.
    
    def get_solve_count(self):
        return self.submissions.filter(is_correct=True).count()
    
    def __str__(self):
        return self.title

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    submitted_flag = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    submission_time = models.DateTimeField(auto_now_add=True)
    contest = models.ForeignKey(Contest, on_delete=models.SET_NULL, null=True, blank=True, related_name='submissions')
    elo_change = models.IntegerField(default=0)  # ELO points gained/lost
    
    def save(self, *args, **kwargs):
        # Check if the submission is correct
        self.is_correct = (self.submitted_flag == self.problem.flag)
        
        # Only calculate ELO if this is a new submission
        is_new = self.pk is None
        
        super(Submission, self).save(*args, **kwargs)
        
        # Update user's ELO after saving if this is a new submission
        if is_new:
            # Only update ELO if the contest is rated or if it's outside a contest
            contest_is_rated = self.contest is None or (self.contest and self.contest.is_rated)
            if contest_is_rated:
                self.elo_change = self.user.update_elo(self.problem, self.is_correct)
                self.save()  # Save again to store the ELO change
                
                # Add problem to solved problems if correct
                if self.is_correct:
                    self.user.solved_problems.add(self.problem)
    
    def __str__(self):
        return f"{self.user.username}'s submission for {self.problem.title}"

class UserContestParticipation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    register_time = models.DateTimeField(auto_now_add=True)
    starting_elo = models.IntegerField(null=True, blank=True)  # ELO before contest
    ending_elo = models.IntegerField(null=True, blank=True)    # ELO after contest
    total_points = models.IntegerField(default=0)
    
    def calculate_contest_performance(self):
        """Calculate total points and update ELO after a contest ends"""
        if self.contest.status != 'FINISHED':
            return
        
        # Store starting ELO if not already set
        if self.starting_elo is None:
            self.starting_elo = self.user.elo
            
        # Calculate total points from submissions in this contest
        submissions = Submission.objects.filter(
            user=self.user,
            contest=self.contest,
            is_correct=True
        )
        
        total_points = sum(sub.problem.points for sub in submissions)
        self.total_points = total_points
        
        # Store ending ELO
        self.ending_elo = self.user.elo
        
        # Create ELO history entry for the entire contest
        if self.ending_elo != self.starting_elo:
            EloHistory.objects.create(
                user=self.user,
                elo_before=self.starting_elo,
                elo_after=self.ending_elo,
                change=self.ending_elo - self.starting_elo,
                change_type='CONTEST_PARTICIPATION',
                related_contest=self.contest,
                description=f"Participation in contest: {self.contest.title}"
            )
        
        self.save()
    
    class Meta:
        unique_together = ('user', 'contest')
        
    def __str__(self):
        return f"{self.user.username} in {self.contest.title}"