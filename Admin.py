import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for



app = Flask(__name__)
app.secret_key = 'your_secret_key'



def user_list():
    # Retrieve list of all users
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email, password, profile_pic_url FROM users ORDER BY id')

        users = c.fetchall()

    # Render template with user list
    return render_template('user_list.html', users=users)





def user_profile(user_id):
    # Retrieve user information and reviews
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        c.execute('SELECT id, resto_id, comment, date FROM reviews WHERE username = ? ORDER BY date DESC', (user[1],))
        reviews = c.fetchall()

    # Render template with user profile and reviews
    return render_template('user_profile.html', user=user, reviews=reviews)




def delete_user():
    user_id = request.form['user_id']
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    return redirect(url_for('user_list'))





def delete_review_admin(review_id):
    if not session['is_admin']:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401
    
    # Delete the review from the database
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        conn.commit()

    # Return a JSON response indicating success
    return jsonify({'success': True})
