
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask import render_template, request, flash, redirect, jsonify
from flask import Flask, render_template, request, flash
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)
app.secret_key = 'cc'  # Set your secret key here

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


@app.route('/login_company')
def login_company():
    return render_template('LoginCompany.html')


@app.route('/register_student')
def register_student():
    return render_template("RegisterStudent.html")


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

        flash("Registration successful!", "success")  # Flash a success message

        # Redirect back to the registration page with a success message
        return render_template("RegisterStudent.html")

    except Exception as e:
        flash(f"Registration failed: {str(e)}",
              "error")  # Flash an error message
        db_conn.rollback()

        # Redirect back to the registration page with an error message
        return render_template("RegisterStudent.html")

    finally:
        cursor.close()

@app.route("/about", methods=['POST'])
def about():
    return render_template('www.tarc.edu.my')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name,
                       last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(
                Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client(
                's3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('EditCompanyProfile.html', name=emp_name)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
