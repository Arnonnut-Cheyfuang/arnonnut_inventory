import mysql.connector

conn = mysql.connector.connect(
    host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
    user='admin_user',
    password='Admin_password456!',
    database='stockdb',
    ssl_ca='server_cert.pem',
    ssl_disabled=False
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM items")
print(cursor.fetchall())