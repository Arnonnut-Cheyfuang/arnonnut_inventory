import mysql.connector
try:
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
    print("Connection is established and the test query was executed successfully")
    print(cursor.fetchall())
    cursor.close()
    conn.close()
except mysql.connector.Error as err:
    print(f"Error: {err}")