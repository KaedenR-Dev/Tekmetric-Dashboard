from getpass import getpass

from auth import create_user

username = input("Username: ")

password = getpass("Password: ")

create_user(username, password)

print("Administrator account created.")