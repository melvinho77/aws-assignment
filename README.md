# Install flask on EC2 
# Either add "sudo" before all commands or use "sudo su" first
# Amazon Linux 2023

#!/bin/bash
yum update -y
yum install git -y
git clone https://github.com/melvinho77/aws-assignment.git
cd aws-assignment
yum install python-pip -y
pip3 install flask pymysql boto3
python3 app.py
