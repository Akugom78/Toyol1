# auth_manager.py
import yaml
import bcrypt
from yaml.loader import SafeLoader
import os

CONFIG_PATH = 'config.yaml'

def load_config():
    """Loads the config.yaml file."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        return yaml.load(file, Loader=SafeLoader)

def save_config(config):
    """Saves the updated config back to config.yaml."""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False, sort_keys=False)

def hash_password(plain_password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def add_user(username: str, name: str, email: str, plain_password: str):
    """Adds a new user to the config.yaml."""
    config = load_config()
    
    if username in config['credentials']['usernames']:
        return False, "Username already exists."
    
    config['credentials']['usernames'][username] = {
        'email': email,
        'name': name,
        'password': hash_password(plain_password)
    }
    
    save_config(config)
    return True, f"User '{username}' added successfully!"

def delete_user(username: str):
    """Deletes a user from the config.yaml."""
    config = load_config()
    
    if username not in config['credentials']['usernames']:
        return False, "User not found."
    if username == 'admin':
        return False, "Cannot delete the primary admin account."
    
    del config['credentials']['usernames'][username]
    save_config(config)
    return True, f"User '{username}' deleted successfully."

def get_all_users():
    """Returns a list of all usernames and their names."""
    config = load_config()
    users = []
    for uname, details in config['credentials']['usernames'].items():
        users.append({"username": uname, "name": details.get('name', 'N/A'), "email": details.get('email', 'N/A')})
    return users