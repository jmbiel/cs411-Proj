# CS 411 Project -- Spring 2018

## Group Members:
    1. Nico Bermudez
    2. Zirui Liu
    3. Max Biel
    4. Rahul Jain

## Project Ideas:
### 1) Nightlife Recommendations:
    Goal: Reccommend bars, restaurants, clubs to a user based on his/her location and preferences which 
    include serveral factors:
        1. Likeliness of crowd
        2. Likeliness of line
        3. Reviews

    How: Utilize uber movement data to determine which places are in highly frequented areas. Use yelp API 
    to access reviews - potentially do lexical analysis to look for key words that the user prefers.  Use 
    Boston public dataset of all bars, restuarants, and clubs - this is a static dataset that may be used
    for join operations at some point in the development of the project.

### 2) Investment Portfolio Recommendations:
    Goal: Profile the user to determine their level of risk adversity.  Based on this, recommend investment
    portfolios and show live feed of how each one is trending.

    How: Use facebook and amazon to profile the user and determine their level of risk adversity.  Use Yahoo
    Finance to recommend a portfolio balanced with stocks, short term reserves, and bonds.

### 3) Combined Music Platform:
    Goal: To create a centralized platform for all existing music services.  Allow a user to connect all
    subscription services, and create playlists which include music from all of them.

    How: Use the numerous web-APIs included in all of the services (Soundcloud, Spotify, Apple Music,
    Amazon Music) - similar to how the sonos system might do this.
