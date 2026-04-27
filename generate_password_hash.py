#!/usr/bin/env python3
import bcrypt

def generate_password_hash(password):
    """Generate a bcrypt hash for the given password"""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against a bcrypt hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

if __name__ == "__main__":
    # Test passwords and their hashes
    passwords = {
        'admin123': 'admin',
        'hr123': 'hr',
        'finance123': 'finance',
        'password123': 'it_employee',
        'password123': 'department_user'
    }
    
    print("Generating password hashes:")
    print("=" * 50)
    
    for password, username in passwords.items():
        hashed = generate_password_hash(password)
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Hash: {hashed}")
        
        # Verify the hash
        is_valid = verify_password(password, hashed)
        print(f"Verification: {'PASS' if is_valid else 'FAIL'}")
        print("-" * 50)
    
    # Generate specific hash for hr123
    print("\nSpecific hash for hr123:")
    hr_hash = generate_password_hash('hr123')
    print(f"UPDATE users SET password_hash = '{hr_hash}' WHERE username = 'hr';")
    
    print("\nSpecific hash for finance123:")
    finance_hash = generate_password_hash('finance123')
    print(f"UPDATE users SET password_hash = '{finance_hash}' WHERE username = 'finance';")
    
    print("\nSpecific hash for password123:")
    password_hash = generate_password_hash('password123')
    print(f"UPDATE users SET password_hash = '{password_hash}' WHERE username IN ('it_employee', 'department_user');")
