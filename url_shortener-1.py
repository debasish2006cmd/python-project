import json
import os
import random
import string
from datetime import datetime

# Storage file
DB_FILE = "url_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def shorten_url(long_url):
    db = load_db()
    # Check if already shortened
    for code, data in db.items():
        if data["original_url"] == long_url:
            print(f"\n[INFO] URL already shortened!")
            print(f"  Short URL : http://short.ly/{code}")
            print(f"  Original  : {long_url}")
            return

    # Generate unique code
    code = generate_code()
    while code in db:
        code = generate_code()

    db[code] = {
        "original_url": long_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "clicks": 0
    }
    save_db(db)
    print(f"\n[SUCCESS] URL Shortened!")
    print(f"  Short URL : http://short.ly/{code}")
    print(f"  Original  : {long_url}")

def redirect_url(short_code):
    db = load_db()
    if short_code in db:
        db[short_code]["clicks"] += 1
        save_db(db)
        print(f"\n[REDIRECT] Redirecting to: {db[short_code]['original_url']}")
        print(f"  Clicks so far: {db[short_code]['clicks']}")
    else:
        print(f"\n[ERROR] Short code '{short_code}' not found!")

def list_urls():
    db = load_db()
    if not db:
        print("\n[INFO] No URLs stored yet.")
        return
    print(f"\n{'CODE':<10} {'CLICKS':<8} {'CREATED':<22} ORIGINAL URL")
    print("-" * 80)
    for code, data in db.items():
        print(f"{code:<10} {data['clicks']:<8} {data['created_at']:<22} {data['original_url']}")

def delete_url(short_code):
    db = load_db()
    if short_code in db:
        del db[short_code]
        save_db(db)
        print(f"\n[SUCCESS] Deleted short code: {short_code}")
    else:
        print(f"\n[ERROR] Short code '{short_code}' not found!")

def main():
    print("=" * 50)
    print("       URL SHORTENER - Python Project")
    print("=" * 50)
    while True:
        print("\nOptions:")
        print("  1. Shorten a URL")
        print("  2. Redirect (access) a short URL")
        print("  3. List all URLs")
        print("  4. Delete a short URL")
        print("  5. Exit")
        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            url = input("Enter long URL: ").strip()
            if url:
                shorten_url(url)
        elif choice == "2":
            code = input("Enter short code (e.g. aB3xYz): ").strip()
            redirect_url(code)
        elif choice == "3":
            list_urls()
        elif choice == "4":
            code = input("Enter short code to delete: ").strip()
            delete_url(code)
        elif choice == "5":
            print("\nGoodbye!")
            break
        else:
            print("[ERROR] Invalid choice. Try again.")

if __name__ == "__main__":
    main()
