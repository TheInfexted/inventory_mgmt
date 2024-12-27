class Config:
    SECRET_KEY = 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://my_user:userpassword@localhost:3306/my_database'
    SQLALCHEMY_TRACK_MODIFICATIONS = False