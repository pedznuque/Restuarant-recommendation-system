import sqlite3
from difflib import get_close_matches
from typing import Any
import pandas as pd
import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'


app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])



@app.route('/')
def index():
    return render_template('index.html')




#--------------------------These are the tables for the sqlite3 Database-----------------------------------   

conn = sqlite3.connect('users.db')
c = conn.cursor()


c.execute('''CREATE TABLE IF NOT EXISTS admin
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password TEXT NOT NULL);''')

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              email TEXT NOT NULL UNIQUE,
              password TEXT NOT NULL,
              profile_pic_url TEXT);''')

              

c.execute('''CREATE TABLE IF NOT EXISTS reviews
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              resto_id INTEGER NOT NULL,
              comment TEXT NOT NULL,
              date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (username) REFERENCES users (username),
              FOREIGN KEY (resto_id) REFERENCES restaurants (id));''')


c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              resto_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              location TEXT NOT NULL,
              cuisine_type TEXT NOT NULL,
              image_url TEXT,
              FOREIGN KEY (username) REFERENCES users (username),
              FOREIGN KEY (resto_id) REFERENCES restaurants (resto_id));''')

c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('Eunice', 'Grace'))
conn.commit()

conn.commit()
conn.close()


#----------------------------For Administrator Dashboard-------------------------------------------


@app.route('/users')
def user_list():
    # Retrieve list of all users
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, email, password, profile_pic_url FROM users ORDER BY id')

        users = c.fetchall()

    # Render template with user list
    return render_template('user_list.html', users=users)


@app.route('/users/<int:user_id>')
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


@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_id = request.form['user_id']
    
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    return redirect(url_for('user_list'))







@app.route('/profile', methods=['GET', 'POST'])
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
            return redirect(url_for('base'))



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






@app.route('/account', methods=['GET', 'POST'])
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
       

    return render_template('Profile_pic.html', profile_pic_url=profile_pic_url)








#-----------------These are functions that allow the user to log in, regiseter and log-out----------------------------------- 

@app.route('/register', methods=['GET', 'POST'])
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


@app.route('/login', methods=['GET', 'POST'])
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
            return render_template('home.html')
        elif user:
            session['username'] = user[1]
            session['is_admin'] = False
            return render_template('home.html')
        else:
            error = 'Invalid Username or Password'
            
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))











#--------------------------It loads the datasets first and it preprocess the data----------------------------------- 


# Load the restaurants data into a DataFrame
restaurants_df = pd.read_csv(r'/workspaces/Restuarant-recommendation-system/datasets/zomato.csv')


# Convert the cuisine and location columns into a single combined column
restaurants_df['combined'] = restaurants_df['cuisines'] + ' ' + restaurants_df['location']

# Convert the combined column into a TF-IDF vector representation
vectorizer = TfidfVectorizer()
tfidf = vectorizer.fit_transform(restaurants_df['combined'].astype(str))












#----------------------------these are the interface and user input of the users and process them----------------


# this is the page of the base
@app.route('/home.html')
def base(): 
    # sugesstion function to display them in the search input
    location_suggestions = restaurants_df['location'].unique().tolist()
    cuisines_suggestions = restaurants_df['cuisines'].unique().tolist()
    search_suggestions = restaurants_df['Resto_name'].unique().tolist()
    return render_template('home.html', location_suggestions=location_suggestions, cuisines_suggestions=cuisines_suggestions, search_suggestions=search_suggestions )




# this is a function that allow the user to get their preference and process them 
@app.route('/recommend', methods=['POST'])
def recommend():
    user_location = request.form['location']
    selected_cuisines = request.form.getlist('cuisine')
    user_cuisine = ' '.join(selected_cuisines)
    user_price_range = request.form['price_range']
 

    restaurants_df_filtered = restaurants_df.copy()
    
    # Convert the cuisine and location columns into a single combined column
    restaurants_df_filtered['combined'] = restaurants_df_filtered['cuisines'] + ' ' + restaurants_df_filtered['location']
    
    # Convert the combined column into a TF-IDF vector representation
    tfidf = vectorizer.transform(restaurants_df_filtered['combined'].astype(str))
    
    # Create a TF-IDF vector for the user's input
    user_input = vectorizer.transform([user_cuisine + ' ' + user_location])

    # Calculate the cosine similarity between the user input and all restaurants
    similarities = cosine_similarity(user_input, tfidf).flatten()

    # Sort the restaurants by cosine similarity, in descending order
    restaurants_df_filtered['similarity'] = similarities
    recommended_restaurants = restaurants_df_filtered.sort_values('similarity', ascending=False)


    # Define a mapping from string labels to numerical price range values
    price_range_labels = {
        'Inexpensive': 1,
        'Moderate': 2,
        'Expensive': 3,
        'Very Expensive': 4,
    }

    # Filter the recommended restaurants by the user's price range preference
    user_price_range = price_range_labels[user_price_range]
    recommended_restaurants = recommended_restaurants[recommended_restaurants['price_range'] == user_price_range]

    #Filter the recommended restaurants by the user's rate preference

    user_rate = request.form.get('rate_slider')
    if user_rate:
         recommended_restaurants = recommended_restaurants[recommended_restaurants['aggregate_rating'] >= float(user_rate)]



    #Show the top 15 recommended restaurants or the closest value if the number of recommended restaurants is less than 15 
    n = min(30, len(recommended_restaurants))
    recommended_restaurants = recommended_restaurants[:n]

    #Get the name, address, and image URL of each restaurant
    Resto_names = recommended_restaurants['Resto_name'].tolist()
    locations = recommended_restaurants['location'].tolist()
    addresses = recommended_restaurants['address'].tolist()
    ratings = recommended_restaurants['rating'].tolist()
    image_urls = recommended_restaurants['image_url'].tolist()
    cuisine_types = recommended_restaurants['cuisines'].tolist()
    cost_for_twos = recommended_restaurants['average_cost_for_two'].tolist()
    Resto_ids = recommended_restaurants['resto_id'].tolist()

    #Create a list of dictionaries, where each dictionary represents a restaurant
    restaurants = [{'Resto_id': Resto_id, 'cost_for_two': cost_for_two, 'cuisine_type': cuisine_type, 'rating': rating, 'address': address, 'Resto_name': Resto_name, 'location': location, 'image_url': image_url} for Resto_id, cost_for_two, cuisine_type, rating, address, Resto_name, location, image_url in zip(Resto_ids, cost_for_twos, cuisine_types, ratings, addresses, Resto_names, locations, image_urls)]

    #Pass the list of dictionaries to the template
    return render_template('recommend.html', restaurants=restaurants)







# allow the user to search for specific restaurants and process them
@app.route('/search')
def search():
    query = request.args.get('query')

    # Find the restaurants in the DataFrame that match the search query
    restaurant_matches = restaurants_df[restaurants_df['Resto_name'].str.contains(query, case=False)]

    if restaurant_matches.empty:
        # If no exact matches were found, try to find the nearest match
        restaurant_names = restaurants_df['Resto_name'].tolist()
        nearest_name = get_close_matches(query, restaurant_names, n=1, cutoff=0.6)
        if nearest_name:
            # Redirect to the search page with the nearest match
            return redirect(url_for('search', query=nearest_name[0]))
        else:
            # Redirect to the "not found" page
            return render_template('not_found.html')
    else:
        # Convert the cuisine and location columns into a single combined column
        restaurant_matches['combined'] = restaurant_matches['cuisines'] + ' ' + restaurant_matches['location']

        # Convert the combined column into a TF-IDF vector representation
        tfidf = vectorizer.transform(restaurant_matches['combined'].astype(str))

        # Calculate the cosine similarity between the search query and all restaurants
        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, tfidf).flatten()

        # Sort the restaurants by cosine similarity, in descending order
        restaurant_matches['similarity'] = similarities
        restaurant_matches = restaurant_matches.sort_values('similarity', ascending=False)

        # Get the top 30 matching restaurants
        restaurant_matches = restaurant_matches.head(30)

        # Get the name, address, and image URL of each restaurant
        Resto_names = restaurant_matches['Resto_name'].tolist()
        locations = restaurant_matches['location'].tolist()
        addresses =restaurant_matches['address'].tolist()
        ratings = restaurant_matches['rating'].tolist()
        image_urls = restaurant_matches['image_url'].tolist()
        cuisine_types = restaurant_matches['cuisines'].tolist()
        cost_for_twos = restaurant_matches['average_cost_for_two'].tolist()
        Resto_ids = restaurant_matches['resto_id'].tolist()
        #Create a list of dictionaries, where each dictionary represents a restaurant
        restaurants = [{'Resto_id': Resto_id, 'cost_for_two': cost_for_two, 'cuisine_type': cuisine_type, 'rating': rating, 'address': address, 'Resto_name': Resto_name, 'location': location, 'image_url': image_url} for Resto_id, cost_for_two, cuisine_type, rating, address, Resto_name, location, image_url in zip(Resto_ids, cost_for_twos, cuisine_types, ratings, addresses, Resto_names, locations, image_urls)]
    

        # Pass the search results to the template
        return render_template('recommend.html', restaurants=restaurants)













#------this is the last page were user clicked their desire restaurant from the results-----------------


# this is function that show more details and allow the user to comment and bookmark
@app.route('/details', methods=['GET', 'POST'])
def details():
    name = request.args.get('name')
    

    # Find the restaurant in the DataFrame that matches the given name
    restaurant = restaurants_df[restaurants_df['resto_id'] == name].iloc[0]



    # Create a dictionary of restaurant details
    restaurant_details = {
        'name': restaurant['Resto_name'],
        'location': restaurant['location'],
        'address': restaurant['address'],
        'rating': restaurant['rating'],
        'large_image_url': restaurant['large_image_url'],
        'image_url': restaurant['image_url'],
        'cuisine_type': restaurant['cuisines'],
        'resto_id': restaurant['resto_id'],
        'latitude': restaurant['latitude'],
        'longitude': restaurant['longitude']
      
    }

    # Handle form submission
    if request.method == 'POST':
        # Get the comment from the form data
        comment = request.form['comment']

        # Insert the comment into the database
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO reviews (username, resto_id, comment) VALUES (?, ?, ?)',
                      (session['username'], restaurant_details['resto_id'], comment))
            conn.commit()

        # Return a response indicating success
        return 'success'

    

  # Get the reviews for the restaurant
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, comment, date FROM reviews WHERE resto_id = ? ORDER BY date DESC', (restaurant_details['resto_id'],))
        reviews = c.fetchall()

      
        # Fetch the profile pic URLs for each user who posted a review
        for i, review in enumerate(reviews):
            c.execute('SELECT profile_pic_url FROM users WHERE username = ?', (review[1],))
            profile_pic_url = c.fetchone()[0]
            reviews[i] = review + (profile_pic_url,)
        



     # Check if the current user has bookmarked the restaurant
    is_bookmarked = False
    if 'username' in session:
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute('''SELECT 1 FROM bookmarks
                         WHERE username = ? AND resto_id = ?''', (session['username'], restaurant_details['resto_id']))
            if c.fetchone() is not None:
                is_bookmarked = True



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



    # Pass the restaurant details and reviews to the template
    return render_template('details.html', restaurant=restaurant_details, reviews=reviews, is_bookmarked=is_bookmarked, profile_pic_url=profile_pic_url) 


@app.route('/delete_review/<name>', methods=['POST'])
def delete_review(name):
    review_id = request.form['review_id']

    # Delete the review from the database
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM reviews WHERE id = ? AND username = ?', (review_id, session['username']))

        conn.commit()

    # Return a JSON response indicating success
    return jsonify({'success': True})



    

@app.route('/delete_review_admin/<review_id>', methods=['POST'])
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






@app.route('/bookmark', methods=['POST'])
def bookmark():
    resto_id = request.form['resto_id']
    name = request.form['name']
    location = request.form['location']
    cuisine_type = request.form['cuisine_type']
    image_url = request.form['image_url']

    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO bookmarks (username, resto_id, name, location, cuisine_type, image_url) VALUES (?, ?, ?, ?, ?, ?)',
                  (session['username'], resto_id, name, location, cuisine_type, image_url))
        conn.commit()

    return 'success'

   
@app.route('/bookmarks')
def bookmarks():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Connect to the database and execute the query
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT resto_id, name, location, cuisine_type, image_url
                     FROM bookmarks
                     WHERE username = ?''', (session['username'],))
        bookmarks = c.fetchall()

    # Render the template with the list of bookmarks
    return render_template('bookmarks.html', bookmarks=bookmarks)
    




@app.route('/bookmarks/delete/<string:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    # Connect to the database and execute the query to delete the bookmark
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('''DELETE FROM bookmarks
                     WHERE username = ? AND resto_id = ?''', (session['username'], bookmark_id))

    # Return a success message
    return jsonify({'message': 'Bookmark deleted successfully'})




    


if __name__ == '__main__':
    app.run(debug=True)
