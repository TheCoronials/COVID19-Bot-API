# COVID19-Bot-API

## Requirements Setup

Install the Python Requirements using pip:

```
pip install -r requirements.txt
```

## Automatic Database Setup and Data Seeding

The Creation of the in memory database as well as the seeding of test data is currently tied into the app’s bootstrap code. 
This means that simply running the main python file will setup and seed the in memory database. 

## Manual Database Setup

The Coronials project uses a sqlite database with the URI of 'sqlite:///coronials-collection.db'

### Creating the sqlite database

In order to create the In Memory Database you will need to run the database_setup script. Navigate to the repo directory:

```
cd repo
```

Run the database_setup script to create the database and tables from the defined models:

```
python database_setup.py
```
