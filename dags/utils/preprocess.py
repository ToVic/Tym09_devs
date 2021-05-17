import pandas as pd
import numpy as np
from airflow.providers.mongo.hooks.mongo import MongoHook
from sklearn.impute import SimpleImputer
import category_encoders as ce
import re 
import unicodedata

COLS_TO_DROP = ['floor_area',
                'floor_max',
                'address',
                'title',
                'city',
                'size',
                'street',
                'description',
                'source',
                'date_updated']


### helper functions
# normalize unicode characters
def normalize_unicode(row):
    return unicodedata.normalize('NFKD', row)


# ziskej část prahy (1, 12, 20, 4...)
def get_prague_part_number(row):
    prague = re.search(r'(Praha)(\s)()(\d*)', row)
    if prague is not None:
        prague = prague.group(0)
    return prague


# pocet pokoju
def get_number_of_rooms(row):
    if 'Garsoniéra' in str(row):
        n_rooms = 1
    elif 'Ostatní' in str(row):
        n_rooms = np.nan
    else:
        n_rooms = str(row)[:1]
    return n_rooms

# get floor number
def get_floor_number(row):
    floor = re.search(r'([-\d]+)', str(row))
    if floor is not None:
        floor = floor[0]
    return floor

# set commas to dots
def set_comma_to_dot(row):
    if isinstance(row, str):
        row = row.replace(',', '.')
    return row

# sets string to lower (if its a string) and strips off whitespace
def set_lower_and_strip(row):
    if isinstance(row, str):
        row = row.strip().lower()
    return row

# fills NaNs with False, sets string to lower (if its a string)
def lower_and_numerize(df, column):
    df[column] = df[column].fillna(False)
    df[column] = df[column].apply(lambda x: x.lower() if isinstance(x, str) else x)

# returns: False if string is "ne"; bool if its already bool; True if its any string other than "ne" 
# (e.g. size of balcony means there is balcony)
def booleanize_column(df, column):
    df[column] = df[column].apply(lambda x: x if isinstance(x, bool) else False if x == 'ne' else True)

# drops any flat with unpaid anuity mention
def drop_anuity(df):
    return df.loc[~df['description'].str.contains('nesplacen[áoué ]+anuit', regex = True), :]


def prepare_data(default_args):
    print('PREPARING DATA...')

    mongo = MongoHook(conn_id='mongo_reality')
    df = pd.DataFrame(list(mongo.find(
        mongo_collection=default_args['mongo_current_collection'],
        query={},
        mongo_db=default_args['mongo_dbname']
    )))
    extra_features = pd.DataFrame(list(mongo.find(
        mongo_collection=default_args['mongo_extrafeatures_collection'],
        query={},
        mongo_db=default_args['mongo_dbname']
    ))).drop(columns=["_id"])

    # set index as link
    df.set_index('_id', inplace=True)
    
    # normalize and get prague part number
    df['address'] = df['address'].apply(normalize_unicode)
    df['city_part_number'] = df.address.apply(get_prague_part_number)
    df['city_part_number'].replace({'Praha ': np.nan, 'Prana\n': np.nan}, inplace=True)
    
    # convert size to rooms & kitchen
    df.dropna(subset=['size'], inplace=True)
    df['rooms'] = df['size'].apply(get_number_of_rooms)
    df['kitchen'] = df['size'].apply(lambda x: False if 'kk' in str(x) else True)
    
    # drop columns with unpaid anuity
    df = drop_anuity(df)
    
    # drop unneeded cols    
    df = df.drop(columns=COLS_TO_DROP)
    
    # rename categories, lower etc.
    df['building_type'] = df['building_type'].replace({'Cihla': 'cihlová',
                                                       'Cihlová': 'cihlová',
                                                       'Panel': 'panelová',
                                                       'Panelová': 'panelová',
                                                       'Smíšená': 'smíšená',
                                                       'Skeletová': 'skeletová',
                                                       'Kamenná': 'kamenná',
                                                       'Montovaná': 'montovaná'})
    
    df['state'] = df['state'].apply(set_lower_and_strip)
    df['state'] = df['state'].replace({'udržovaný': 'dobrý',
                                       'dobrý stav': 'dobrý',
                                       've výstavbě (hrubá stavba)': 've výstavbě'})
    
    df['equipment'] = df['equipment'].apply(set_lower_and_strip)
    df['equipment'] = df['equipment'].fillna(False)
    df['equipment'] = df['equipment'].replace({'částečně zařízený': 'částečně',
                                                       'nezařízený': 'nevybavený',
                                                       'zařízený': 'vybavený',
                                                       'ne': 'nevybavený',
                                                       'ano': 'vybavený',
                                                       True: 'vybavený',
                                                       False: 'nevybavený',
                                                       'null': 'nevybavený'})
    
    # fill nans    
    for column in ['balcony', 'basement', 'elevator', 'terrace', 'loggia', 'garage']:
        lower_and_numerize(df, column)
        
    df['penb'].fillna('G', inplace=True)
    
    # clean penb
    df['penb'] = df['penb'].apply(lambda x: str(x)[:1])
    
    # get floor number
    df['floor'] = df['floor'].apply(get_floor_number)
    
    # convert True/False to 1/0
    df['price'] = df['price'].apply(set_comma_to_dot)
    
    # replace "null" as NaN
    df = df.replace('null', np.nan, regex=True)
    
    # lower strings, replace with bools, turn bool into 1/0
    for column in ['balcony', 'basement', 'elevator', 'terrace', 'loggia', 'garage']:
        booleanize_column(df, column)
        df[column] = df[column].astype(np.float32)
    
    # turn cols to floats
    for column in ['floor', 'rooms', 'kitchen', 'price']:
        df[column] = df[column].astype(np.float32)
    
    # remove flats more expensive than 30 mil and cheaper than 1 mil
    df = df[df['price'].lt(30_000_000) & df['price'].gt(1_000_000)]
    
    # some area wrongly empty string value
    df['area'] = df['area'].replace('', np.nan, regex=True)
    
    # merge and keep links as indices
    df = df.reset_index().merge(extra_features, how='left', left_on='city_part_number', right_on='city_part_number').set_index('_id')
    
    numerical_cols = ['area',
                      'rooms',
                      'floor',
                      'rooms',
                      'pocet_cizincu',
                      'materske_skoly',
                      'zakladni_skoly',
                      'hustota_zalidneni',
                      'index_stari',
                      'kulturni_zarizeni',
                      'rekreacni_plochy',
                      'sportovni_plochy',
                      'detska_hriste',
                      'lesy_lesoparky',
                      'parky',
                      'znecisteni_ovzdusi',
                      'obyv_nocni_hluk',
                      'podil_zastavenych_ploch']
    
    numeric_imputer = SimpleImputer(strategy='mean')
    
    categorical_cols = ['owner',
                        'building_type',
                        'penb',
                        'state',
                        'city_part',
                        'equipment']
    
    # target encoding
    encoder = ce.TargetEncoder(return_df=True, cols=categorical_cols, verbose=1, min_samples_leaf=10)
    categorical_imputer = SimpleImputer(strategy='most_frequent')
    
    # drop city part only to add it later
    df_city_part = df.pop('city_part_number')
    
    # features and target split
    y = df.pop('price').astype(float)
    X = df
    
    # encode - categorical, numerical, target
    X = encoder.fit_transform(X, y)
    X[categorical_cols] = categorical_imputer.fit_transform(X[categorical_cols])
    X[numerical_cols] = numeric_imputer.fit_transform(X[numerical_cols])
    
    # create processed dataframe
    processed_dataset = pd.DataFrame(X, columns=list(df.columns), index=df.index)
    processed_dataset['price'] = y.values
    processed_dataset['district'] = df_city_part
    
    # processed_dataset.to_csv('processed_dataset.csv', index=True)
    return processed_dataset