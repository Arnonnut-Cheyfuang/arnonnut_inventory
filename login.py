import mysql.connector
import hashlib

def login(username, password):
    # Connect to the database
    
    conn = mysql.connector.connect(
    host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
    user='admin_user',
    password='Admin_password456!',
    database='stockdb',
    ssl_ca='server_cert.pem',
    ssl_disabled=False
    )

    cursor = conn.cursor(dictionary=True)

    # Use parameterised query to avoid SQL injection
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        password+= user["salt"]
        hash_obj = hashlib.sha256(password.encode('utf-8'))
        password = hash_obj.hexdigest()
        if password == user["password"]:
            print("Login successful!")
            return True
        else:
            print("Incorrect password.")
            return False
    else:
        print("User not found.")
        return False

    cursor.close()
    conn.close()

    if __name__ == "__main__":
        username = input("Enter username: ")
        password = input("Enter password: ")
        login(username, password)