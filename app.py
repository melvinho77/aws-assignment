from flask import render_template, make_response
from flask import redirect
import mimetypes
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from botocore.exceptions import ClientError
from pymysql import connections
import boto3
from config import *
import datetime
from weasyprint import HTML

app = Flask(__name__)
app.static_folder = 'static'  # The name of your static folder
app.static_url_path = '/static'  # The URL path to serve static files
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

        # Retrieve cohort

        if not student:
            return "No such student exist."

    except Exception as e:
        return str(e)

    if student:
        # Student found in the database, login successful

        # Retrieve the cohort where student belongs to
        select_sql = "SELECT startDate, endDate FROM cohort c WHERE cohortId = %s"
        cursor = db_conn.cursor()
        cursor.execute(select_sql, (student[10]))
        cohort = cursor.fetchone()
        cursor.close()

        # Convert start_date_str and end_date_str into datetime.date objects
        start_date_str = str(cohort[0])
        end_date_str = str(cohort[1])
        start_date = datetime.date.fromisoformat(start_date_str)
        end_date = datetime.date.fromisoformat(end_date_str)

        #######################################################################
        # Retrieve supervisor details
        supervisor_query = "SELECT l.name, l.email FROM lecturer l, student s WHERE s.supervisor = l.lectId AND studentId = %s"
        cursor = db_conn.cursor()
        cursor.execute(supervisor_query, (student[0]))
        supervisor = cursor.fetchone()
        cursor.close()

        # Retrieve the company details
        company_query = "SELECT c.name, j.jobLocation, salary, jobPosition, jobDesc FROM company c, job j, companyApplication ca, student s WHERE c.companyId = j.company AND ca.student = s.studentId AND ca.job = j.jobId AND s.studentId = %s AND ca.`status` = 'approved'"
        cursor = db_conn.cursor()
        cursor.execute(company_query, (student[0]))
        companyDetails = cursor.fetchone()
        cursor.close()
        #######################################################################

        # Create a list to store all the retrieved data
        user_data = {
            'studentId': student[0],
            'studentName': student[1],
            'IC': student[2],
            'mobileNumber': student[3],
            'gender': student[4],
            'address': student[5],
            'email': student[6],
            'level': student[7],
            'programme': student[8],
            'cohort': student[10],
            'start_date': start_date,
            'end_date': end_date,
            # Default values if supervisor is not found
            'supervisor': supervisor if supervisor else ("N/A", "N/A"),
            # Default values if company details are not found
            'companyDetails': companyDetails if companyDetails else ("N/A", "N/A", "N/A", "N/A", "N/A")
        }

        # Set the loggedInStudent session
        session['loggedInStudent'] = student[0]

        # Redirect to the student home page with the user_data
        return render_template('studentHome.html', data=user_data)

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
    stud_resume_file_name_in_s3 = 'resume/' + id + "_resume"
    student_resume_file = request.files['resume']

    # Create the folder if not exist
    s3_client = boto3.client('s3')
    folder_name = 'resume/'

    # Check if the folder (prefix) already exists
    response = s3_client.list_objects_v2(
        Bucket=custombucket, Prefix=folder_name)

    # If the folder (prefix) doesn't exist, you can create it
    if 'Contents' not in response:
        s3_client.put_object(Bucket=custombucket, Key=(folder_name + '/'))

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
        db_conn.rollback()
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
    object_key = f"resume/{student_id}_resume"

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

    # Retrieve all the submission details based on student
    report_sql = "SELECT * from report WHERE student = %s"
    report_cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        cohort = cursor.fetchone()

        report_cursor.execute(report_sql, (id))
        report_details = report_cursor.fetchall()

        if not cohort:
            return "No such cohort or report details exists."

    except Exception as e:
        return str(e)

    # Create a list to store report details
    report_list = []

    # Iterate over the fetched report rows and append them to the list
    for row in report_details:
        report_list.append({
            # Adjust this to match your database structure
            'reportId': row[0],
            'submissionDate': row[1],
            'reportType': row[2],
            'status': row[3],
            'late': row[4],
            'remark': row[5],
            'student': row[6],
        })

    # Convert start_date_str and end_date_str into datetime.date objects
    start_date_str = str(cohort[0])
    end_date_str = str(cohort[1])

    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)

    # Calculate submission dates and report names
    submission_info = calculate_submission_date(start_date, end_date)

    # Format submission dates as "year-month-day"
    submission_dates = [date.strftime('%Y-%m-%d')
                        for date, _ in submission_info]
    report_names = [report_name for _, report_name in submission_info]

    combined_data = list(zip(submission_dates, report_names))

    return render_template('StudentViewReport.html', student_id=session.get('loggedInStudent'), combined_data=combined_data, start_date=cohort[0], end_date=cohort[1], report_list=report_list)

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

        # Calculate the 4th day of the target month as a datetime.date object
        submission_date = datetime.date(target_year, target_month + 1, 4)

        # If the start date is before the 4th day of the current month,
        # adjust the submission date to the 4th day of the next month
        if start_date.day < 4 and submission_date > start_date:
            submission_date = datetime.date(
                target_year, target_month + 1, 4)

        report_name = f'Progress Report {i}'
        submission_info.append((submission_date, report_name))

    # Calculate the final report submission date, which is 1 week before the end date.
    final_report_date = end_date - datetime.timedelta(days=7)
    submission_info.append((final_report_date, 'Final Report'))

    return submission_info

# Calculate the submission counts (INSERT AFTER REGISTER)


def calculate_submission_count(start_date, end_date):
    # Calculate the number of months between the start date and end date.
    months_between_dates = (end_date.year - start_date.year) * \
        12 + (end_date.month - start_date.month) + 1

    # Calculate the count of submission reports including the final report
    report_count = months_between_dates + 1  # +1 for the final report

    return report_count

# Upload progress report function


@app.route('/uploadProgressReport', methods=['GET', 'POST'])
def uploadProgressReport():
    # Retrieve all required data from forms / session
    id = session['loggedInStudent']
    report_type = request.form.get('report_type')
    # Remove spaces and concatenate words
    report_type = report_type.replace(" ", "")
    submission_date = request.form.get('submission_date')
    student_progress_report = request.files['progress_report']

    # Change submission date into datetime obj
    submission_date_obj = datetime.date.fromisoformat(submission_date)

    s3_client = boto3.client('s3')
    folder_name = 'progressReport/' + id  # Replace 'id' with your folder name

    # Check if the folder (prefix) already exists
    response = s3_client.list_objects_v2(
        Bucket=custombucket, Prefix=folder_name)

    # If the folder (prefix) doesn't exist, you can create it
    if 'Contents' not in response:
        s3_client.put_object(Bucket=custombucket, Key=(folder_name + '/'))

    # UPLOAD PROGRESS FOLDER OPERATION
    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()
    object_key = 'progressReport/' + id + '/' + id + "_" + report_type

    s3 = boto3.resource('s3')

    # Update the Report Table
    update_sql = "UPDATE report SET submissionDate = %s, status = %s, late = %s WHERE student = %s AND reportType = %s"
    request_cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        # Compare submission dates
        if datetime.date.today() > submission_date_obj:
            request_cursor.execute(
                update_sql, (datetime.date.today(), 'submitted', 1, id, report_type))
        else:
            request_cursor.execute(
                update_sql, (datetime.date.today(), 'submitted', 0, id, report_type))

        db_conn.commit()

        print("Data inserted in MySQL RDS... uploading resume to S3...")

        # Set the content type to 'application/pdf' when uploading to S3
        s3.Object(custombucket, object_key).put(
            Body=student_progress_report,
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
        db_conn.rollback()
        return str(e)

    print("Progress Report sucessfully submitted.")
    return render_template('UploadProgressReportOutput.html', studentName=student[1], id=session['loggedInStudent'])

# View progress report


@app.route('/viewProgressReport', methods=['GET', 'POST'])
def viewProgressReport():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')
    # Use request.args to get query parameters
    report_type = request.args.get('report_type')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"progressReport/{student_id}/{student_id}_{report_type}"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)

# Upload supporting documents


@app.route('/uploadSupportingDocuments', methods=['GET', 'POST'])
def uploadSupportingDocuments():
    id = session['loggedInStudent']

    # Retrieve the necessary documents
    acceptanceForm = request.files['acceptanceForm']
    acknowledgementForm = request.files['acknowledgementForm']
    indemnityLetter = request.files['indemnityLetter']
    supportLetter = request.files['supportLetter']
    hiredEvidence = request.files['hiredEvidence']

    objKey_acceptanceForm = 'supportingDocument/' + id + '/' + id + "_acceptanceForm"
    objKey_acknowledgementForm = 'supportingDocument/' + \
        id + '/' + id + "_acknowledgementForm"
    objKey_indemnityLetter = 'supportingDocument/' + \
        id + '/' + id + "_indemnityLetter"
    objKey_supportLetter = 'supportingDocument/' + id + '/' + id + "_supportLetter"
    objKey_hiredEvidence = 'supportingDocument/' + id + '/' + id + "_hiredEvidence"

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cursor = db_conn.cursor()

    # Create the folder if not exist
    s3_client = boto3.client('s3')
    folder_name = 'supportingDocument/' + id  # Replace 'id' with your folder name

    # Check if the folder (prefix) already exists
    response = s3_client.list_objects_v2(
        Bucket=custombucket, Prefix=folder_name)

    # If the folder (prefix) doesn't exist, you can create it
    if 'Contents' not in response:
        s3_client.put_object(Bucket=custombucket, Key=(folder_name + '/'))

    s3 = boto3.resource('s3')

    try:
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        # Set the content type to 'application/pdf' when uploading to S3
        # Upload acceptance form
        s3.Object(custombucket, objKey_acceptanceForm).put(
            Body=acceptanceForm,
            ContentType='application/pdf'
        )

        # Upload acknowledgement form
        s3.Object(custombucket, objKey_acknowledgementForm).put(
            Body=acknowledgementForm,
            ContentType='application/pdf'
        )

        # Upload indemnity letter
        s3.Object(custombucket, objKey_indemnityLetter).put(
            Body=indemnityLetter,
            ContentType='application/pdf'
        )

        # Upload support letter
        s3.Object(custombucket, objKey_supportLetter).put(
            Body=supportLetter,
            ContentType='application/pdf'
        )

        # Upload hired evidence
        s3.Object(custombucket, objKey_hiredEvidence).put(
            Body=hiredEvidence,
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
        db_conn.rollback()
        return str(e)

    print("Supporting documents sucessfully submitted.")
    return render_template('UploadSupportingDocumentsOutput.html', studentName=student[1], id=session['loggedInStudent'])

# View supporting documents
# View acceptance form


@app.route('/viewAcceptanceForm')
def viewAcceptanceForm():
  # Retrieve student's ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"supportingDocument/{student_id}/{student_id}_acceptanceForm"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


@app.route('/viewAcknowledgementForm')
def viewAcknowledgementForm():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"supportingDocument/{student_id}/{student_id}_acknowledgementForm"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


@app.route('/viewIndemnityLetter')
def viewIndemnityLetter():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"supportingDocument/{student_id}/{student_id}_indemnityLetter"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


@app.route('/viewSupportLetter')
def viewSupportLetter():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"supportingDocument/{student_id}/{student_id}_supportLetter"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)


@app.route('/viewHiredEvidence')
def viewHiredEvidence():
    # Retrieve student's ID
    student_id = session.get('loggedInStudent')

    if not student_id:
        return "Student not logged in."

    # Construct the S3 object key
    object_key = f"supportingDocument/{student_id}/{student_id}_hiredEvidence"

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
            # If the report does not exist, return a page with a message
            return render_template('no_report_found.html')
        else:
            return str(e)

    # Redirect the user to the URL of the PDF file
    return redirect(response)

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

    # Retrieve the cohort where student belongs to
    select_sql = "SELECT startDate, endDate FROM cohort WHERE cohortId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (cohort))
        cohort = cursor.fetchone()

        if not cohort:
            return "No such cohort details exists."

    except Exception as e:
        return str(e)

    # Retrieve start date and end date
    # Convert start_date_str and end_date_str into datetime objects
    start_date_str = str(cohort[0])
    end_date_str = str(cohort[1])

    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")

    # Calculate the report count for the student
    report_count = calculate_submission_count(start_date, end_date)

    # Loop and insert the details into the report table
    for i in range(1, report_count + 1):
        report_type = f'ProgressReport{i}' if i != report_count else 'FinalReport'

        # You can customize this insert SQL query based on your database schema
        insert_report_sql = "INSERT INTO report (submissionDate, reportType, status, late, remark, student) VALUES (%s, %s, %s, %s, %s, %s)"

        try:
            cursor.execute(insert_report_sql, (None, report_type,
                           'pending', 0, None, student_id))
            db_conn.commit()
        except Exception as e:
            db_conn.rollback()

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

            # Retrieve the cohort where student belongs to
            select_sql = "SELECT startDate, endDate FROM cohort c WHERE cohortId = %s"
            cursor = db_conn.cursor()
            cursor.execute(select_sql, (user[10]))
            cohort = cursor.fetchone()
            cursor.close()

            # Convert start_date_str and end_date_str into datetime.date objects
            start_date_str = str(cohort[0])
            end_date_str = str(cohort[1])
            start_date = datetime.date.fromisoformat(start_date_str)
            end_date = datetime.date.fromisoformat(end_date_str)

            #######################################################################
            # Retrieve supervisor details
            supervisor_query = "SELECT l.name, l.email FROM lecturer l, student s WHERE s.supervisor = l.lectId AND studentId = %s"
            cursor = db_conn.cursor()
            cursor.execute(supervisor_query, (user[0]))
            supervisor = cursor.fetchone()
            cursor.close()

            # Retrieve the company details
            company_query = "SELECT c.name, j.jobLocation, salary, jobPosition, jobDesc FROM company c, job j, companyApplication ca, student s WHERE c.companyId = j.company AND ca.student = s.studentId AND ca.job = j.jobId AND s.studentId = %s AND ca.`status` = 'approved'"
            cursor = db_conn.cursor()
            cursor.execute(company_query, (user[0]))
            companyDetails = cursor.fetchone()
            cursor.close()
            #######################################################################

            # Create a list to store all the retrieved data
            user_data = {
                'studentId': user[0],
                'studentName': user[1],
                'IC': user[2],
                'mobileNumber': user[3],
                'gender': user[4],
                'address': user[5],
                'email': user[6],
                'level': user[7],
                'programme': user[8],
                'cohort': user[10],
                'start_date': start_date,
                'end_date': end_date,
                # Default values if supervisor is not found
                'supervisor': supervisor if supervisor else ("N/A", "N/A"),
                # Default values if company details are not found
                'companyDetails': companyDetails if companyDetails else ("N/A", "N/A", "N/A", "N/A", "N/A")
            }

            # Set the loggedInStudent session
            session['loggedInStudent'] = user[0]

            # Redirect to the student home page with the user_data
            return render_template('studentHome.html', data=user_data)

        else:
            # User not found, login failed
            return render_template('LoginStudent.html', msg="Access Denied: Invalid Email or Ic Number")

# GWEE YONG SEAN
# Function to create a database connection context


def get_db_connection():
    customhost = 'employee.cgtpcksgf7rv.us-east-1.rds.amazonaws.com'
    customuser = 'aws_user'
    custompass = 'Bait3273'
    customdb = 'employee'

    return connections.Connection(
        host=customhost,
        port=3306,
        user=customuser,
        password=custompass,
        db=customdb
    )


@app.route("/displayJobFind", methods=['POST', 'GET'])
def displayAllJobs():
    # Get filter values from the form
    search_company = request.form.get('search-company', '')
    search_title = request.form.get('search-title', '')
    search_state = request.form.get('search-state', 'All')
    search_allowance = request.form.get('search-allowance', '1800')

    # Construct the base SQL query with a JOIN between the job and company tables
    select_sql = """
        SELECT j.*, c.name AS company_name
        FROM job j
        LEFT JOIN company c ON j.company = c.companyId
        WHERE 1
    """

    # Add filter conditions based on form inputs
    if search_company:
        select_sql += f" AND c.name LIKE '%{search_company}%'"

    if search_title:
        select_sql += f" AND j.jobPosition LIKE '%{search_title}%'"

    if search_state != 'All':
        select_sql += f" AND j.jobLocation LIKE '%{search_state}%'"

    if search_allowance:
        select_sql += f" AND j.salary <= {search_allowance}"

    # Add the condition to check the company's status
    select_sql += " AND c.status = 'activated'"

    # Add the condition to check numOfOperating greater than 0
    select_sql += " AND j.numOfOperating > 0"

    try:
        with get_db_connection() as db_conn:
            with db_conn.cursor() as cursor:
                cursor.execute(select_sql)
                jobs = cursor.fetchall()

                job_objects = []
                for job in jobs:
                    job_id = job[0]
                    publish_date = job[1]
                    job_type = job[2]
                    job_position = job[3]
                    qualification_level = job[4]
                    job_requirement = job[6]
                    job_location = job[7]
                    salary = job[8]
                    company_id = job[10]
                    company_name = job[12]  # Extracted from the JOINed column

                    # Generate the S3 image URL using custombucket and customregion
                    company_image_file_name_in_s3 = "comp-id-" + \
                        str(company_id)+"_image_file"
                    s3 = boto3.client('s3', region_name=customregion)
                    bucket_name = custombucket

                    response = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name,
                                'Key': company_image_file_name_in_s3},
                        ExpiresIn=1000  # Adjust the expiration time as needed
                    )
                    job_object = {
                        "job_id": job_id,
                        "publish_date": publish_date,
                        "job_type": job_type,
                        "job_position": job_position,
                        "qualification_level": qualification_level,
                        "job_requirement": job_requirement,
                        "job_location": job_location,
                        "salary": salary,
                        "company_name": company_name,
                        "company_id": company_id,
                        "image_url": response
                    }

                    job_objects.append(job_object)

        return render_template('SearchCompany.html', jobs=job_objects)

    except Exception as e:
        # Log the exception for debugging
        print(f"Error: {str(e)}")
        return "An error occurred while fetching job data."


@app.route("/displayJobDetails", methods=['POST', 'GET'])
def display_job_details():
    if request.method == 'POST':
        # Get the selected job_id from the form
        selected_job_id = request.form.get('transfer-id')

        apply_student_id = session.get('loggedInStudent')

        select_sql = """
        SELECT j.*, c.name AS company_name, i.name AS industry_name, c.email AS company_email, c.phone AS company_phone
        FROM job j
        LEFT JOIN company c ON j.company = c.companyId
        LEFT JOIN industry i on j.industry = i.industryId
        WHERE jobId =%s
        """
        cursor = db_conn.cursor()
        try:
            cursor.execute(select_sql, (selected_job_id,))
            job = cursor.fetchone()

            if not job:
                return "No such job exists."
        except Exception as e:
            return str(e)

        # Initialize job_objects as an empty list
        job_objects = []

        # Append job details to job_objects
        job_id = job[0]
        publish_date = job[1]
        job_type = job[2]
        job_position = job[3]
        qualification_level = job[4]
        job_description = job[5]
        job_requirement = job[6]
        job_location = job[7]
        salary = job[8]
        num_of_operate = job[9]
        company_id = job[10]
        company_name = job[12]  # Extracted from the JOINed column
        industry_name = job[13]
        company_email = job[14]
        company_phone = job[15]

        # Generate the S3 image URL using custombucket and customregion
        company_image_file_name_in_s3 = "comp-id-" + \
            str(company_id) + "_image_file"
        s3 = boto3.client('s3', region_name=customregion)
        bucket_name = custombucket

        response = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name,
                    'Key': company_image_file_name_in_s3},
            ExpiresIn=1000  # Adjust the expiration time as needed
        )

        job_object = {
            "job_id": job_id,
            "publish_date": publish_date,
            "job_type": job_type,
            "job_position": job_position,
            "qualification_level": qualification_level,
            "job_description": job_description,
            "job_requirement": job_requirement,
            "job_location": job_location,
            "salary": salary,
            "company_name": company_name,
            "company_id": company_id,
            "num_of_operate": num_of_operate,
            "industry_name": industry_name,
            "company_email": company_email,
            "company_phone": company_phone,
            "image_url": response
        }

        job_objects.append(job_object)

        job_applied = False  # Initialize as False by default

        # Check if the student has applied for this job
        check_application_sql = """
        SELECT COUNT(*) as total
        FROM companyApplication
        WHERE student = %s AND job = %s
        """

        cursor.execute(check_application_sql,
                       (apply_student_id, selected_job_id))
        application_count = cursor.fetchone()

        if application_count and application_count[0] > 0:
            job_applied = True

        return render_template('JobDetail.html', jobs=job_objects, job_applied=job_applied)

    return render_template('SearchCompany.html', jobs=job_objects)


@app.template_filter('replace_and_keep_hyphen')
def replace_and_keep_hyphen(s):
    return s.replace('-', '<br>-').replace('<br>-', '-', 1)


@app.route("/studentApplyCompany", methods=['POST', 'GET'])
def studentApplyCompany():

    id = session['loggedInStudent']

    # Create a cursor
    cursor = db_conn.cursor()

    try:
        # Get the search query from the request (if provided)
        search_query = request.args.get('search', '')

        # Get the total number of applications
        total_applications = get_total_applications(cursor, search_query)

        # Define the number of applications per page
        per_page = 6  # Adjust as needed

        # Get the current page from the request or default to 1
        current_page = request.args.get('page', default=1, type=int)

        # Calculate the total number of pages
        num_pages = (total_applications + per_page - 1) // per_page

        # Calculate the start and end indices for the current page
        start_index = (current_page - 1) * per_page
        end_index = start_index + per_page

        # Get the applications for the current page
        applications = get_applications(
            cursor, session['loggedInStudent'], per_page, start_index, search_query)

        return render_template("trackApplication.html", applications=applications, current_page=current_page, num_pages=num_pages, id=id)

    except Exception as e:
        # Handle exceptions here
        return "An error occurred: " + str(e)

    finally:
        cursor.close()


def get_total_applications(cursor, search_query):
    # Execute the SELECT COUNT(*) query to get the total row count
    select_sql = """
    SELECT COUNT(*) as total
    FROM companyApplication ca
    LEFT JOIN job j ON ca.job = j.jobId
    LEFT JOIN company c ON j.company = c.companyId
    WHERE ca.student=%s
    """

    if search_query:
        select_sql += " AND c.name LIKE %s"
        cursor.execute(
            select_sql, (session['loggedInStudent'], f"%{search_query}%"))
    else:
        cursor.execute(select_sql, (session['loggedInStudent'],))

    apply_result = cursor.fetchone()
    return apply_result[0]


def calculate_pagination(total, per_page):
    num_pages = (total + per_page - 1) // per_page
    current_page = request.args.get('page', 1, type=int)
    start_index = (current_page - 1) * per_page
    end_index = start_index + per_page
    return num_pages, current_page, start_index, end_index


def get_applications(cursor, student_id, per_page, start_index, search_query):
    select_application = """
    SELECT ca.*, c.name AS company_name, j.jobPosition AS job_position, j.jobLocation AS job_location
    FROM companyApplication ca
    LEFT JOIN job j ON ca.job = j.jobId
    LEFT JOIN company c ON j.company = c.companyId
    WHERE ca.student=%s
    """

    if search_query:
        select_application += " AND c.name LIKE %s"

    select_application += " LIMIT %s OFFSET %s"

    if search_query:
        cursor.execute(select_application, (student_id,
                       f"%{search_query}%", per_page, start_index))
    else:
        cursor.execute(select_application, (student_id, per_page, start_index))

    application_track = cursor.fetchall()

    application_objects = []
    for row in application_track:
        application_id = row[0]
        applyDateTime = row[1]
        status = row[2]
        student = row[3]
        job = row[4]
        company_name = row[5]
        job_position = row[6]
        job_location = row[7]

        application_object = {
            "application_id": application_id,
            "applyDateTime": applyDateTime,
            "status": status,
            "student": student,
            "job": job,
            "company_name": company_name,
            "job_position": job_position,
            "job_location": job_location
        }
        application_objects.append(application_object)

    return application_objects


@app.route("/applyCompany", methods=['POST'])
def applyCompany():
    try:
        # Get the selected job_id from the form
        apply_job_id = request.form.get('apply-job-id')
        apply_student_id = session['loggedInStudent']
        now = datetime.datetime.now()

        # Create a cursor
        cursor = db_conn.cursor()

        # Get the next available application ID (you may need to adjust this logic)
        cursor.execute("SELECT MAX(applicationId) FROM companyApplication")
        max_id = cursor.fetchone()[0]
        company_id = max_id + 1 if max_id is not None else 1

        # Insert the application record into the database
        insert_application_sql = """
        INSERT INTO companyApplication (applicationId, applyDateTime, status, student, job)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_application_sql, (company_id, now,
                       'pending', apply_student_id, apply_job_id))
        db_conn.commit()

    except Exception as e:
        db_conn.rollback()
    # Handle the exception if needed

    finally:
        cursor.close()

    # This line is outside the try-except block
    return redirect(url_for("studentApplyCompany"))


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

# DOWNLOAD FOCS_StudF06.pdf (Student Support Letter)


@app.route('/downloadStudF06', methods=['GET'])
def download_StudF06():
    id = session.get('loggedInStudent')

    select_sql = "SELECT * FROM student WHERE studentId = %s"
    cohort_sql = "SELECT startDate, endDate FROM cohort c WHERE cohortId = %s"
    cursor = db_conn.cursor()

    try:
        # Retrieve student data
        cursor.execute(select_sql, (id))
        student = cursor.fetchone()

        # Retrieve cohort data
        cursor.execute(cohort_sql, (student[10]))
        cohort = cursor.fetchone()

        db_conn.commit()

        # Format dates
        todayDate = datetime.datetime.now().strftime('%d-%B-%Y')
        startDate = cohort[0].strftime('%d-%B-%Y')
        endDate = cohort[1].strftime('%d-%B-%Y')

        # Prepare the data as a list
        data = {
            'todayDate': todayDate,
            'startDate': startDate,
            'endDate': endDate,
            'studentId': student[0],
            'studentName': student[1],
            'programme': student[8]
        }

    except Exception as e:
        db_conn.rollback()
        return str(e)

    # Render the HTML template with the data
    rendered_template = render_template('StudentSupportLetter.html', data=data)

    # Use pdfkit to generate the PDF
    html = HTML(string=rendered_template, base_url=request.url)
    pdf = html.write_pdf(presentational_hints=True)

    # Create a response object with the PDF data
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline;filename={id}_SupportLetter.pdf'

    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
