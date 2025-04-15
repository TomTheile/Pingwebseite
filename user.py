from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """User class for Flask-Login"""
    
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        
    @staticmethod
    def get(user_id):
        """Get a user by ID"""
        if user_id == 1:
            return PREDEFINED_USER
        return None
        
    @staticmethod
    def find_by_username(username):
        """Find a user by username"""
        if username == PREDEFINED_USER.username:
            return PREDEFINED_USER
        return None
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)


# Create the predefined user
PREDEFINED_USER = User(
    id=1, 
    username="Red_Angels",
    password_hash=generate_password_hash("t2344T78")
)