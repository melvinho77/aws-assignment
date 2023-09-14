from flask import render_template
from flask import redirect
import mimetypes
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from botocore.exceptions import ClientError
from pymysql import connections
import os
import boto3
from config import *
import datetime

app = Flask(__name__)
app.secret_key = 'cc'

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route('/')
def index():
    return render_template('home.html', number=1)


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('home.html')


@app.route('/register_company')
def register_company():
    return render_template('RegisterCompany.html')


@app.route('/login_company', methods=['GET', 'POST'])
def login_company():
    return render_template('LoginCompany.html')


@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    return render_template('LoginStudent.html')

# Navigation to Student Home Page


@app.route('/student_home', methods=['GET', 'POST'])
def student_home():
    id = session['loggedInStudent']

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        if not student:
            return "No such student exist."

    except Exception as e:
        return str(e)

    return render_template('studentHome.html', studentId=student[0],
                           studentName=student[1],
                           IC=student[2],
                           mobileNumber=student[3],
                           gender=student[4],
                           address=student[5],
                           email=student[6],
                           level=student[7],
                           programme=student[8],
                           supervisor=student[9],
                           cohort=student[10])

# Navigation to Edit Student Page


@app.route('/edit_student', methods=['GET', 'POST'])
def edit_student():
    id = session['loggedInStudent']

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        if not student:
            return "No such student exist."

    except Exception as e:
        return str(e)

    pendingRequestCount = check_pending_requests(id)

    return render_template('EditStudentProfile.html', studentId=student[0],
                           studentName=student[1],
                           IC=student[2],
                           mobileNumber=student[3],
                           gender=student[4],
                           address=student[5],
                           email=student[6],
                           level=student[7],
                           programme=student[8],
                           supervisor=student[9],
                           cohort=student[10],
                           pendingRequestCount=pendingRequestCount)

# CHECK REQUEST EDIT PENDING


def check_pending_requests(id):
    pending_request_sql = "SELECT COUNT(*) FROM request WHERE studentId = %s AND status = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(pending_request_sql, (id, 'pending'))
        foundRecords = cursor.fetchall()

        if not foundRecords:
            return 0

        return foundRecords[0][0]

    except Exception as e:
        return str(e)

# Update student profile (Function)


@app.route('/update_student', methods=['GET', 'POST'])
def update_student():
    id = session['loggedInStudent']

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        if not student:
            return "No such student exist."

    except Exception as e:
        return str(e)

    # Get the newly updated input fields
    newStudentName = request.form['studentName']
    newGender = request.form['gender']
    newMobileNumber = request.form['mobileNumber']
    newAddress = request.form['address']

    # Compare with the old fields
    # Student name
    if student[1] != newStudentName:
        # Insert into request table
        insert_sql = "INSERT INTO request (attribute, newData, status, reason, studentId) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_sql, ('studentName', newStudentName,
                                    'pending', None, session['loggedInStudent']))
        db_conn.commit()

    # Gender
    if student[4] != newGender:
        # Insert into request table
        insert_sql = "INSERT INTO request (attribute, newData, status, reason, studentId) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_sql, ('gender', newGender, 'pending',
                                    None, session['loggedInStudent']))
        db_conn.commit()

    # Mobile number
    if student[3] != newMobileNumber:
        # Insert into request table
        insert_sql = "INSERT INTO request (attribute, newData, status, reason, studentId) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_sql, ('mobileNumber', newMobileNumber,
                                    'pending', None, session['loggedInStudent']))
        db_conn.commit()

    # Address
    if student[5] != newAddress:
        # Insert into request table
        insert_sql = "INSERT INTO request (attribute, newData, status, reason, studentId) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_sql, ('address', newAddress,
                                    'pending', None, session['loggedInStudent']))
        db_conn.commit()

    return redirect('/edit_student')

# Navigate to Upload Resume Page


@app.route('/upload_resume', methods=['GET', 'POST'])
def upload_resume():
    id = session['loggedInStudent']

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        if not student:
            return "No such student exist."

    except Exception as e:
        return str(e)

    return render_template('UploadResume.html', studentId=student[0],
                           studentName=student[1],
                           IC=student[2],
                           mobileNumber=student[3],
                           gender=student[4],
                           address=student[5],
                           email=student[6],
                           level=student[7],
                           programme=student[8],
                           supervisor=student[9],
                           cohort=student[10],)

# Upload Resume into S3


@app.route('/uploadResume', methods=['GET', 'POST'])
def uploadResume():
    id = session['loggedInStudent']

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()
    stud_resume_file_name_in_s3 = id + "_resume"
    student_resume_file = request.files['resume']

    s3 = boto3.resource('s3')

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()
        db_conn.commit()

        print("Data inserted in MySQL RDS... uploading resume to S3...")

        # Set the content type to 'application/pdf' when uploading to S3
        s3.Object(custombucket, stud_resume_file_name_in_s3).put(
            Body=student_resume_file,
            ContentType='application/pdf'
        )

        bucket_location = boto3.client(
            's3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

    except Exception as e:
        return str(e)

    print("Resume uploaded complete.")
    return render_template('UploadResumeOutput.html', studentName=student[1], id=session['loggedInStudent'])


# Download resume from S3 (based on Student Id)
@app.route('/viewResume', methods=['GET', 'POST'])
def view_resume():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')
    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"{student_id}_resume"

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')

    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': custombucket,
                'Key': object_key,
                'ResponseContentDisposition': 'inline',
            },
            ExpiresIn=3600  # Set the expiration time (in seconds) as needed
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            # If the resume does not exist, return a page with a message
            return render_template('no_resume_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


# Navigate to Student View Report
@app.route('/view_progress_report', methods=['GET', 'POST'])
def view_progress_report():
    # Retrieve student's ID
    id = session.get('loggedInStudent')
    if not id:
        return "Student not logged in."

    # Retrieve the cohort where student belongs to
    select_sql = "SELECT startDate, endDate FROM cohort c, student s WHERE studentId = %s AND c.cohortId = s.cohort"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        cohort = cursor.fetchone()

        if not cohort:
            return "No such cohort exists."

    except Exception as e:
        return str(e)

    # Convert start_date_str and end_date_str into datetime objects
    start_date_str = str(cohort[0])
    end_date_str = str(cohort[1])

    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")

    # Calculate submission dates and report names
    submission_info = calculate_submission_date(start_date, end_date)

    # Format submission dates as "day-month-year"
    submission_dates = [date.strftime('%d-%m-%Y')
                        for date, _ in submission_info]
    report_names = [report_name for _, report_name in submission_info]

    combined_data = list(zip(submission_dates, report_names))

    return render_template('StudentViewReport.html', student_id=session.get('loggedInStudent'), combined_data=combined_data)

# Calculate the submission dates and return in a list


def calculate_submission_date(start_date, end_date):
    # Calculate the number of months between the start date and end date.
    months_between_dates = (end_date.year - start_date.year) * \
        12 + (end_date.month - start_date.month) + 1

    # Initialize a list to store submission dates and report names as tuples.
    submission_info = []

    for i in range(1, months_between_dates + 1):
        # Calculate the target month and year for this report
        target_month = (start_date.month + i - 1) % 12
        target_year = start_date.year + (start_date.month + i - 1) // 12

        # Calculate the 4th day of the target month
        submission_date = datetime.date(target_year, target_month + 1, 4)

        # If the start date is before the 4th day of the current month,
        # adjust the submission date to the 4th day of the next month
        if start_date.day < 4 and submission_date > start_date:
            submission_date = datetime.date(
                target_year, target_month + 2, 4)

        report_name = f'Progress Report {i}'
        submission_info.append((submission_date, report_name))

    # Calculate the final report submission date, which is 1 week before the end date.
    final_report_date = end_date - datetime.timedelta(days=7)
    submission_info.append((final_report_date, 'Final Report'))

    return submission_info

# Upload progress report function


@app.route('/uploadProgressReport', methods=['GET', 'POST'])
def uploadProgressReport():
    # Retrieve Student ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in"

# Navigate to Student Registration


@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    return render_template("RegisterStudent.html")

# Register a student


@app.route("/addstud", methods=['POST'])
def add_student():
    try:
        level = request.form['level']
        cohort = request.form['cohort']
        programme = request.form['programme']
        student_id = request.form['studentId']
        email = request.form['email']
        name = request.form['name']
        ic = request.form['ic']
        mobile = request.form['mobile']
        gender = request.form['gender']
        address = request.form['address']

        insert_sql = "INSERT INTO student (studentId, studentName, IC, mobileNumber, gender, address, email, level, programme, cohort) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor = db_conn.cursor()

        cursor.execute(insert_sql, (student_id, name, ic, mobile,
                                    gender, address, email, level, programme, cohort))
        db_conn.commit()

    except Exception as e:
        db_conn.rollback()

    finally:
        cursor.close()

    # Redirect back to the registration page with a success message
    return render_template("home.html")


@app.route("/about", methods=['POST'])
def about():
    return render_template('www.tarc.edu.my')

# Verify login


@app.route("/verifyLogin", methods=['POST', 'GET'])
def verifyLogin():
    if request.method == 'POST':
        StudentIc = request.form['StudentIc']
        Email = request.form['Email']

        # Query the database to check if the email and IC number match a record
        cursor = db_conn.cursor()
        query = "SELECT * FROM student WHERE IC = %s AND email = %s"
        cursor.execute(query, (StudentIc, Email))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # User found in the database, login successful
            # Redirect to the student home page
            session['loggedInStudent'] = user[0]
            return render_template('studentHome.html', studentId=user[0], studentName=user[1], IC=user[2], mobileNumber=user[3], gender=user[4], address=user[5], email=user[6], level=user[7], programme=user[8], supervisor=user[9], cohort=user[10])
        else:
            # User not found, login failed
            return render_template('LoginStudent.html', msg="Access Denied: Invalid Email or Ic Number")


@app.route('/downloadStudF04', methods=['GET'])
def download_StudF04():
    # Construct the S3 object key
    object_key = f"forms/FOCS_StudF04.docx"

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')

    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': custombucket,
                'Key': object_key,
                'ResponseContentDisposition': 'inline',
            },
            ExpiresIn=3600  # Set the expiration time (in seconds) as needed
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            # If the resume does not exist, return a page with a message
            return render_template('no_resume_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


# DOWNLOAD FOCS_StudF05.docx
@app.route('/downloadStudF05', methods=['GET'])
def download_StudF05():
    # Construct the S3 object key
    object_key = f"forms/FOCS_StudF05.docx"

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')

    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': custombucket,
                'Key': object_key,
                'ResponseContentDisposition': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            },
            ExpiresIn=3600  # Set the expiration time (in seconds) as needed
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            # If the resume does not exist, return a page with a message
            return render_template('no_resume_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
