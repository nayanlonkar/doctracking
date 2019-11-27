import re


def usernameValidation(username):
    if re.match(r'[A-Za-z0-9@#$%^&+=]{4, 80}', username):
        return True
    else:
        return False


def passwordValidation(password):
    if re.match(r'[A-Za-z0-9@#$%^&+=_]{4, 80}', password):
        return True
    else:
        return False

# length should be atleast 4 and atmost 80
# username and password can have special characters {@, #, $, %, ^, &, +, _, =}
