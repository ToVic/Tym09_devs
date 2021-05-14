#%%
import pandas as pd
from pandas_profiling import ProfileReport
from pymongo import MongoClient

username = '*'
password = '*'
client = MongoClient(f'mongodb+srv://{username}:{password}@cluster0.mtfak.mongodb.net/myFirstDatabase')
db = client.reality
data = pd.DataFrame(list(db.currentdata.find()))