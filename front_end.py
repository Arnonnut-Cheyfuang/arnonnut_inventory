import mysql.connector
import hashlib

user_name = ""
location = ""
conn = None
cursor = None

def login(username, password):
    global conn, cursor, user_name, location

    conn = mysql.connector.connect(
        host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
        user='readonly_user',
        password='Readonly_pass789!',
        database='stockdb',
        ssl_ca='server_cert.pem',
        ssl_disabled=False
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        password += user["pepper"]
        hash_obj = hashlib.sha256(password.encode('utf-8'))
        password = hash_obj.hexdigest()

        if password == user["password"]:
            user_name = user["full_name"]
            location = user["current_location_id"]
            return True
        else:
            print("Incorrect password.")
            return False
    else:
        print("User not found.")
        return False

def welcome_page():
    global conn, cursor
    print("Welcome to stock tracker!\nPlease Log in\n*NOTE: To register, please contact head quater to be provisioned*\n")
    username = input("Enter username: ")
    password = input("Enter password: ")

    while True:
        if login(username, password):
            print(f"Login successful! Welcome {user_name}!")
            conn = mysql.connector.connect(
                host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
                user='inventory_mover',
                password='Strong_Password1234!',
                database='stockdb',
                ssl_ca='server_cert.pem',
                ssl_disabled=False
            )
            cursor = conn.cursor(dictionary=True)
            break
        else:
            print("Login failed. Please try again.")
            username = input("Enter username: ")
            password = input("Enter password: ")

def scan_item():
    global cursor, location
    while True:
        try:
            rfid = input("Enter RFID Tag ID: ")
            cursor.execute("""
                SELECT r.item_id, r.current_location_id, i.item_name
                FROM rfid_tags r
                JOIN items i ON r.item_id = i.item_id
                WHERE r.rfid_tag_id = %s
            """, (rfid,))
            result = cursor.fetchone()

            if not result:
                print(f"RFID {rfid} not found!")
                return

            item_id = result['item_id']
            old_location_id = result['current_location_id']
            item_name = result['item_name']
            print(f"Scanned {item_name} (Item ID {item_id})\n Item's previous location : {old_location_id} current location {location}")
            # Update RFID location
            cursor.execute(
                    "UPDATE rfid_tags SET current_location_id = %s, status = 'In Stock' WHERE rfid_tag_id = %s",
                    (location, rfid)
            )
            #Decrease old stock
            cursor.execute(
                    "UPDATE stock_levels SET quantity = quantity - 1 WHERE item_id = %s AND location_id = %s",
                    (item_id, old_location_id)
                )
            #Increase new stock
            cursor.execute(
                """
                INSERT INTO stock_levels (item_id, location_id, quantity)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE quantity = quantity + 1
                """,
                (item_id, location)
            )
            conn.commit()
            print(f"RFID {rfid} {item_name} scanned successfully.")
            break
        except Exception as err:
            print(f"Error: {err}")

def check_stock_level():
    global cursor
    try:
        cursor.execute("""
        SELECT 
            i.item_id,
            i.item_name,
            s.location_id AS current_location_id,
            s.stock_level
        FROM items i
        JOIN stock s ON i.item_id = s.item_id
        """)
        results = cursor.fetchall()
        if not results:
            print("No stock data found.")
            return

        print(f"{'Item ID':<10} {'Item Name':<30} {'Location':<15} {'Level':<10}")
        print("-" * 70)
        for row in results:
            print(f"{row['item_id']:<10} {row['item_name']:<30} {row['current_location_id']:<15} {row['stock_level']:<10}")
    except Exception as err:
        print(f"Error: {err}")

def view_item_details():
    global conn,cursor
    cursor.execute("SELECT i.item_id, i.item_name, i.description, i.supplier_id, s.supplier_name, s.contact_info FROM items i INNER JOIN  suppliers s on i.supplier_id = s.supplier_id")
    lists = cursor.fetchall()
    if not lists:
        print("No items found")
        return
    while True:
        for index, row in enumerate(lists, start=1):
            print(f"{index}. {row['item_name']}")
        try:
            option = input("Please select an item to view details (1-{}): ".format(len(lists)))
            option = int(option)-1
            if option < 0 or option > len(lists):
                raise ValueError("Please enter a number in the item list")
        except Exception as err:
            print(f"Please supply a valid input\nError: {err}")
            continue
        print("="*20)
        print(f"Showing item {lists[option]['item_name']}")
        print("-"*20)
        selected = lists[option]
        for key, value in selected.items():
            print(f"{key}: {value}")
        print("="*20 + "\n" + "="*20)
        print("1. View another item\n2. Back to main menu")
        quit = False
        while True:
            ops = input("Please select an option: ")
            try:
                ops = int(ops)
                if ops == 1:
                    print("="*20)
                    break
                elif ops == 2:
                    quit = True
                    print("="*20)
                    break
                else:
                    raise ValueError("Please enter a number")
            except Exception as err:
                print(f"Please supply a valid input\nError: {err}")
        if quit:
            break
def locaete():
    global conn, cursor
    try:
        cursor.execute("SELECT i.item_id, i.item_name, l.location_name, l.address from items i INNER JOIN stock_levels s ON i.item_id=s.item_id INNER JOIN locations l on l.location_id = s.location_id;")
        results = cursor.fetchall()
        if not results:
            print("No stock data found.")
            return
    except Exception as err:
        print(f"Error: {err}")
def main_menu():
    global user_name
    print(f"Welcome to the main menu! {user_name}")
    print("How can I help you today?")
    while True:
            option = input("1. Scan item\n2. Check stock level\n3. View item details\n")
            option = int(option)

if __name__ == "__main__":
    welcome_page()
    view_item_details()