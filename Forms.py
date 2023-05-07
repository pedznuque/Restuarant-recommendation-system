import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for



app = Flask(__name__)






def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if len(username) > 9:
            error = 'Username should not be longer than 9 letters.'
            return render_template('login.html', error=error)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if the email already exists in the database
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        email_exists = c.fetchone()
        
        # Check if the username already exists in the database
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        username_exists = c.fetchone()
        
        if email_exists:
            # Email already exists in the database
            error = 'Email already exists. Please use a different email.'
            return render_template('register.html', error=error)
        elif username_exists:
            # Username already exists in the database
            error = 'Username already exists! Please choose a different username.'
            return render_template('register.html', error=error)
        else:
            # Add user to the database
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            conn.commit()
            conn.close()
            success = 'You have successfully registered!'
            return redirect(url_for('login'))
    
    return render_template('register.html')






def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if user is admin
        c.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (username, password))
        admin = c.fetchone()
        
        # If user is not admin, check if they are a regular user
        if not admin:
            c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()
            
        conn.close()
        
        if admin:
            session['username'] = admin[1]
            session['is_admin'] = True
            return render_template('index.html')
        elif user:
            session['username'] = user[1]
            session['is_admin'] = False
            return render_template('index.html')
        else:
            error = 'Invalid Username or Password'
            
    return render_template('login.html', error=error)





def logout():
    session.pop('username', None)
    return redirect(url_for('index'))
