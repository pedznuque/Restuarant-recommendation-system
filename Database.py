
import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for




app = Flask(__name__)
app.secret_key = 'your_secret_key'







def tables():
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

    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('Pedro', 'Pogi'))
    conn.commit()

    conn.commit()
    conn.close()
