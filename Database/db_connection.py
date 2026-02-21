from flask_mysqldb import MySQL

def init_db(app):
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = '8055'
    app.config['MYSQL_DB'] = 'gtl_auth'

    mysql = MySQL(app)
    return mysql