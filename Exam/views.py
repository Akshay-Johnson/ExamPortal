from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.utils.timezone import now, localtime, is_naive, make_aware
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse

import os
import logging

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

from .models import (
    Profile, Exam, ExamResult, StudentExam, StudentAnswer, 
    Question, Submission, Student , MalpracticeRecord
)
from .forms import (
    TeacherProfileEditForm, StudentProfileForm, ExamForm, QuestionForm
)

from django.forms import modelformset_factory, inlineformset_factory

###################################################################

def clear_popup_message(request):
    request.session.pop('popup_message', None)
    request.session.pop('popup_type', None)
    return JsonResponse({'status': 'cleared'})


def index(request):
    return render(request, 'index.html')

def studentregister(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        first_name = request.POST['first_name'].strip()
        last_name = request.POST['last_name'].strip()
        email = request.POST['email'].strip()
        phone = request.POST['phone'].strip()
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # 🔹 Check if passwords match
        if password != confirm_password:
            messages.error(request, "⚠️ Passwords do not match.")
            return redirect('studentregister')

        # 🔹 Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "⚠️ Invalid email format. Please enter a valid email.")
            return redirect('studentregister')

        # 🔹 Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username is already taken. Please choose another.")
            return redirect('studentregister')

        if User.objects.filter(email=email).exists():
            messages.error(request, "⚠️ Email is already registered. Please use a different one.")
            return redirect('studentregister')

        # 🔹 Check if phone number is already registered
        if Profile.objects.filter(phone=phone).exists():
            messages.error(request, "⚠️ This phone number is already in use.")
            return redirect('studentregister')

        # 🔹 Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, f"⚠️ Password is too weak: {', '.join(e)}")
            return redirect('studentregister')

        try:
            # ✅ Create the new user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.save()

            # ✅ Assign the user to the "Student" group
            student_group, _ = Group.objects.get_or_create(name='Student')
            user.groups.add(student_group)
            user.save()

            # ✅ Create the Profile with the phone number
            Profile.objects.create(user=user, phone=phone)

            messages.success(request, "✅ Registration successful! You can now log in.")
            return redirect('studentlogin')

        except Exception as e:
            messages.error(request, f"⚠️ An error occurred: {str(e)}")
            return redirect('studentregister')

    return render(request, 'studentregister.html')

def studentlogin(request):
    if request.method == 'POST':
        identifier = request.POST['identifier'].strip()  # Can be username or email
        password = request.POST['password'].strip()

        user = None

        try:
            # Check if the identifier is an email or a username
            if User.objects.filter(email=identifier).exists():
                user = User.objects.get(email=identifier)  # Get user by email
            elif User.objects.filter(username=identifier).exists():
                user = User.objects.get(username=identifier)  # Get user by username

            if user:
                # Authenticate using the actual username
                user = authenticate(request, username=user.username, password=password)

                if user is not None:
                    # Check if user belongs to the "Student" group
                    if user.groups.filter(name='Student').exists():
                        login(request, user)
                        request.session['popup_message'] = "✅ Login successful! Welcome to your dashboard."
                        request.session['popup_type'] = "success"
                        return redirect('studentdashboard')  # Redirect to student dashboard
                    else:
                        request.session['popup_message'] = "⚠️ You do not have student access."
                        request.session['popup_type'] = "error"
                        return redirect('studentlogin')
                else:
                    request.session['popup_message'] = "⚠️ Invalid credentials. Please try again."
                    request.session['popup_type'] = "error"
                    return redirect('studentlogin')
            else:
                request.session['popup_message'] = "⚠️ No account found with this username or email."
                request.session['popup_type'] = "error"
                return redirect('studentlogin')

        except User.DoesNotExist:
            request.session['popup_message'] = "⚠️ No account found with this username or email."
            request.session['popup_type'] = "error"
            return redirect('studentlogin')

    return render(request, 'studentlogin.html')


@login_required(login_url='studentlogin')
def studentdashboard(request):
    student = request.user  

    # ✅ Fetch only approved and non-expired exams, calculating total marks correctly
    exams = Exam.objects.filter(approval_status="approved", expiry_date__gte=now()) \
                        .annotate(total_marks=Sum('questions__marks'))  

    # ✅ Fetch only approved and expired exams
    expired_exams = Exam.objects.filter(approval_status="approved", expiry_date__lt=now()) \
                               .annotate(total_marks=Sum('questions__marks'))  

    return render(request, 'studentdashboard.html', {
        'exams': exams,
        'expired_exams': expired_exams
    })
   

def student_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None  # In case the profile doesn't exist yet

    return render(request, 'student_profile.html', {'profile': profile, 'user': request.user})


def edit_student_profile(request):
    return render(request, 'edit_student_profile.html')


def update_student_profile(request):
    user = request.user  # Get logged-in user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile, user=user)
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone', '').strip()  # Get phone input

        # Validate passwords
        if password:
            if len(password) < 8:
                messages.error(request, "⚠️ Password must be at least 8 characters long.")
                return redirect('edit_student_profile')

            if password != confirm_password:
                messages.error(request, "⚠️ Passwords do not match.")
                return redirect('edit_student_profile')

        # Phone number validation
        if phone_number:
            if not phone_number.isdigit():
                messages.error(request, "⚠️ Phone number must contain only digits.")
                return redirect('edit_student_profile')

            if len(phone_number) < 10 or len(phone_number) > 15:
                messages.error(request, "⚠️ Phone number must be between 10 and 15 digits long.")
                return redirect('edit_student_profile')

            if phone_number.startswith("0"):
                messages.error(request, "⚠️ Phone number cannot start with 0.")
                return redirect('edit_student_profile')

            # Check for duplicate phone number (excluding the current user)
            existing_profile = Profile.objects.filter(phone=phone_number).exclude(user=user).first()
            if existing_profile:
                messages.error(request, "⚠️ This phone number is already in use.")
                return redirect('edit_student_profile')

        if form.is_valid():
            profile = form.save(commit=False)
            profile.phone = phone_number  # Save valid phone number

            # Handle profile picture update
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            profile.save()

            # Update user details separately
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data['email']
            user.save()

            # Update password if provided
            if password:
                user.set_password(password)
                user.save()
                update_session_auth_hash(request, user)  # Keep user logged in after password change

            messages.success(request, "✅ Profile updated successfully!")
            return redirect('student_profile')
        else:
            messages.error(request, "⚠️ There was an error updating your profile. Please check the fields.")

    else:
        # Prefill form with user data
        form = StudentProfileForm(instance=profile, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': profile.phone
        }, user=user)

    return render(request, 'edit_student_profile.html', {'form': form})

def exam_completed(request):
    return render(request, 'exam_completed.html')

#studentlogout
def user_logout(request):
    logout(request) 
    return redirect('index')  

def teacherregister(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Check if username is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken. Please choose a different username.")
            return redirect('teacherregister')

        # Check if email is already in use
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered. Please use a different email.")
            return redirect('teacherregister')

        # Validate phone number: must be 10 digits and not start with 0
        if not re.fullmatch(r'^[1-9]\d{9}$', phone):
            messages.error(request, "Phone number must be 10 digits and cannot start with 0.")
            return redirect('teacherregister')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please try again.")
            return redirect('teacherregister')

        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, f"Password error: {' '.join(e.messages)}")
            return redirect('teacherregister')

        try:
            # Create the user
            user = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            user.is_active = False  # Mark user as inactive until admin approval
            user.save()

            # Create or update the profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.save()

            # Assign the user to the "Teacher" group
            teacher_group, created = Group.objects.get_or_create(name='Teacher')
            user.groups.add(teacher_group)

            messages.success(request, "Your registration request has been sent for approval. Please wait for admin approval.")
            return redirect('teacherapproval')

        except Exception as e:
            messages.error(request, f"Error occurred: {str(e)}")
            return redirect('teacherregister')
    
    return render(request, 'teacherregister.html')

def teacherlogin(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '').strip()

        if not username_or_email or not password:
            request.session['popup_message'] = "⚠️ Please enter both email/username and password."
            request.session['popup_type'] = "error"
            return redirect('teacherlogin')

        user = None
        if User.objects.filter(email=username_or_email).exists():
            try:
                user = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user.username, password=password)
            except User.DoesNotExist:
                user = None  # Handle the case where the user is not found
        else:
            user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                request.session['popup_message'] = "✅ Login successful! Welcome to your dashboard."
                request.session['popup_type'] = "success"
                return redirect('teacherdashboard')
            else:
                request.session['popup_message'] = "⚠️ Your account is inactive. Please wait for admin approval."
                request.session['popup_type'] = "error"
                return redirect('teacherlogin')
        else:
            request.session['popup_message'] = "⚠️ Invalid login credentials. Please try again."
            request.session['popup_type'] = "error"
            return redirect('teacherlogin')

    return render(request, 'teacherlogin.html')
    # Retrieve and clear popup messages
    error_message = request.session.pop('error_message', None)
    success_message = request.session.pop('success_message', None)
    request.session.pop('popup_message', None)
    request.session.pop('popup_type', None)

    return render(request, 'teacherlogin.html', {
        'error_message': error_message,
        'success_message': success_message
    })


def teacherdashboard(request):
    # Fetch exams created by the logged-in teacher
    exams = Exam.objects.filter(created_by=request.user).prefetch_related('results__student')

    total_exams = exams.count()
    last_exam = exams.order_by('-created_at').first()

    # Count pending submissions (assuming score=0 means not graded yet)
    pending_submissions = ExamResult.objects.filter(exam__in=exams, score=0).count()

    # ✅ Fetch distinct students who have taken at least one exam
    total_students = User.objects.filter(groups__name='Student').count()
    total_students_attended = ExamResult.objects.filter(exam__in=exams).values_list('student', flat=True).distinct().count()

    # Debugging log to check the total student count
    print("✅ DEBUG: Total Students:", total_students)

    context = {
        'exams': exams,
        'total_exams': total_exams,
        'pending_submissions': pending_submissions,
        'total_students': total_students,  # Ensure this is passed to the template
        'total_students_attended': total_students_attended,
        'last_exam': last_exam,
    }

    return render(request, 'teacherdashboard.html', context)




def teacher_profile(request):
    # Get the currently logged-in user
    teacher = request.user
    
    # You can also fetch related details (e.g., teacher profile data from a custom model)
    return render(request, 'teacher_profile.html', {'teacher': teacher})


import re

def edit_teacher_profile(request):
    teacher = request.user
    profile, created = Profile.objects.get_or_create(user=teacher)  # Ensure profile exists

    if request.method == 'POST':
        form = TeacherProfileEditForm(request.POST, request.FILES, instance=teacher)

        # Retrieve additional fields from the form
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone')
        qualification = request.POST.get('qualification')
        experience = request.POST.get('experience')

        # Validate phone number format
        if phone and not re.match(r'^\+?\d{10,15}$', phone):
            messages.error(request, "⚠️ Enter a valid phone number (e.g., +1234567890 or 0123456789).")
            return redirect('edit_teacher_profile')

        # Validate password conditions
        if new_password:
            if len(new_password) < 8:
                messages.error(request, "⚠️ Password must be at least 8 characters long.")
                return redirect('edit_teacher_profile')

            if new_password != confirm_password:
                messages.error(request, "⚠️ Passwords do not match.")
                return redirect('edit_teacher_profile')

        if form.is_valid():
            # Update password if provided
            if new_password:
                teacher.set_password(new_password)
                update_session_auth_hash(request, teacher)  # Keep user logged in

            # Update profile fields
            profile.phone = phone
            profile.qualification = qualification
            profile.experience = experience

            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            # Save changes
            profile.save()
            form.save()

            messages.success(request, "✅ Profile updated successfully!")
            return redirect('teacher_profile')  # Redirect to profile page after update
        else:
            # Capture form errors and display as popups
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = TeacherProfileEditForm(instance=teacher)

    return render(request, 'edit_teacher_profile.html', {'form': form, 'profile': profile})


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ExamForm
from .models import Question
import logging

# Set up logging for debugging
logger = logging.getLogger(__name__)

@login_required
def create_exam(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        
        if form.is_valid():
            try:
                # Save exam instance
                exam = form.save(commit=False)
                exam.created_by = request.user  # Assign teacher
                exam.approval_status = "pending"  # Mark exam as pending approval
                
                # Handle time limit
                selected_time_limit = request.POST.get("time_limit")
                custom_time = request.POST.get("custom_time_limit")
                
                if selected_time_limit == "custom":
                    if custom_time and custom_time.isdigit():
                        exam.time_limit = int(custom_time)
                    else:
                        messages.error(request, "Please enter a valid custom time limit.")
                        return render(request, "create_exam.html", {"form": form})
                else:
                    try:
                        exam.time_limit = int(selected_time_limit)
                    except ValueError:
                        messages.error(request, "Invalid time limit. Please try again.")
                        return render(request, "create_exam.html", {"form": form})
                
                exam.save()  # Save exam to DB

                # ✅ Save questions dynamically
                question_count = 1
                while f"question_{question_count}" in request.POST:
                    question_text = request.POST.get(f"question_{question_count}")
                    correct_answer = request.POST.get(f"correct_answer_{question_count}")
                    marks = request.POST.get(f"marks_{question_count}")

                    # Options (Either text or image)
                    options = {}
                    for opt in ['a', 'b', 'c', 'd']:
                        text = request.POST.get(f"option_{question_count}_{opt}")
                        image = request.FILES.get(f"option_{question_count}_{opt}_image")
                        options[opt] = (text, image)

                    # Validation: Ensure either text or image is provided for each option
                    valid = True
                    for opt, (text, image) in options.items():
                        if not text and not image:
                            messages.error(request, f"Either text or image must be provided for Option {opt.upper()} in Question {question_count}.")
                            valid = False
                        elif text and image:
                            messages.error(request, f"Cannot have both text and image for Option {opt.upper()} in Question {question_count}.")
                            valid = False

                    if valid and all([question_text, correct_answer, marks]):
                        Question.objects.create(
                            exam=exam,
                            text=question_text,
                            correct_answer=correct_answer,
                            marks=int(marks),
                            option_a_text=options['a'][0], option_a_image=options['a'][1],
                            option_b_text=options['b'][0], option_b_image=options['b'][1],
                            option_c_text=options['c'][0], option_c_image=options['c'][1],
                            option_d_text=options['d'][0], option_d_image=options['d'][1],
                        )

                    question_count += 1

                messages.success(request, "Exam created successfully! Waiting for admin approval.")
                return redirect("view_created_exams")

            except Exception as e:
                logger.error("Error creating exam: %s", str(e))
                messages.error(request, "An error occurred while creating the exam. Please try again.")
        
        else:
            logger.warning("Form errors: %s", form.errors)
            messages.error(request, "Please correct the errors in the form.")
    
    else:
        form = ExamForm()

    return render(request, "create_exam.html", {"form": form})


@login_required
def update_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Inline formset for questions (allows deletion)
    QuestionFormSet = inlineformset_factory(
        Exam, Question, form=QuestionForm, extra=0, can_delete=True
    )

    if request.method == "POST":
        exam_form = ExamForm(request.POST, instance=exam)
        question_formset = QuestionFormSet(request.POST, request.FILES, instance=exam, prefix="question_set")

        if exam_form.is_valid() and question_formset.is_valid():
            # ✅ Mark exam as pending approval after update
            exam = exam_form.save(commit=False)
            exam.approval_status = "pending"
            exam.save()

            # ✅ Save the updated questions
            questions = question_formset.save(commit=False)
            for question in questions:
                question.exam = exam  # Ensure question is linked to exam

                # ✅ Validate that either text or image is provided for each option
                for opt in ["option_a", "option_b", "option_c", "option_d"]:
                    text_field = f"{opt}_text"
                    image_field = f"{opt}_image"

                    text = getattr(question, text_field)
                    image = getattr(question, image_field)

                    if text and image:
                        messages.error(request, f"Error: Option {opt.upper()} cannot have both text and an image.")
                        return render(request, "update_exam.html", {
                            "exam_form": exam_form,
                            "question_formset": question_formset,
                            "exam": exam
                        })

                    if not text and not image:
                        messages.error(request, f"Error: Option {opt.upper()} must have either text or an image.")
                        return render(request, "update_exam.html", {
                            "exam_form": exam_form,
                            "question_formset": question_formset,
                            "exam": exam
                        })

                question.save()

            # ✅ Handle deleted questions
            for form in question_formset.deleted_forms:
                if form.instance.pk:  # Ensure the question exists in the database before deleting
                    form.instance.delete()

            messages.success(request, "Exam updated successfully! Waiting for admin approval.")
            return redirect("view_created_exams")

        messages.error(request, "Please correct the errors below.")

    else:
        exam_form = ExamForm(instance=exam)
        question_formset = QuestionFormSet(instance=exam, prefix="question_set")

    return render(request, "update_exam.html", {
        "exam_form": exam_form,
        "question_formset": question_formset,
        "exam": exam
    })



def edit_exam(request, exam_id):
    # Fetch the exam to be edited
    exam = get_object_or_404(Exam, id=exam_id)

    # If the request is a POST request, handle form submission
    if request.method == 'POST':
        exam_form = ExamForm(request.POST, instance=exam)
        question_forms = [QuestionForm(request.POST, instance=q) for q in exam.questions.all()]

        # If the form is valid, save it and redirect to the exam list page
        if exam_form.is_valid() and all(form.is_valid() for form in question_forms):
            exam_form.save()
            for form in question_forms:
                form.save()
            return redirect('view_created_exams')  # Redirect to the created exams page
    else:
        # If GET request, show the form with existing exam details
        exam_form = ExamForm(instance=exam)
        question_forms = [QuestionForm(instance=q) for q in exam.questions.all()]

    return render(request, 'edit_exam.html', {
        'exam_form': exam_form,
        'question_forms': question_forms,
        'exam': exam
    })


def delete_exam(request, exam_id):
    print(f"Delete Exam called for exam ID: {exam_id}")  # Debugging
    if request.method == "POST":
        exam = get_object_or_404(Exam, id=exam_id)
        print(f"Exam found: {exam.subject}")  # Debugging

        if request.user == exam.created_by:
            exam.delete()
            print("Exam deleted successfully!")  # Debugging
            return redirect('view_created_exams')
        else:
            print("Unauthorized deletion attempt!")  # Debugging
            return HttpResponseForbidden("You are not allowed to delete this exam.")
    
    print("Invalid request method (not POST)")  # Debugging
    return redirect('view_created_exams')

@login_required
def remove_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.user != exam.created_by:
        return HttpResponseForbidden("You are not allowed to remove this exam.")
    
    return render(request, "remove_exam.html", {"exam": exam})

@login_required
def confirm_remove_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.user == exam.created_by:
        exam.delete()
        return redirect("view_created_exams")
    return HttpResponseForbidden("You are not allowed to remove this exam.")

@login_required
def view_created_exams(request):
    exams = Exam.objects.filter(created_by=request.user).prefetch_related("questions")
    return render(request, "view_created_exams.html", {"exams": exams})


def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student = request.user

    has_attempted = ExamResult.objects.filter(exam=exam, student=student).exists()

    # Ensure only one StudentExam entry per student-exam
    student_exam, created = StudentExam.objects.get_or_create(student=student, exam=exam)

    if created or not student_exam.attempted_at:
        student_exam.attempted_at = now()
        student_exam.save()

    return render(request, 'start_exam.html', {'exam': exam, 'has_attempted': has_attempted})


import random
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student = request.user

    # If the exam is already completed, show the exam completed page
    if ExamResult.objects.filter(student=student, exam=exam).exists():
        return render(request, 'exam_completed.html', {'exam': exam})

    # Get all questions and shuffle them
    questions = list(exam.questions.all())
    random.shuffle(questions)

    if request.method == "POST":
        total_score = 0

        for question in exam.questions.all():  # Use original order for correctness matching
            selected_option = request.POST.get(f'question_{question.id}', None)
            if selected_option:
                is_correct = selected_option == question.correct_answer
                score = question.marks if is_correct else 0

                # Store student's answer
                Submission.objects.create(
                    student=student,
                    exam=exam,
                    question=question,
                    selected_option=selected_option,
                    score=score
                )
                total_score += score

        # Mark exam as attempted only after submission
        ExamResult.objects.create(student=student, exam=exam, score=total_score)

        return redirect('my_results')

    return render(request, 'take_exam.html', {'exam': exam, 'questions': questions})


from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.timezone import now
from .models import Exam, StudentExam, ExamResult, Submission

def submit_exam(request, exam_id):
    if request.method == "POST":
        exam = get_object_or_404(Exam, id=exam_id)
        student = request.user

        # Prevent duplicate submissions
        if StudentExam.objects.filter(student=student, exam=exam, submitted_at__isnull=False).exists():
            return JsonResponse({"status": "error", "message": "You have already submitted this exam."})

        total_score = 0
        answered = False  

        for question in exam.questions.all():
            selected_option = request.POST.get(f"question_{question.id}")

            if selected_option:
                answered = True
                is_correct = (selected_option == question.correct_answer)
                score = question.marks if is_correct else 0
            else:
                score = 0  

            Submission.objects.create(
                student=student,
                exam=exam,
                question=question,
                selected_option=selected_option if selected_option else "N/A",
                score=score
            )
            total_score += score

        if not answered:
            messages.error(request, "You didn't answer any questions.")
            return redirect('available_exam')

        # Count malpractice warnings (3+ triggers auto-flag)
        malpractice_count = MalpracticeRecord.objects.filter(student=student, exam=exam).count()
        flagged = malpractice_count >= 3  

        # Ensure `StudentExam` is created or updated correctly
        student_exam, created = StudentExam.objects.update_or_create(
            student=student,
            exam=exam,
            defaults={
                "submitted_at": now(),
                "attempted_at": now() if not StudentExam.objects.filter(student=student, exam=exam).exists() else StudentExam.objects.get(student=student, exam=exam).attempted_at
            }
        )

        # Ensure `ExamResult` is created or updated correctly
        ExamResult.objects.update_or_create(
            student=student,
            exam=exam,
            defaults={
                "score": total_score,
                "submitted_at": now(),
                "flagged": flagged
            }
        )

        # Response for automatic submission (JavaScript detection)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Exam submitted automatically due to malpractice warnings."})

        messages.success(request, "Exam submitted successfully.")
        response = HttpResponseRedirect('/my-results/')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    return redirect('available_exam')



def exam_results(request):
    """
    View to display exam results for the teacher, including submission times, 
    passing criteria, and detailed breakdown of student responses with malpractice warnings.
    """

    exams = Exam.objects.filter(created_by=request.user).prefetch_related(
        'questions', 'results__student'
    )

    student_exams = StudentExam.objects.filter(exam__in=exams).select_related('student', 'exam')

    student_exam_dict = {
        (se.student_id, se.exam_id): se.submitted_at for se in student_exams
    }

    exam_data = []
    for exam in exams:
        total_marks = exam.questions.aggregate(total=Sum('marks'))['total'] or 0
        passing_marks = (total_marks * exam.passing_grade) / 100 if total_marks > 0 else 0

        results = []
        for result in exam.results.all():
            # ✅ Get all student submissions for this exam
            submissions = Submission.objects.filter(student=result.student, exam=exam).select_related("question")

            # ✅ Calculate total marks obtained
            total_marks_obtained = sum(
                sub.question.marks if sub.selected_option == sub.question.correct_answer else 0
                for sub in submissions
            )

            # ✅ Calculate percentage score
            total_score = round((total_marks_obtained / total_marks * 100), 2) if total_marks > 0 else 0

            # ✅ Fetch malpractice warnings count from MalpracticeRecord model
            malpractice_count = MalpracticeRecord.objects.filter(student=result.student, exam=exam).count()

            # ✅ Prepare question breakdown like in `my_results`
            questions_data = [
                {
                    "question": sub.question.text,
                    "selected_option": sub.selected_option,
                    "correct_answer": sub.question.correct_answer,
                    "score": sub.question.marks if sub.selected_option == sub.question.correct_answer else 0,
                }
                for sub in submissions
            ]

            results.append({
                "student": result.student,
                "score": total_score,
                "marks_obtained": total_marks_obtained,
                "submitted_at": student_exam_dict.get((result.student.id, exam.id), "Not Available"),
                "is_passed": total_score >= exam.passing_grade,
                "video_url": result.video_url,
                "malpractice_count": malpractice_count,  # ✅ Corrected malpractice count
                "questions": questions_data,  
            })

        exam_data.append({
            "exam": exam,
            "total_marks": total_marks,
            "passing_marks": round(passing_marks, 2),
            "results": results,
        })

    return render(request, 'examresults.html', {'exam_data': exam_data})


@login_required
def view_exam_teacher(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Calculate total marks for the exam
    total_marks = exam.questions.aggregate(total=Sum('marks'))['total'] or 0

    return render(request, 'view_exam_teacher.html', {
        'exam': exam,
        'total_marks': total_marks
    })


@never_cache  # Prevents caching
def my_results(request):
    student = request.user

    # Fetch exam results for the student
    results = ExamResult.objects.filter(student=student).select_related("exam")

    exams = {}
    for result in results:
        exam = result.exam
        passing_grade = exam.passing_grade  # Fetch from the model dynamically

        # Fetch student submissions for the exam
        submissions = Submission.objects.filter(student=student, exam=exam).select_related("question")

        # Calculate total marks available for the exam
        total_marks = exam.questions.aggregate(total=Sum("marks"))["total"] or 0

        # Calculate obtained marks correctly
        total_marks_obtained = sum(
            sub.question.marks if sub.selected_option == sub.question.correct_answer else 0
            for sub in submissions
        )

        # Calculate percentage score
        total_score = (total_marks_obtained / total_marks * 100) if total_marks > 0 else 0

        # Prepare question details
        questions_data = [
            {
                "question": sub.question.text,
                "selected_option": sub.selected_option,
                "correct_answer": sub.question.correct_answer,
                "score": sub.question.marks if sub.selected_option == sub.question.correct_answer else 0,
            }
            for sub in submissions
        ]

        exams[exam.subject] = {
            "total_score": round(total_score, 2),  # Rounded percentage
            "passing_grade": passing_grade,  # Uses dynamic passing grade
            "questions": questions_data,
        }

    response = render(request, 'my_results.html', {'exams': exams})

    # 🔥 Ensure cache is fully disabled 🔥
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils.timezone import localtime, is_naive, make_aware
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from django.db.models import Sum
from .models import Exam, ExamResult, Submission, StudentExam, MalpracticeRecord  # Import MalpracticeRecord
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import localtime, make_aware, is_naive
from django.db.models import Sum

def download_exam_report(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    results = ExamResult.objects.filter(exam=exam)
    total_marks = exam.questions.aggregate(total=Sum('marks'))['total'] or 0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{exam.subject}_report.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    question_style = ParagraphStyle(
        name='QuestionStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=0,
        wordWrap='CJK'
    )

    title = Paragraph(f"<b>{exam.subject} Exam Report</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 8))

    summary_data = [["Student", "Score (%)", "Marks", "Passing Grade", "Status", "Malpractice", "Submitted At"]]
    total_students = 0
    total_passed = 0

    for result in results:
        submissions = Submission.objects.filter(student=result.student, exam=exam)
        total_marks_obtained = sum(
            sub.question.marks if sub.selected_option == sub.question.correct_answer else 0
            for sub in submissions
        )

        score_percent = round((total_marks_obtained / total_marks * 100), 2) if total_marks else 0
        status = "Passed" if score_percent >= exam.passing_grade else "Failed"
        if status == "Passed":
            total_passed += 1
        total_students += 1

        student_exam = StudentExam.objects.filter(student=result.student, exam=exam).first()
        submitted_at = "N/A"
        if student_exam and student_exam.submitted_at:
            if is_naive(student_exam.submitted_at):
                student_exam.submitted_at = make_aware(student_exam.submitted_at)
            submitted_at = localtime(student_exam.submitted_at).strftime('%Y-%m-%d %I:%M %p')

        malpractice_count = MalpracticeRecord.objects.filter(student=result.student, exam=exam).count()

        summary_data.append([
            result.student.username,
            f"{score_percent}%",
            f"{total_marks_obtained}/{total_marks}",
            f"{exam.passing_grade}%",
            status,
            malpractice_count,
            submitted_at
        ])

    summary_table = Table(summary_data, colWidths=[
        1.2 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 0.8 * inch, 0.9 * inch, 1.5 * inch
    ])

    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 8))

    total_summary = [
        ["Total Students Attended:", total_students],
        ["Total Students Passed:", total_passed]
    ]
    total_summary_table = Table(total_summary, colWidths=[2.5 * inch, 1 * inch])
    total_summary_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))

    elements.append(total_summary_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>Detailed Student Answers</b>", styles['Heading2']))
    elements.append(Spacer(1, 6))

    for result in results:
        submissions = Submission.objects.filter(student=result.student, exam=exam)
        if submissions.exists():
            elements.append(Paragraph(f"<b>Student: {result.student.username}</b>", styles['Heading3']))
            elements.append(Spacer(1, 4))

            answer_data = [["No.", "Question", "Selected Option", "Correct Answer", "Marks"]]

            for index, sub in enumerate(submissions, 1):
                is_correct = "✔" if sub.selected_option == sub.question.correct_answer else "✘"
                wrapped_question = Paragraph(sub.question.text, question_style)
                answer_data.append([
                    index,
                    wrapped_question,
                    f"{sub.selected_option} {is_correct}",
                    sub.question.correct_answer,
                    sub.score
                ])

            answer_table = Table(answer_data, colWidths=[
                0.5 * inch, 3.5 * inch, 1.2 * inch, 1.2 * inch, 0.6 * inch
            ])

            answer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (1, 1), (-1, -1), 'TOP')
            ]))

            elements.append(KeepTogether(answer_table))
            elements.append(Spacer(1, 6))  # small spacer between students

    doc.build(elements)
    return response


def adminlogin(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()  # Trim spaces
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, "Successfully logged in as admin!")
            return redirect('admindashboard')  # Redirect to admin dashboard
        else:
            messages.error(request, "Invalid credentials or not an admin!")

    # Clear messages after they are displayed once
    storage = messages.get_messages(request)
    storage.used = True

    return render(request, 'adminlogin.html')

# Admin logout view

def adminlogout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('index')  # Redirect to the home page after logout


def admindashboard(request):
    total_teachers = User.objects.filter(groups__name='Teacher').count()
    total_students = User.objects.filter(groups__name='Student').count()
    total_exams = Exam.objects.count()

    # Get pending teachers (assuming unapproved teachers have `is_active=False`)
    pending_teachers = User.objects.filter(groups__name='Teacher', is_active=False).count()

    # Get pending exams (assuming pending exams have `approval_status="pending"`)
    pending_exams = Exam.objects.filter(approval_status="pending").count()

    # Debugging logs
    print("✅ DEBUG: Admin Dashboard View Called")
    print("Total Teachers:", total_teachers)
    print("Total Students:", total_students)
    print("Total Exams:", total_exams)
    print("Pending Teacher Approvals:", pending_teachers)
    print("Pending Exam Approvals:", pending_exams)

    context = {
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_exams': total_exams,
        'pending_teachers': pending_teachers,  # Added pending teacher approvals
        'pending_exams': pending_exams,  # Added pending exam approvals
    }

    return render(request, 'admindashboard.html', context)

# def adminlogin(request):
#     return render(request, 'adminlogin.html')


def admin_pending_exams(request):
    pending_exams = Exam.objects.filter(approval_status='pending')
    approved_exams = Exam.objects.filter(approval_status='approved')
    rejected_exams = Exam.objects.filter(approval_status='rejected')  # Added rejected exams

    return render(request, 'admin_exam_approval.html', {
        'pending_exams': pending_exams,
        'approved_exams': approved_exams,
        'rejected_exams': rejected_exams  # Pass rejected exams to the template
    })




@login_required
def exam_approval(request):
    if request.method == "POST":
        exam_id = request.POST.get("exam_id")
        action = request.POST.get("action")

        exam = get_object_or_404(Exam, id=exam_id)

        if action == "approve":
            exam.approval_status = "approved"
            messages.success(request, f"Exam '{exam.subject}' has been approved.")
        elif action == "reject":
            exam.approval_status = "rejected"
            messages.error(request, f"Exam '{exam.subject}' has been rejected.")

        exam.save()
        return redirect("exam_approval")  # Reload the page after action

    pending_exams = Exam.objects.filter(approval_status="pending")
    approved_exams = Exam.objects.filter(approval_status="approved")
    rejected_exams = Exam.objects.filter(approval_status="rejected")  # ✅ Include rejected exams

    return render(request, "admin_pending_exams.html", {
        "pending_exams": pending_exams,
        "approved_exams": approved_exams,
        "rejected_exams": rejected_exams,  # ✅ Pass rejected exams to template
    })

# @login_required
# def view_exam(request, exam_id):
#     exam = get_object_or_404(Exam, id=exam_id)
    
#     # Calculate total marks for the exam
#     total_marks = exam.questions.aggregate(total=Sum('marks'))['total'] or 0

#     return render(request, 'view_exam.html', {
#         'exam': exam,
#         'total_marks': total_marks
#     })

@staff_member_required
def approve_exam(request, exam_id):
    """Admin approves an exam and notifies the teacher by email."""
    exam = get_object_or_404(Exam, id=exam_id)

    if exam.approval_status != "approved":
        exam.approval_status = "approved"
        exam.save()

        # ✅ Send email to the teacher
        teacher = exam.created_by
        if teacher.email:
            try:
                email_body = render_to_string("exam_approved_email.html", {
                    "teacher": teacher,
                    "exam": exam,
                })

                email = EmailMessage(
                    subject="Your Exam Has Been Approved 🎉",
                    body=email_body,
                    to=[teacher.email],
                )
                email.content_subtype = "html"
                email.send()

                messages.success(request, f"Exam '{exam.subject}' approved and teacher was notified by email.")
            except Exception as e:
                messages.warning(request, f"Exam approved, but email notification failed: {e}")
        else:
            messages.warning(request, "Exam approved, but the teacher has no email address.")
    else:
        messages.info(request, f"Exam '{exam.subject}' is already approved.")

    return redirect("exam_approval")

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Exam

@staff_member_required
def reject_exam(request, exam_id):
    """Admin rejects an exam by updating its approval status instead of deleting it."""
    exam = get_object_or_404(Exam, id=exam_id)

    if exam.approval_status != "rejected":
        exam.approval_status = "rejected"
        exam.save()

        # ✅ Email the teacher who created this exam
        teacher = exam.created_by
        if teacher.email:
            try:
                email_body = render_to_string("exam_rejected_email.html", {
                    "teacher": teacher,
                    "exam": exam,
                })

                email = EmailMessage(
                    subject="Your Exam Has Been Rejected",
                    body=email_body,
                    to=[teacher.email],
                )
                email.content_subtype = "html"
                email.send()

                messages.success(request, f"Exam '{exam.subject}' has been rejected and the teacher was notified.")
            except Exception as e:
                messages.warning(request, f"Exam rejected but failed to send email: {e}")
        else:
            messages.warning(request, "Exam rejected but teacher has no email address.")

    else:
        messages.warning(request, f"Exam '{exam.subject}' is already rejected.")

    return redirect("exam_approval")




@login_required
def approve_teacher(request, teacher_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized action!")
        return redirect('admindashboard')

    try:
        teacher = User.objects.get(id=teacher_id, groups__name='Teacher', is_active=False)
        teacher.is_active = True  # Activate the teacher
        teacher.save()

        # ✅ Send approval email
        try:
            email_body = render_to_string("teacher_approved_email.html", {
                "teacher": teacher,
            })

            email = EmailMessage(
                subject="You're Approved as a Teacher!",
                body=email_body,
                to=[teacher.email],
            )
            email.content_subtype = "html"
            email.send()
            messages.success(request, f"{teacher.username} has been approved and notified by email.")
        except Exception as email_error:
            messages.warning(request, f"{teacher.username} was approved, but email failed: {email_error}")

    except User.DoesNotExist:
        messages.error(request, "Teacher not found!")

    return redirect('teacher_pending')

def teacherapproval(request):
    return render(request, 'teacherapproval.html')

@login_required
def reject_teacher(request, teacher_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized action!")
        return redirect('admindashboard')

    try:
        teacher = User.objects.get(id=teacher_id, groups__name='Teacher', is_active=False)

        # ✅ Send rejection email before deleting
        if teacher.email:
            try:
                email_body = render_to_string("teacher_rejected_email.html", {
                    "teacher": teacher,
                })

                email = EmailMessage(
                    subject="Teacher Registration Denied",
                    body=email_body,
                    to=[teacher.email],
                )
                email.content_subtype = "html"
                email.send()
                messages.info(request, f"Teacher {teacher.username} was notified by email about the rejection.")
            except Exception as e:
                messages.warning(request, f"Email to {teacher.username} failed: {e}")

        teacher.delete()
        messages.success(request, f"Teacher request for {teacher.username} has been rejected and removed.")
        
    except User.DoesNotExist:
        messages.error(request, "Teacher not found!")

    return redirect('teacher_pending')


def teacher_pending(request):
    # Ensure only superusers (admins) can access this view
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized action!")
        return redirect('admindashboard')  # Redirect to the admin dashboard if not authorized

    # Fetch all pending teachers (inactive teachers)
    pending_teachers = User.objects.filter(groups__name='Teacher', is_active=False)

    # Check if the admin is approving a teacher
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        approve_action = request.POST.get('approve_action')

        if teacher_id and approve_action == 'approve':
            try:
                teacher = User.objects.get(id=teacher_id)
                teacher.is_active = True  # Mark the teacher as active (approved)
                teacher.save()
                messages.success(request, f"Teacher {teacher.username} has been approved.")
            except User.DoesNotExist:
                messages.error(request, "Teacher not found.")

            return redirect('teacher_pending')  # Redirect back to the teacher list page after approval

    # Render the pending teacher list
    return render(request, 'teacherpending.html', {
        'pending_teachers': pending_teachers,
    })


def manage_student(request, id):
    student = get_object_or_404(User, id=id)

    # Your logic for managing the student here (e.g., updating their details)
    if request.method == 'POST':
        # Example: updating student info
        student.first_name = request.POST.get('first_name')
        student.last_name = request.POST.get('last_name')
        student.save()
        messages.success(request, f"Student {student.username} updated successfully!")

    return render(request, 'manage_student.html', {'student': student})


def delete_student(request, id):
    # Fetch the student user by ID
    student = get_object_or_404(User, id=id)

    # Check if the user is a student
    if student.groups.filter(name='Student').exists():
        student.delete()
        messages.success(request, f"Student {student.username} deleted successfully.")
    else:
        messages.error(request, "This user is not a student.")
    
    return redirect('manage_users')  # Redirect back to the admin dashboard


def manage_teacher(request, id):
    # Fetch the teacher by ID
    teacher = get_object_or_404(User, id=id)

    # Example of rendering a template to manage teacher details
    return render(request, 'manage_teacher.html', {'teacher': teacher})


def delete_teacher(request, id):
    # Fetch the teacher by ID
    teacher = get_object_or_404(User, id=id)

    # Delete the teacher
    teacher.delete()

    # Optionally, add a success message
    messages.success(request, f"Teacher {teacher.username} has been deleted successfully.")

    # Redirect to a page, e.g., the admin dashboard
    return redirect('manage_users')


def manage_users(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied!")
        return redirect('adminlogin')

    # Fetch active teachers and students
    active_teachers = User.objects.filter(groups__name='Teacher', is_active=True)
    students = User.objects.filter(groups__name='Student', is_active=True)

    return render(request, 'manageusers.html', {
        'active_teachers': active_teachers,
        'students': students,
    })


def is_admin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_admin)
def manage_exams(request):
    exams = Exam.objects.all()
    return render(request, 'manage_exams.html', {'exams': exams})

# View for deleting an exam
@login_required
@user_passes_test(is_admin)
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == "POST":
        exam.delete()
        messages.success(request, "Exam deleted successfully.")
    
    # Redirect back to the Manage Exams page
    return redirect('manage_exams')

def save_recording(request):
    if request.method == "POST" and request.FILES.get("video"):
        video_file = request.FILES["video"]
        exam_id = request.POST.get("exam_id")

        # Save file
        file_path = f"recordings/exam_{exam_id}_{video_file.name}"
        file_name = default_storage.save(file_path, video_file)

        return JsonResponse({"status": "success", "file_url": default_storage.url(file_name)})

    return JsonResponse({"status": "error", "message": "No video file received."})

import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.files.storage import default_storage
from .models import Exam, ExamResult

logger = logging.getLogger(__name__)

def upload_recording(request, exam_id):
    if request.method == "POST" and request.FILES.get("recording"):
        try:
            exam = get_object_or_404(Exam, id=exam_id)
            student = request.user

            if not student.is_authenticated:
                logger.warning("🚫 Unauthenticated user tried to upload recording.")
                return JsonResponse({"error": "Authentication required"}, status=403)

            recording_file = request.FILES["recording"]
            if not recording_file.name.endswith(".webm"):
                logger.warning("⚠️ Invalid recording format uploaded.")
                return JsonResponse({"error": "Invalid file format"}, status=400)

            # Save the video file
            filename = f"recordings/exam_{exam.id}_student_{student.id}.webm"
            file_path = default_storage.save(filename, recording_file)

            # Update or create the exam result with the video URL
            result, created = ExamResult.objects.get_or_create(exam=exam, student=student)
            result.video_url = file_path
            result.save()

            logger.info(f"✅ Recording saved for student {student.id} in exam {exam.id}: {file_path}")

            return JsonResponse({
                "message": "Recording uploaded successfully",
                "video_url": file_path
            })

        except Exception as e:
            logger.exception("❌ Error during recording upload")
            return JsonResponse({"error": "Failed to upload recording"}, status=500)

    logger.warning("⚠️ Invalid recording upload attempt - no file or wrong method.")
    return JsonResponse({"error": "Invalid request"}, status=400)

def available_exam(request):
    student = request.user
    current_time = now()

    # ✅ Fetch only approved exams & calculate total marks
    approved_exams = Exam.objects.filter(approval_status="approved") \
                                .annotate(total_marks=Sum('questions__marks'))

    # ✅ Get student's attempted exams & scores
    attempted_exams = ExamResult.objects.filter(student=student).select_related("exam")
    attempted_exam_data = {result.exam_id: result.score for result in attempted_exams}

    # ✅ Available exams (NOT attempted & NOT expired)
    available_exams = approved_exams.exclude(id__in=attempted_exam_data.keys()).filter(expiry_date__gte=current_time)

    # ✅ Expired exams (Past expiry date)
    expired_exams = approved_exams.filter(expiry_date__lt=current_time)

    # ✅ Assign student scores for attempted exams
    for result in attempted_exams:
        exam = result.exam
        exam.student_score = attempted_exam_data.get(exam.id, 0)

    context = {
        "available_exams": available_exams,
        "attempted_exams": attempted_exams,  # Contains student scores
        "expired_exams": expired_exams,
    }
    return render(request, "availableexams.html", context)

import json
import logging
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Exam, MalpracticeRecord

logger = logging.getLogger(__name__)

@csrf_exempt  # Use only if necessary; consider CSRF token in frontend requests instead.
def record_malpractice(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))  # Ensure proper decoding
        exam_id = data.get("exam_id")
        issue = data.get("issue")

        if not request.user.is_authenticated:
            logger.warning("Unauthorized malpractice report attempt.")
            return JsonResponse({"status": "error", "message": "User not authenticated"}, status=401)

        if not exam_id or not issue:
            logger.warning(f"Missing data in malpractice report: {data}")
            return JsonResponse({"status": "error", "message": "Missing exam_id or issue"}, status=400)

        exam = get_object_or_404(Exam, id=exam_id)
        malpractice_record = MalpracticeRecord.objects.create(student=request.user, exam=exam, issue=issue)

        logger.info(f"Malpractice recorded: {malpractice_record}")
        return JsonResponse({"status": "success", "message": "Malpractice recorded."})

    except json.JSONDecodeError:
        logger.error("Invalid JSON format received in malpractice report.")
        return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)

    except Exception as e:
        logger.exception(f"Unexpected error recording malpractice: {e}")
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"}, status=500)


def get_malpractice_count(request, exam_id):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "User not authenticated"}, status=401)

    count = MalpracticeRecord.objects.filter(student=request.user, exam_id=exam_id).count()
    return JsonResponse({"status": "success", "malpractice_count": count})



from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

@login_required
def send_result_email(request):
    if request.method == "POST":
        exam_name = request.POST.get("exam_name")
        student = request.user

        # Get exam data from your context logic
        results = ExamResult.objects.filter(student=student, exam__subject=exam_name).select_related("exam")
        if not results.exists():
            messages.error(request, "No result found for this exam.")
            return redirect("my_results")

        result = results.first()
        exam = result.exam
        submissions = Submission.objects.filter(student=student, exam=exam).select_related("question")
        total_marks = exam.questions.aggregate(total=Sum("marks"))["total"] or 0
        obtained = sum(
            sub.question.marks if sub.selected_option == sub.question.correct_answer else 0
            for sub in submissions
        )
        percentage = round((obtained / total_marks * 100), 2) if total_marks else 0

        # Determine if the student passed
        passed = percentage >= exam.passing_grade

        # Render email HTML
        email_body = render_to_string("email_result_template.html", {
            "student": student,
            "exam": exam,
            "submissions": submissions,
            "total_marks": total_marks,
            "obtained": obtained,
            "percentage": percentage,
            "passed": passed,  # Include passed in context
        })

        email = EmailMessage(
            subject=f"{exam.subject} - Exam Report",
            body=email_body,
            from_email="onlineexam575@gmail.com",  # Replace with your domain's email
            to=[student.email],
        )
        email.content_subtype = "html"  # To send HTML email
        email.send()

        messages.success(request, "Your report has been emailed to your Gmail address.")
        return redirect("my_results")



from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import os


@login_required
def send_exam_report_email_to_teacher(request):
    if request.method == "POST":
        exam_id = request.POST.get("exam_id")
        try:
            # Fetch the exam object using the provided exam ID
            exam = get_object_or_404(Exam, pk=exam_id)
            teacher = exam.created_by  # Teacher who created the exam

            # Fetch all submissions related to this exam
            submissions = Submission.objects.filter(exam=exam)
            total_marks = sum(q.marks for q in exam.questions.all())
            students = set(sub.student for sub in submissions)

            results = []
            video_attachments = []

            for student in students:
                student_subs = submissions.filter(student=student)

                # Calculate score and percentage for each student
                score = sum(
                    s.question.marks for s in student_subs
                    if s.selected_option == s.question.correct_answer
                )
                percentage = round(score / total_marks * 100, 2) if total_marks else 0

                # Get the exam result for the student
                exam_result = ExamResult.objects.filter(student=student, exam=exam).first()

                # Get video file path (if exists)
                video_url = None
                video_path = None
                if exam_result and exam_result.video_url:
                    video_url = exam_result.video_url.url
                    video_path = exam_result.video_url.name

                # Attach video to email if available
                if video_path and default_storage.exists(video_path):
                    filename = f"{student.username}_recording{os.path.splitext(video_path)[1]}"
                    with default_storage.open(video_path, 'rb') as video_file:
                        video_attachments.append((filename, video_file.read(), 'video/mp4'))

                # Calculate malpractice count (default to 0 if no result exists)
                mal_count = MalpracticeRecord.objects.filter(student=student, exam=exam).count()

                # Add student's results to the list
                results.append({
                    "student": student,
                    "score": percentage,
                    "is_passed": percentage >= exam.passing_grade,
                    "malpractice_count": mal_count,
                    "submitted_at": exam_result.submitted_at if exam_result else "N/A",
                    "video_url": video_url,
                })

            # Render the email body using the template
            email_body = render_to_string("teacher_exam_report_email.html", {
                "exam": exam,
                "results": results,
                "total_marks": total_marks
            })

            # Create and send the email with the compiled report
            email = EmailMessage(
                subject=f"Exam Report: {exam.subject} - {exam.date}",
                body=email_body,
                to=[teacher.email],
            )
            email.content_subtype = "html"

            # Attach video files if available
            for filename, filedata, mimetype in video_attachments:
                email.attach(filename, filedata, mimetype)

            email.send()
            messages.success(request, f"Report and recordings sent to {teacher.email}")

        except Exception as e:
            # Handle any errors that occur during the email sending process
            messages.error(request, f"Error sending report: {e}")

    return redirect("exam_results")