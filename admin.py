import mysql.connector
import hashlib
import sys
import pandas as pd
import time
import getpass as g
import secrets

# Global variables for session state
user_name = ""
location = ""
conn = None
cursor = None
attempt = 0
locked = 0

def log_action(username, action_type, description):
    """
    Log user actions to the logs table for auditing.
    """
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
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    try:
        curso.execute("""
            INSERT INTO logs (username, action_type, description)
            VALUES (%s, %s, %s)
        """, (username, action_type, description))
        con.commit()
    except Exception as log_err:
        print(f"Failed to log action: {log_err}")

def login(username, password):
    """
    Authenticate user credentials and set session variables.
    """
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

        # Fetch user record
        curso.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = curso.fetchone()
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
    if user:
        # Hash password with pepper and compare
        password += user["pepper"]
        hash_obj = hashlib.sha256(password.encode('utf-8'))
        password = hash_obj.hexdigest()

        if (password == user["password"]) and (user["privilege"] == "read_write"):
            user_name = user["full_name"]
            location = user["current_location_id"]
            log_action(username, "LOGIN", f"Login successful for user {username}")
            con.close()
            curso.close()
            return True
        else:
            print("Invalid Login.\nMake sure you are using the correct username and password.\nOr your account is not provisioned to access this system.\n")
            log_action(username, "LOGIN_FAIL", f"Incorrect password attempt for user {username}")
            attempt+=1
            time.sleep(1.5)
            return False
    else:
        print("User not found.")
        log_action(username, "LOGIN_FAIL", f"Login failed: user {username} not found")
        attempt+=1
        time.sleep(1.5)
        return False

def welcome_page():
    """
    Display welcome/login prompt and handle login attempts and lockout.
    """
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
        password = g.getpass("Enter password: ")
        if login(username, password):
            print(f"Login successful! Welcome {user_name}!")
            # Connect with higher privilege after login
            conn = mysql.connector.connect(
                host='ec2-3-25-95-9.ap-southeast-2.compute.amazonaws.com',
                user='app_user',
                password='App_password123!',
                database='stockdb',
                ssl_ca='server_cert.pem',
                ssl_disabled=False
            )
            cursor = conn.cursor(dictionary=True)
            break
        else:
            print("Login failed. Please try again.")

def scan_item():
    """
    Scan an RFID tag and update its location and stock levels.
    """
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
            log_action(user_name, "UPDATE", f"RFID {rfid} ({item_name}) scanned and moved to location {location}")
            break
        except Exception as err:
            log_action(user_name, "ERROR", f"Failed to scan RFID {rfid}: {err}")
            print(f"Error: {err}")

def check_stock_level():
    """
    Display current stock levels for all items and locations.
    """
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
    """
    Show details for a selected item, including supplier info.
    """
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
            if option < 0 or option > len(lists)-1:
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
    """
    Locate an item and display its location and address.
    """
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
    """
    Export inventory data to an Excel file.
    """
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
        log_action(user_name, "EXPORT", "Exported inventory data to Excel")
    except Exception as err:
        print(f"Connection Error!\n{err}\n")
        log_action(user_name, "ERROR", f"Export failed: {err}")

def manage_inventory():
    """
    Menu for managing items and suppliers (CRUD operations).
    """
    global cursor, conn, user_name
    while True:
        print("\n" + "="*20)
        print("Inventory & Supplier Management")
        print("="*20)
        print("1. Add Item\n2. Edit Item\n3. Delete Item")
        print("4. Add Supplier\n5. Edit Supplier\n6. Delete Supplier")
        print("7. Back to Main Menu")

        try:
            choice = int(input("Choose an option (1–7): "))
            if choice not in range(1, 8):
                raise ValueError("Option out of range.")
        except Exception as err:
            print(f"Invalid input! Please enter a number between 1 and 7.\nError: {err}\n")
            continue

        match choice:
            case 1:
                # Add new item
                try:
                    cursor.execute("SELECT supplier_id, supplier_name FROM suppliers")
                    suppliers = cursor.fetchall()
                    if not suppliers:
                        print("No suppliers found. Please add a supplier first.")
                        continue
                    print("\nAvailable Suppliers:")
                    for s in suppliers:
                        print(f"ID: {s['supplier_id']} | Name: {s['supplier_name']}")
                    item_name = input("Item name: ")
                    description = input("Description: ")
                    supplier_id = input("Enter Supplier ID from list above: ")
                    cursor.execute("INSERT INTO items (item_name, description, supplier_id) VALUES (%s, %s, %s)", 
                                   (item_name, description, supplier_id))
                    conn.commit()
                    print("Item added successfully.")
                    log_action(user_name, "INSERT", f"Added item '{item_name}' with supplier ID {supplier_id}")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to add item: {err}")

            case 2:
                # Edit existing item
                try:
                    cursor.execute("SELECT item_id, item_name FROM items")
                    items = cursor.fetchall()
                    if not items:
                        print("No items found.")
                        continue
                    print("\nAvailable Items:")
                    for i in items:
                        print(f"ID: {i['item_id']} | Name: {i['item_name']}")
                    item_id = input("Enter Item ID to update: ")
                    new_name = input("New Item Name: ")
                    new_desc = input("New Description: ")
                    cursor.execute("UPDATE items SET item_name = %s, description = %s WHERE item_id = %s",
                                   (new_name, new_desc, item_id))
                    conn.commit()
                    print("Item updated successfully.")
                    log_action(user_name, "UPDATE", f"Updated item ID {item_id} to '{new_name}'")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to update item ID {item_id}: {err}")

            case 3:
                # Delete item
                try:
                    cursor.execute("SELECT item_id, item_name FROM items")
                    items = cursor.fetchall()
                    if not items:
                        print("No items found.")
                        continue
                    print("\nAvailable Items:")
                    for i in items:
                        print(f"ID: {i['item_id']} | Name: {i['item_name']}")
                    item_id = input("Enter Item ID to delete: ")
                    cursor.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
                    conn.commit()
                    print("Item deleted successfully.")
                    log_action(user_name, "DELETE", f"Deleted item ID {item_id}")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to delete item ID {item_id}: {err}")

            case 4:
                # Add new supplier
                try:
                    name = input("Supplier name: ")
                    contact = input("Contact info: ")
                    cursor.execute("INSERT INTO suppliers (supplier_name, contact_info) VALUES (%s, %s)", 
                                   (name, contact))
                    conn.commit()
                    print("Supplier added successfully.")
                    log_action(user_name, "INSERT", f"Added supplier '{name}'")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to add supplier: {err}")

            case 5:
                # Edit supplier
                try:
                    cursor.execute("SELECT supplier_id, supplier_name FROM suppliers")
                    suppliers = cursor.fetchall()
                    if not suppliers:
                        print("No suppliers found.")
                        continue
                    print("\nAvailable Suppliers:")
                    for s in suppliers:
                        print(f"ID: {s['supplier_id']} | Name: {s['supplier_name']}")
                    sid = input("Enter Supplier ID to update: ")
                    new_name = input("New Supplier Name: ")
                    new_contact = input("New Contact Info: ")
                    cursor.execute("UPDATE suppliers SET supplier_name = %s, contact_info = %s WHERE supplier_id = %s",
                                   (new_name, new_contact, sid))
                    conn.commit()
                    print("Supplier updated successfully.")
                    log_action(user_name, "UPDATE", f"Updated supplier ID {sid} to '{new_name}'")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to update supplier ID {sid}: {err}")

            case 6:
                # Delete supplier
                try:
                    cursor.execute("SELECT supplier_id, supplier_name FROM suppliers")
                    suppliers = cursor.fetchall()
                    if not suppliers:
                        print("No suppliers found.")
                        continue
                    print("\nAvailable Suppliers:")
                    for s in suppliers:
                        print(f"ID: {s['supplier_id']} | Name: {s['supplier_name']}")
                    sid = input("Enter Supplier ID to delete: ")
                    cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (sid,))
                    conn.commit()
                    print("Supplier deleted successfully.")
                    log_action(user_name, "DELETE", f"Deleted supplier ID {sid}")
                except Exception as err:
                    print(f"Error: {err}")
                    log_action(user_name, "ERROR", f"Failed to delete supplier ID {sid}: {err}")

            case 7:
                print("Returning to main menu...\n")
                break

def view_logs():
    """
    Display all logs for auditing purposes.
    """
    global conn, cursor
    try:
        cursor.execute("SELECT * FROM logs")
        logs = cursor.fetchall()
        if not logs:
            print("No logs found.")
            return
        print(f"{'Log ID':<10} {'User':<30} {'Action Type':<30} {'Description':<70} {'Timestamp':<50}")
        print("-" * 200)
        for log in logs:
            print(f"{log['log_id']:<10} {log['username']:<30} {log['action_type']:<30} {log['description']:<70} {str(log['timestamp']):<20}")
        print("-" * 200)
    except Exception as err:
        print(f"Error: {err}\n")

def register():
    """
    Register a new user with read_only privilege.
    """
    global conn, cursor
    try:
        username = input("Choose a username: ")
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            print("Username already exists. Please try another.")
            return

        password = g.getpass("Choose a password: ")
        full_name = input("Enter your full name: ")
        location_id = input("Enter your default location ID: ")

        pepper = secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        hashed_pw = hashlib.sha256((password + pepper).encode('utf-8')).hexdigest()

        cursor.execute("""
            INSERT INTO users (username, password, pepper, full_name, current_location_id, privilege)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, hashed_pw, pepper, full_name, location_id, 'read_only'))

        conn.commit()
        print("Registration successful. Await provisioning to gain access.")
        log_action(username, "REGISTER", f"Registered user {username} with read_only privilege.")
        cursor.close()
        conn.close()

    except Exception as err:
        print(f"Registration failed: {err}")
        log_action("SYSTEM", "REGISTER_FAIL", f"Failed to register user {username}: {err}")

def main_menu():
    """
    Main menu for user actions after login.
    """
    global user_name
    print(f"Welcome! {user_name}")
    print("How can I help you today?\n")
    while True:
            option = input("1. Scan item\n2. Check stock level\n3. View item details\n4. Locate an item\n5. Export Stock Data\n6. Manage Inventory and Suppliers\n7. View Logs\n8. Register a staff\n9. Quit\nYour selection: ")
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
                    manage_inventory()
                case 7:
                    view_logs()
                case 8:
                    register()
                case 9:
                    print("Exiting....\n")
                    conn.close()
                    cursor.close()
                    print("="*20)
                    print(f"Goodbye, see you again soon! {user_name}\n")
                    print("="*20)
                    sys.exit()
            print("Could I offer you any more help?\n")
            print("="*20)

if __name__ == "__main__":
    # Entry point: show welcome/login and then main menu
    welcome_page()
    main_menu()