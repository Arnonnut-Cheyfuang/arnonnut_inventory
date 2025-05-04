# Application Documentation: arnonnut\_inventory

## 1. Introduction

**arnonnut\_inventory** is a secure, Python-based inventory tracking application that interacts with a MySQL backend hosted on an Amazon EC2 instance. The system allows users to:

* Log in securely
* Track item stock levels
* View item details and supplier information
* Scan items using RFID-based inputs (or manual entry simulation)

This document explains how to set up, run, and use the application.

## 2. System Requirements

* **Python Version:** 3.10+
* **MySQL Server:** Hosted on EC2 (SSL-enabled)
* **Hardware:** RFID scanner (optional), standard laptop

## 3. Installation Guide

### 3.1 Clone the Repository

```bash
git clone <https://github.com/Arnonnut-Cheyfuang/arnonnut_inventory>
cd arnonnut_inventory
```

### 3.2 Create Virtual Environment & Install Requirements

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 4. Running the Application

### 4.1 Start the Front-End

```bash
python front_end.py
```

Follow the prompt for user options: login, register, view items, etc.

### 4.2 Admin Script (For adding items or testing)

```bash
python admin.py
```

### 4.3 Test SQL Connection

```bash
python sql_test.py
```

## 5. User Guide

### 5.1 Login / Register

* Enter your username and password
* Login attempts are rate-limited and locked on repeated failures
* Registeration can be only be done with the admin privilege

### 5.2 Viewing Items

* See list of items
* Select to view full item + supplier details

### 5.3 Scanning Items

* (Future enhancement) Use RFID scanner
* Simulated manually for now

## 6. Administrator Guide

### 6.1 Creating Users

Use MySQL or admin script to register users

* `admin_user` has select, insert, update, delete access
* `readonly_user` has only select and update access

### 6.2 Managing Inventory

* Add, update, or remove items through admin interface or SQL directly


## 7. Security Measures

* Passwords hashed with SHA-256 and a per-user pepper
* SSL enforced between client and EC2-hosted MySQL server
* Role-based access using MySQL privileges
* Locked accounts after multiple failed login attempts
* The SQL Queries are parameterised, so it has protetion against SQL injection

## 8. Troubleshooting

| Issue                      | Solution                                                                          |
| -------------------------- | --------------------------------------------------------------------------------- |
| SSL error on DB connection | Check `server-cert.pem` path and `require_secure_transport`                       |
| Login always fails         | Confirm pepper logic and password hash matches DB                                 |
| Module missing             | Ensure virtual environment is activated and use `pip install -r requirements.txt` |

## 9. Appendix

### 9.1 DB Schema Outline

* `users(username, password, pepper, full_name, current_location_id)`
* `items(item_id, item_name, description, supplier_id)`
* `suppliers(supplier_id, supplier_name, contact_info)`

### 9.2 API / CLI

* Future enhancements could include Flask API for mobile/cloud integration
