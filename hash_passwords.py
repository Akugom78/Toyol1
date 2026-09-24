# hash_passwords.py
import bcrypt
import yaml

def hash_password(plain_text_password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_text_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def generate_hash_interactive():
    print("--- ATC RAG Password Hash Generator ---")
    username = input("Enter username (e.g., controller2): ").strip()
    name = input("Enter full name (e.g., Siti Controller): ").strip()
    email = input("Enter email (e.g., siti@atc.local): ").strip()
    plain_password = input("Enter plain text password: ").strip()
    
    hashed_pw = hash_password(plain_password)
    
    print("\n✅ Copy and paste this block into your config.yaml under 'credentials.usernames':")
    print("-" * 50)
    print(f"    {username}:")
    print(f"      email: {email}")
    print(f"      name: {name}")
    print(f"      password: {hashed_pw}")
    print("-" * 50)

if __name__ == "__main__":
    generate_hash_interactive()