CAMPUS HARDWARE INVENTORY SYSTEM - FINAL FIXED VERSION

Run:
  pip install -r requirements.txt
  python app.py

Open:
  http://127.0.0.1:5000

DEFAULT ADMIN LOGIN
  Username: admin
  Password: Admin@123

IMPORTANT LOGIN FIX
  The app now initializes/repairs the built-in admin account every time it starts.
  This means an old or partially-created SQLite database will not leave the admin
  account with an invalid password.

  Existing inventory is preserved. Seed items are inserted only when missing.

Optional manual repair:
  python reset_admin.py

FEATURES
  - Minimalist purple/blue responsive UI
  - Login and registration
  - Dashboard overview
  - Inventory Panel with search/category filter
  - Admin add/edit/delete inventory
  - User borrowing requests
  - Admin Approvals for borrowing and pending returns
  - Password request submitted by users and approved/rejected by admin
  - 35+ sample hardware items including Raspberry Pi Pico
