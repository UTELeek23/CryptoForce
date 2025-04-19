from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Rank, Problem, Contest, Submission, EloHistory, UserContestParticipation

# Tùy chỉnh giao diện admin cho User
class CustomUserAdmin(UserAdmin):
    # Giữ lại các trường mặc định từ UserAdmin
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('bio', 'avatar', 'elo', 'country')}),
    )
    # Thêm các trường tùy chỉnh vào danh sách hiển thị
    list_display = ('username', 'email', 'first_name', 'last_name', 'elo', 'country', 'is_staff', 'is_active')
    list_filter = UserAdmin.list_filter + ('country',)
    search_fields = UserAdmin.search_fields + ('country',)
    readonly_fields = ('last_active',)

# Đăng ký User với CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

# Đăng ký Rank với giao diện admin
@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_elo', 'max_elo', 'color_code')
    search_fields = ('name',)
    ordering = ('min_elo',)

# Đăng ký Problem với giao diện admin
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'difficulty_level', 'points', 'is_active', 'created_at')
    list_filter = ('category', 'difficulty_level', 'is_active')
    search_fields = ('title', 'description', 'category')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'points', 'is_active')
        }),
        ('Difficulty Settings', {
            'fields': ('difficulty', 'difficulty_level')
        }),
        ('Solution', {
            'fields': ('flag', 'solution'),
            'classes': ('collapse',),
            'description': 'The flag and solution are sensitive information. Keep them secure!'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

# Đăng ký Contest với giao diện admin
@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('title', 'contest_type', 'status', 'start_time', 'end_time', 'is_rated')
    list_filter = ('contest_type', 'status', 'is_rated')
    search_fields = ('title', 'description')
    filter_horizontal = ('problems',)
    date_hierarchy = 'start_time'
    actions = ['update_contest_status']
    
    def update_contest_status(self, request, queryset):
        for contest in queryset:
            contest.update_status()
        self.message_user(request, f"{queryset.count()} contests had their status updated.")
    update_contest_status.short_description = "Update status of selected contests"

# Đăng ký Submission với giao diện admin
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'is_correct', 'submission_time', 'elo_change')
    list_filter = ('is_correct', 'submission_time')
    search_fields = ('user__username', 'problem__title')
    date_hierarchy = 'submission_time'
    readonly_fields = ('submission_time', 'elo_change')

# Đăng ký EloHistory với giao diện admin
@admin.register(EloHistory)
class EloHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'elo_before', 'elo_after', 'change', 'change_type')
    list_filter = ('change_type', 'timestamp')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)

# Đăng ký UserContestParticipation với giao diện admin
@admin.register(UserContestParticipation)
class UserContestParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'register_time', 'starting_elo', 'ending_elo', 'total_points')
    list_filter = ('register_time',)
    search_fields = ('user__username', 'contest__title')
    date_hierarchy = 'register_time'
    readonly_fields = ('register_time',)
    actions = ['calculate_performance']
    
    def calculate_performance(self, request, queryset):
        for participation in queryset:
            participation.calculate_contest_performance()
        self.message_user(request, f"Calculated performance for {queryset.count()} participations.")
    calculate_performance.short_description = "Calculate contest performance for selected participations"
