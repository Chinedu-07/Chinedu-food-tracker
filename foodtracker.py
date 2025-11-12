import streamlit as st
import csv
import os

# -------------------- CONSTANTS --------------------
USER_DB = "users.csv"
CURRENCY_MAP = {
    "Nigeria": "₦",
    "United States": "$",
    "United Kingdom": "£",
    "Canada": "C$",
    "Ghana": "₵",
    "South Africa": "R",
    "India": "₹"
}

# -------------------- USER AUTH FUNCTIONS --------------------
def load_users():
    users = {}
    if os.path.exists(USER_DB):
        with open(USER_DB, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                country = row.get('country', 'Nigeria')  # default if missing
                users[row['email']] = {'name': row['name'], 'password': row['password'], 'country': country}
    return users

def save_user(name, email, password, country):
    file_exists = os.path.exists(USER_DB)
    with open(USER_DB, 'a', newline='') as file:
        fieldnames = ['name', 'email', 'password', 'country']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'name': name, 'email': email, 'password': password, 'country': country})

def verify_user(email, password):
    users = load_users()
    if email in users and users[email]['password'] == password:
        return True, users[email]
    return False, None

# -------------------- PRICE TRACKER FUNCTIONS --------------------
def load_prices(user_email):
    filename = f"{user_email}_prices.csv"
    prices = {}
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Handle old CSVs without new columns
                current = float(row.get('current_price', row.get('price', 0)))
                last = float(row.get('last_price', current))
                target = float(row.get('target_price', current))
                prices[row['item']] = {
                    'current_price': current,
                    'last_price': last,
                    'target_price': target
                }
    return prices

def save_prices(user_email, prices):
    filename = f"{user_email}_prices.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['item', 'current_price', 'last_price', 'target_price'])
        for item, data in prices.items():
            writer.writerow([item, data['current_price'], data['last_price'], data['target_price']])

def update_prices(user_email, new_prices):
    """Compare new prices, update CSV, return messages and alerts."""
    old_prices = load_prices(user_email)
    messages = []
    alerts = []
    for item, data in new_prices.items():
        new_price = data['current_price']
        target_price = data['target_price']
        last_price = old_prices.get(item, {}).get('current_price', new_price)
        
        # Determine status
        if new_price < last_price:
            msg = f"✅ {item} got cheaper: {last_price} → {new_price}"
        elif new_price > last_price:
            msg = f"⚠️ {item} increased: {last_price} → {new_price}"
        else:
            msg = f"🔹 {item} stayed the same: {new_price}"
        
        messages.append(msg)

        # Check alerts
        if new_price <= target_price:
            alerts.append(f"🚨 {item} has reached your target price: {new_price} ≤ {target_price}")

        # Update price record
        old_prices[item] = {
            'current_price': new_price,
            'last_price': last_price,
            'target_price': target_price
        }
    
    # Save updated prices
    save_prices(user_email, old_prices)
    return messages, alerts

# -------------------- STREAMLIT APP --------------------
st.set_page_config(page_title="Food Price Tracker", page_icon="🍎", layout="wide")
st.title("🍎 Sophisticated Food Price Tracker Bot")

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# -------------------- LOGOUT --------------------
if st.session_state.logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_info = {}
        st.rerun()

# -------------------- LOGIN / SIGNUP --------------------
if not st.session_state.logged_in:
    menu = st.sidebar.selectbox("Menu", ["Login", "Sign Up"])

    if menu == "Sign Up":
        st.subheader("Create a New Account")
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        country = st.selectbox("Country", list(CURRENCY_MAP.keys()))

        if st.button("Sign Up"):
            users = load_users()
            if email in users:
                st.warning("⚠️ Email already exists!")
            else:
                save_user(name, email, password, country)
                st.success(f"✅ Account created for {name}! Currency: {CURRENCY_MAP[country]}")
                st.info("You can now log in from the Login tab.")

    elif menu == "Login":
        st.subheader("Log In to Your Account")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            valid, user_info = verify_user(email, password)
            if valid:
                st.session_state.logged_in = True
                st.session_state.user_info = user_info
                st.session_state.user_info['email'] = email
                st.success(f"Welcome back, {user_info['name']}! 👋")
                st.rerun()
            else:
                st.error("❌ Invalid email or password.")

# -------------------- DASHBOARD --------------------
if st.session_state.logged_in:
    user = st.session_state.user_info
    currency = CURRENCY_MAP.get(user['country'], "$")
    st.subheader(f"Welcome, {user['name']}! Currency: {currency} ({user['country']})")
    st.markdown("---")
    st.subheader("📊 Track Your Food Prices with Alerts")

    # Multi-item input in columns (mobile-friendly)
    st.info("Enter items, current price, and target price. Add as many as you like!")
    new_prices = {}
    num_items = st.number_input("Number of items to track", min_value=1, max_value=20, value=2, step=1)

    for i in range(1, num_items+1):
        col1, col2, col3 = st.columns(3)
        with col1:
            item = st.text_input(f"Item {i} Name", key=f"item{i}")
        with col2:
            price = st.number_input(f"Current Price", min_value=0.0, max_value=10000.0, value=0.0, step=0.01, key=f"price{i}")
        with col3:
            target = st.number_input(f"Target Price", min_value=0.0, max_value=10000.0, value=price, step=0.01, key=f"target{i}")
        if item.strip() != "":
            new_prices[item.strip()] = {'current_price': price, 'target_price': target}

    if st.button("Track Prices"):
        messages, alerts = update_prices(user['email'], new_prices)
        st.subheader("📢 Price Tracker Results")
        for msg in messages:
            # color coding
            if msg.startswith("✅"):
                st.success(msg)
            elif msg.startswith("⚠️"):
                st.warning(msg)
            else:
                st.info(msg)
        
        if alerts:
            st.subheader("🚨 Alerts")
            for alert in alerts:
                st.error(alert)

    # Display current tracked prices in expandable section
    st.markdown("---")
    with st.expander("💾 Your Current Tracked Prices"):
        current_prices = load_prices(user['email'])
        for item, data in current_prices.items():
            price_change = data['current_price'] - data['last_price']
            change_symbol = "🔹"
            if price_change < 0:
                change_symbol = "✅"
            elif price_change > 0:
                change_symbol = "⚠️"
            st.write(f"{item}: {currency}{data['current_price']:.2f} ({change_symbol} last: {currency}{data['last_price']:.2f}, target: {currency}{data['target_price']:.2f})")
