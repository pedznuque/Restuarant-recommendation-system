import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import os
from werkzeug.utils import secure_filename






app = Flask(__name__)
app.secret_key = 'your_secret_key'



app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])








def profile():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    error = None

    # Handle form submission
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if old password is correct
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (session['username'], old_password))
        user = c.fetchone()
        
        # Check if new username is already taken
        c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
        existing_user = c.fetchone()
        conn.close()

        if user is None:
            error = 'Incorrect password'
        elif existing_user is not None:
            error = 'Username already taken'
        else:
            # Update username and/or password
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            if new_username:
                c.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user[0]))
                session['username'] = new_username
            if new_password:
                c.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user[0]))
            conn.commit()
            conn.close()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('home'))


    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if 'username' in session:
        # Get user's current profile picture URL
        c.execute("SELECT profile_pic_url FROM users WHERE username = ?", (session['username'],))
        result = c.fetchone()
        if result is not None:
            profile_pic_url = result[0]
        else:
            profile_pic_url = 'https://cdn-icons-png.flaticon.com/512/1144/1144709.png'
    elif 'is_admin' in session:
        profile_pic_url = 'https://cdn-icons-png.flaticon.com/512/1144/1144709.png'
    else:
        profile_pic_url = 'https://cdn-icons-png.flaticon.com/512/1144/1144709.png'
            
    if profile_pic_url is None:
        profile_pic_url = 'https://cdn-icons-png.flaticon.com/512/1144/1144709.png'

    return render_template('Profile_setting.html', error=error, profile_pic_url=profile_pic_url)






def profile_pic():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Get user's current profile picture URL
    c.execute("SELECT profile_pic_url FROM users WHERE username = ?", (session['username'],))
    profile_pic_url = c.fetchone()[0]
    
    if request.method == 'POST':
        # Update user's profile picture URL
        profile_pic = request.files['profile_pic']
        if profile_pic:
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_pic_url = url_for('static', filename='uploads/' + filename)
            c.execute("UPDATE users SET profile_pic_url = ? WHERE username = ?", (profile_pic_url, session['username']))
            conn.commit()
            conn.close()

            return redirect(url_for('profile'))
       

    return render_template('profile_pic.html', profile_pic_url=profile_pic_url)


