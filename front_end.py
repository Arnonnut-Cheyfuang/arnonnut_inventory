import mysql.connector
import hashlib
import sys
import pandas as pd
import time

user_name = ""
location = ""
conn = None
cursor = None
attempt = 0
locked = 0

def login(username, password):
    global conn, cursor, user_name, location, attempt, locked
    try:
        con = mysql.connector.connect(
            host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
            user='readonly_user',
            password='Readonly_pass789!',
            database='stockdb',
            ssl_ca='server_cert.pem',
            ssl_disabled=False
        )
        curso = con.cursor(dictionary=True)

        curso.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = curso.fetchone()
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    if user:
        password += user["pepper"]
        hash_obj = hashlib.sha256(password.encode('utf-8'))
        password = hash_obj.hexdigest()

        if password == user["password"]:
            user_name = user["full_name"]
            location = user["current_location_id"]
            con.close()
            curso.close()
            return True
        else:
            print("Incorrect password.")
            attempt+=1
            time.sleep(1.5)
            return False
    else:
        print("User not found.")
        attempt+=1
        time.sleep(1.5)
        return False

def welcome_page():
    global conn, cursor, attempt, locked
    print("="*20)
    print("Welcome to stock tracker!\nPlease Log in\n*NOTE: To register, please contact head quater to be provisioned*\n")
    print("="*20)

    while True:
        if attempt >= 5:
            locked+=1
            wait_time = 300 * locked
            print("*"*20)
            print(f"Too many log in attempts! System is locked for {wait_time // 60} minutes. Countdown:")
            for remaining in range(wait_time, 0, -1):
                mins, secs = divmod(remaining, 60)
                timer = f"{mins:02d}:{secs:02d}"
                print(f"\rUnlocks in: {timer}", end="")
                time.sleep(1)
            print("\n"+ "="*20)
            print("System unlocked")
            print("="*20)
            attempt = 0
        username = input("Enter username: ")
        password = input("Enter password: ")
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
            l.location_name AS "Current Location",
            s.quantity
        FROM items i
        JOIN stock_levels s ON i.item_id = s.item_id
        INNER JOIN locations l ON s.location_id=l.location_id
        """)
        results = cursor.fetchall()
        if not results:
            print("="*20)
            print("No stock data found.")
            print("="*20)
            return

        print(f"{'Item ID':<10} {'Item Name':<30} {'Location':<15} {'Level':<10}")
        print("-" * 70)
        for row in results:
            print(f"{row['item_id']:<10} {row['item_name']:<30} {row['Current Location']:<15} {row['quantity']:<10}")
    except Exception as err:
        print(f"Error: {err}\n")

def view_item_details():
    global conn,cursor
    try:
        cursor.execute("SELECT i.item_id, i.item_name, i.description, i.supplier_id, s.supplier_name, s.contact_info FROM items i INNER JOIN  suppliers s on i.supplier_id = s.supplier_id")
        lists = cursor.fetchall()
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    if not lists:
        print("No items found")
        return
    while True:
        for index, row in enumerate(lists, start=1):
            print(f"{index}. {row['item_name']}")
        try:
            option = input("Please select an item to view details (1-{}): \n".format(len(lists)))
            option = int(option)-1
            if option < 0 or option > len(lists):
                raise ValueError("Please enter a number in the item list")
        except Exception as err:
            print(f"Please supply a valid input\nError: {err}\n")
            continue
        print("="*20)
        print(f"Showing item {lists[option]['item_name']}")
        print("-"*20)
        selected = lists[option]
        for key, value in selected.items():
            print(f"{key}: {value}")
        print("="*20 + "\n" + "="*20)
        print("1. View another item\n2. Back to main menu\n")
        quit = False
        while True:
            ops = input("Please select an option: \n")
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
def locate():
    global conn, cursor
    try:
        cursor.execute("SELECT i.item_id, i.item_name, l.location_name, l.address from items i INNER JOIN stock_levels s ON i.item_id=s.item_id INNER JOIN locations l on l.location_id = s.location_id;")
        lists = cursor.fetchall()
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    if not lists:
        print("No stock data found.\n")
        return
    while True:
        for index, row in enumerate(lists, start=1):
            print(f"{index}. {row['item_name']}")
        try:
            option = input("Please select an item to locate (1-{}):\n ".format(len(lists)))
            option = int(option)-1
            if option < 0 or option > len(lists):
                raise ValueError("Please enter a number in the item list\n")
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
        print("1. View another item\n2. Back to main menu\n")
        quit = False
        while True:
            ops = input("Please select an option: \n")
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
                    raise ValueError("Please enter a number\n")
            except Exception as err:
                print(f"Please supply a valid input\nError: {err}\n")
        if quit:
            break
        
def export():
    global conn
    try:
        query = """SELECT i.item_id, i.item_name, i.description, l.location_name, sl.quantity, s.supplier_name, s.contact_info 
                FROM items i INNER JOIN  suppliers s on i.supplier_id = s.supplier_id INNER JOIN stock_levels sl ON i.item_id=sl.item_id 
                INNER JOIN locations l ON  l.location_id = sl.location_id
                """
        df = pd.read_sql(query, conn)
        df.to_excel("inventory_export.xlsx", index=False)
        print("="*20)
        print("Exported successfully to inventory_export.xlsx")
        print("="*20)
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    
def main_menu():
    global user_name
    print(f"Welcome! {user_name}")
    print("How can I help you today?\n")
    while True:
            option = input("1. Scan item\n2. Check stock level\n3. View item details\n4. Locate an item\n5. Export Stock Data\n6. Quit\nYour selection: ")
            print("="*20)
            try:
                option = int(option)
                if option not in range(1,7):
                    raise ValueError("Selected value is not in the option\n")
            except Exception as err:
                print(f"Please input a valid choice!\nError: {err}\n")
                print("="*20)
            match option:
                case 1:
                    scan_item()
                case 2:
                    check_stock_level()
                case 3:
                    view_item_details()
                case 4:
                    locate()
                case 5:
                    export()
                case 6:
                    print("Exiting....\n")
                    conn.close()
                    cursor.close()
                    print("="*20)
                    print(f"Goodbye, see you again soon! {user_name}\n")
                    print("="*20)
                    sys.exit()
            print("Could I offer you any more help?\n")
if __name__ == "__main__":
    welcome_page()
    main_menu()