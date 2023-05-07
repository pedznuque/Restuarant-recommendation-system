import sqlite3
from Database import tables
from Profile_setting import profile, profile_pic
from Admin import user_list, user_profile, delete_user
from Forms import login, logout, register


from datetime import datetime
from difflib import get_close_matches
from typing import Any
import pandas as pd
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random
from datetime import datetime








app = Flask(__name__)
app.secret_key = 'your_secret_key'







# THIS IS THE STARTER PAGE OF THE SYSTEM
@app.route('/')
def index():
    return render_template('index.html')



tables()


# THESE ARE THE ROUTES FOR PROFILE_SETTING"S FUNCTIONS
app.route('/profile', methods=['GET', 'POST'])(profile)
app.route('/account', methods=['GET', 'POST'])(profile_pic)



# THESE ARE THE ROUTES FOR ADMIN'S FUNCTIONS
app.route('/users')(user_list)
app.route('/users/<int:user_id>')(user_profile)
app.route('/delete_user', methods=['POST'])(delete_user)



# THESE THE ROUTES FOR LOG IN AND REGISTER FORMS
app.route('/register', methods=['GET', 'POST'])(register)
app.route('/login', methods=['GET', 'POST'])(login)
app.route('/logout')(logout)












# Load the restaurants data into a DataFrame
restaurants_df = pd.read_csv(r'/workspaces/Restuarant-recommendation-system/dataset/zomato.csv')


# Convert the cuisine and location columns into a single combined column
restaurants_df['combined'] = restaurants_df['cuisines'] + ' ' + restaurants_df['location']

# Convert the combined column into a TF-IDF vector representation
vectorizer = TfidfVectorizer()
tfidf = vectorizer.fit_transform(restaurants_df['combined'].astype(str))



# Function to randomly select n unique restaurants from a DataFrame for a given cuisine
def get_random_restaurants(df, cuisine, n=5):
    cuisine_restaurants = df[df['cuisines'] == cuisine]
    unique_restaurants = cuisine_restaurants['Resto_name'].unique()
    if len(unique_restaurants) < n:
        # Adjust the sample size if the number of unique restaurants is less than n
        n = len(unique_restaurants)
    cuisine_restaurants = cuisine_restaurants.drop_duplicates(subset='Resto_name').sample(n=n, replace=False)
    return cuisine_restaurants

@app.route('/feed', methods=['GET'])
def feed():
    # Filter out cuisines with 1 or 2 restaurants
    filtered_cuisines = []
    for cuisine in restaurants_df['cuisines'].unique():
        cuisine_restaurants = restaurants_df[restaurants_df['cuisines'] == cuisine]
        unique_restaurants = cuisine_restaurants['Resto_name'].nunique()
        if unique_restaurants > 2:
            filtered_cuisines.append(cuisine)

    
    # Randomly select three cuisines from the updated filtered list
    cuisines = random.sample(filtered_cuisines, 20)
    feed_data = {}

    for cuisine in cuisines:
        # Get randomly selected restaurants for the cuisine
        cuisine_restaurants = get_random_restaurants(restaurants_df, cuisine, n=10)

        # Create a list of restaurant details for the cuisine
        restaurant_details = []
        for _, row in cuisine_restaurants.iterrows():
            restaurant_detail = {
                'name': row['Resto_name'],
                'location': row['location'],
                'address': row['address'],
                'rating': row['rating'],
                'large_image_url': row['large_image_url'],
                'image_url': row['image_url'],
                'cuisine_type': row['cuisines'],
                'resto_id': row['resto_id'],
                'latitude': row['latitude'],
                'longitude': row['longitude']
            }
            restaurant_details.append(restaurant_detail)

        # Store the cuisine's restaurants in the feed_data dictionary
        feed_data[cuisine] = restaurant_details

    # Extract unique values from the "cuisine" column
    cuisine_select = restaurants_df['cuisines'].unique()


    # Pass the feed data and updated cuisines list to the template
    return render_template('feed.html', feed_data=feed_data, cuisine_select=cuisine_select)





# this is a function that allow the user to get their preference and process them 
@app.route('/recommend', methods=['POST'])
def recommend():
    user_location = request.form['location']
    selected_cuisines = request.form['cuisine']
    user_price_range = request.form['price_range']



    # Create a TF-IDF vector for the user's input
    user_input = vectorizer.transform([selected_cuisines + ' ' + user_location])

    # Calculate the cosine similarity between the user input and all restaurants
    similarities = cosine_similarity(user_input, tfidf).flatten()

    # Sort the restaurants by cosine similarity, in descending order
    restaurants_df['similarity'] = similarities
    recommended_restaurants = restaurants_df.sort_values('similarity', ascending=False)


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
