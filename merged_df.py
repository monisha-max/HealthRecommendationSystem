#!/usr/bin/env python
# coding: utf-8
import pandas as pd

import numpy as np
df = pd.read_csv('A_Z_medicines_dataset_of_India.csv')
df.sample(5)
df.shape

df.columns
#1.Data Cleaning
df.info()

#checking for duplicate values
df.duplicated().sum()
#remove duplicates
df = df.drop_duplicates(keep='first')
df.duplicated().sum()


df.shape


df.drop(columns=['id','Is_discontinued','manufacturer_name','type','pack_size_label'],inplace=True)
df.shape
df
df1 = pd.read_csv("medicine_dataset.csv",low_memory=False)
df1.sample(10)
for feature in df1.columns:
    print(feature)

df1.shape
import pandas as pd

print(df1.columns)

columns_to_drop = ['id', 'sideEffect4', 'sideEffect5', 'sideEffect6',
                   'sideEffect7', 'sideEffect8', 'sideEffect9', 'sideEffect10', 'sideEffect11', 'sideEffect12',
                   'sideEffect13', 'sideEffect14', 'sideEffect15', 'sideEffect16', 'sideEffect17', 'sideEffect18',
                   'sideEffect19', 'sideEffect20', 'sideEffect21', 'sideEffect22', 'sideEffect23', 'sideEffect24',
                   'sideEffect25', 'sideEffect26', 'sideEffect27', 'sideEffect28', 'sideEffect29', 'sideEffect30',
                   'sideEffect31', 'sideEffect32', 'sideEffect33', 'sideEffect34', 'sideEffect35', 'sideEffect36',
                   'sideEffect37', 'sideEffect38', 'sideEffect39', 'sideEffect40', 'sideEffect41', 'use0', 'use1',
                   'use2', 'use3', 'use4', 'Habit Forming', 'Action Class']


df1.drop(columns=columns_to_drop, inplace=True)

print(df1.columns)
df1.head()

df1.shape


df1.isnull().sum()

df1.duplicated().sum()

df1 = df1.drop_duplicates(keep='first')

df1.duplicated().sum()

df1

df

df1
# Convert all strings to lowercase in df1
df = df.applymap(lambda x: x.lower() if isinstance(x, str) else x)

# Convert all strings to lowercase in df2
df1 = df1.applymap(lambda x: x.lower() if isinstance(x, str) else x)

df
df1
# Merge the DataFrames based on their name column
merged_df = pd.merge(df, df1, how='inner', on='name')

merged_df

import pandas as pd
from IPython.display import HTML

merged_df.to_csv('merged_df.csv', index=False)

csv_link = '<a href="merged_df.csv" download>Click here to download your file</a>'
display(HTML(csv_link))

def get_medicine_details(medicine_name):
    # remove  extra spaces 
    filtered_df = merged_df[merged_df['name'].str.strip().str.lower() == medicine_name.strip().lower()]

    if filtered_df.empty:
        print(f"No details found for medicine: {medicine_name}")
        return None

    # Return the desired columns
    return filtered_df[['substitute0', 'substitute1', 'substitute2', 'substitute3', 'substitute4',
                        'sideEffect0', 'sideEffect1', 'sideEffect2', 'sideEffect3', 'Therapeutic Class', 'price(₹)', 'short_composition1', 'short_composition2']]

medicine_name = input("Enter the name of the medicine: ")

medicine_details = get_medicine_details(medicine_name)

if medicine_details is not None:
    print(medicine_details)



import pandas as pd
import requests


def get_medicine_details(medicine_name, merged_df):
    filtered_df = merged_df[merged_df['name'].str.strip().str.lower() == medicine_name.strip().lower()]

    if filtered_df.empty:
        print(f"Sorry, {medicine_name} is not available in the dataset.")
        return None

    
    return filtered_df[['substitute0', 'substitute1', 'substitute2', 'substitute3', 'substitute4',
                        'sideEffect0', 'sideEffect1', 'sideEffect2', 'sideEffect3', 'Therapeutic Class', 'price(₹)', 'short_composition1', 'short_composition2']]

def search_medicine_online(medicine_name, substitutes):
    API_KEY = "AIzaSyAf57eBhlNcPybhVAch4JhOQt0Yp4-113U"
    SEARCH_ENGINE_ID = "805b54bb3ec354bec"

    all_substitute_urls = {}  

    for substitute_name in substitutes:
        
        if isinstance(substitute_name, str):
            search_query = substitute_name + ' buy online India'

            url = 'https://www.googleapis.com/customsearch/v1'
            params = {
                'q': search_query,
                'key': API_KEY,
                'cx': SEARCH_ENGINE_ID
            }

            response = requests.get(url, params=params)
            results = response.json()

            if 'items' in results and results['items']:
                
                all_substitute_urls[substitute_name] = results['items'][0]['link']
            else:
                print(f"No search results found for substitute: {substitute_name}")

    return all_substitute_urls

try:
    merged_df = pd.read_csv("merged_df.csv")
except FileNotFoundError:
    print("Error: The merged_df.csv file is not found.")
    exit()

medicine_name = input("Enter the name of the medicine: ")

medicine_details = get_medicine_details(medicine_name, merged_df)

if medicine_details is not None:
    print(medicine_details)

    substitute_columns = ['substitute0', 'substitute1', 'substitute2', 'substitute3', 'substitute4']
    if all(col in medicine_details.columns for col in substitute_columns):
        substitutes = medicine_details[substitute_columns].values.tolist()[0]
        substitute_urls = search_medicine_online(medicine_name, substitutes)

        for substitute, url in substitute_urls.items():
            print(f"{substitute} URL:", url)

