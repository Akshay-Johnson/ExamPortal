from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class Profile(models.Model):
    USER_TYPES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='student')  
    phone = models.CharField(max_length=15, null=True, blank=True)  
    bio = models.TextField(null=True, blank=True)  
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True) 
    qualification = models.CharField(max_length=255, blank=True, null=True)  
    experience = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return f'{self.user.username} ({self.get_user_type_display()}) Profile'

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    phone = models.CharField(max_length=15, null=True, blank=True)  

    def __str__(self):
        return f'Teacher: {self.user.username}'

    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    phone = models.CharField(max_length=15, null=True, blank=True)  

    def __str__(self):
        return f'Student: {self.user.username}'

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

class Exam(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    subject = models.CharField(max_length=255)
    time_limit = models.IntegerField()
    duration = models.IntegerField(null=True, blank=True)
    rules = models.TextField(default="No specific rules.")
    date = models.DateField()
    expiry_date = models.DateField(default=now)  
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ Track modifications
    passing_grade = models.IntegerField(default=50)

    approval_status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending'
    )

    def approve(self):
        """Approve the exam."""
        self.approval_status = 'approved'
        self.save()

    def reject(self):
        """Reject the exam."""
        self.approval_status = 'rejected'
        self.save()

    def save(self, *args, **kwargs):
        """Ensure expiry_date is set and passing_grade is valid."""
        if not self.expiry_date:
            self.expiry_date = self.date  
        if self.passing_grade < 0 or self.passing_grade > 100:
            raise ValueError("Passing grade must be between 0 and 100.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject} ({self.approval_status})"

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions") 
    text = models.CharField(max_length=500)

    # Option A
    option_a_text = models.CharField(max_length=200, blank=True, null=True)
    option_a_image = models.ImageField(upload_to="question_images/", blank=True, null=True)

    # Option B
    option_b_text = models.CharField(max_length=200, blank=True, null=True)
    option_b_image = models.ImageField(upload_to="question_images/", blank=True, null=True)

    # Option C
    option_c_text = models.CharField(max_length=200, blank=True, null=True)
    option_c_image = models.ImageField(upload_to="question_images/", blank=True, null=True)

    # Option D
    option_d_text = models.CharField(max_length=200, blank=True, null=True)
    option_d_image = models.ImageField(upload_to="question_images/", blank=True, null=True)

    # Answer and Marks
    correct_answer = models.CharField(
        max_length=1, 
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    )
    is_graded = models.BooleanField(default=False)
    marks = models.PositiveIntegerField(default=1)  # Removed syntax issue

    def __str__(self):
        return self.text



class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text
    
class MalpracticeRecord(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    issue = models.CharField(max_length=255)  # e.g., "Face not detected", "Tab switched"
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.issue}"


class ExamResult(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_results")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    score = models.FloatField(default=0.0)  

    # Timestamps for tracking exam progress
    attempted_at = models.DateTimeField(null=True, blank=True)  
    submitted_at = models.DateTimeField(null=True, blank=True)  
    video_url = models.FileField(upload_to="recordings/", null=True, blank=True)
    malpractice_warnings = models.IntegerField(default=0)

    class Meta:
        unique_together = ('student', 'exam')  

    def save(self, *args, **kwargs):
        """ Ensure submitted_at is updated when the exam is submitted """
        if not self.attempted_at:
            self.attempted_at = now()

        if not self.submitted_at:
            student_exam = StudentExam.objects.filter(student=self.student, exam=self.exam).first()
            if student_exam and student_exam.submitted_at:
                self.submitted_at = student_exam.submitted_at  # Sync with StudentExam
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} - {self.exam.subject} - {self.score}"

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="student_answers")
    selected_option = models.CharField(max_length=200)  
    is_correct = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.student.username} - {self.question.text} - {self.selected_option}"
    

class StudentExam(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_exams")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_exams")

    attempted_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'exam')  # Prevents duplicates

    def save(self, *args, **kwargs):
        """ Ensure timestamps are set correctly when saving """
        if not self.pk:  # New record
            if not self.attempted_at:
                self.attempted_at = now()
        
        if self.submitted_at and not self.attempted_at:
            self.attempted_at = self.submitted_at  # Ensures attempted_at is never blank

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} - {self.exam.subject}"

class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="submissions")  
    selected_option = models.CharField(max_length=1, blank=False, null=False)  
    score = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now=True)  # Updates in real-time

    def save(self, *args, **kwargs):
        # Auto-grade the submission
        if self.selected_option.lower() == self.question.correct_answer.lower():
            self.score = self.question.marks  # Full marks for correct answer
        else:
            self.score = 0  # No marks for incorrect answer

        super().save(*args, **kwargs)

        # Update StudentExam's submitted_at field when the last question is submitted
        student_exam, _ = StudentExam.objects.get_or_create(student=self.student, exam=self.exam)
        student_exam.submitted_at = now()
        student_exam.save(update_fields=['submitted_at'])

        # Update ExamResult's submitted_at field
        exam_result, _ = ExamResult.objects.get_or_create(student=self.student, exam=self.exam)
        exam_result.submitted_at = student_exam.submitted_at
        exam_result.save(update_fields=['submitted_at'])

    def __str__(self):
        return f"{self.student.username} - {self.question.text} - {self.selected_option} ({self.score} marks)"
    
class ExamMalpractice(models.Model):
    exam_id = models.IntegerField()
    issue = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Exam {self.exam_id}: {self.issue} ({self.timestamp})"
    

from django.contrib.auth.models import User

# ✅ Proxy Model for Students
class StudentUser(User):
    class Meta:
        proxy = True

# ✅ Proxy Model for Teachers
class TeacherUser(User):
    class Meta:
        proxy = True

# ✅ Proxy Model for Admin Users
class AdminUser(User):
    class Meta:
        proxy = True  # This creates a separate Admin table in the admin panel