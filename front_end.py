import mysql.connector
import hashlib
user = ""
location = ""
def login(username, password):
    conn = mysql.connector.connect(
    host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
    user='readonly_user',
    password='Readonly_pass789!',
    database='stockdb',
    ssl_ca='server_cert.pem',
    ssl_disabled=False
    )

    cursor = conn.cursor(dictionary=True)

    # Use parameterised query to avoid SQL injection
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        password+= user["pepper"]
        hash_obj = hashlib.sha256(password.encode('utf-8'))
        password = hash_obj.hexdigest()
        if password == user["password"]:
            user = user["full_name"]
            location = user["current_location_id"]
            return True
        else:
            print("Incorrect password.")
            return False
    else:
        print("User not found.")
        return False

    cursor.close()
    conn.close()

def welcome_page():
    print("Welcome to stock tracker!\nPlease Log in\n*NOTE: To register, please contact head quater to be provisioned*\n")
    username = input("Enter username: ")
    password = input("Enter password: ")
    while True:
        if(login(username, password)):
            print("Login successful!")
            break
        else:
            print("Login failed. Please try again.")
            username = input("Enter username: ")
            password = input("Enter password: ")
def scan_item():
    rfid = input("Enter RFID code: ")
    
def main_menu():
    print(f"Welcome to the main menu! {user}")
    print("How can I help you today?")
    option = input("1.Scan item\n2.Check stcok level\n3.View item details\n")
if __name__ == "__main__":
    welcome_page()