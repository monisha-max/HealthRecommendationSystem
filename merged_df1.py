#!/usr/bin/env python
# coding: utf-8
import pandas as pd
import numpy as np
df = pd.read_csv('merged_df.csv')
df.head()
df.columns
df['Chemical Class'] = df['Chemical Class'].fillna('')


#for missing values
df.isnull().sum()

df.duplicated().sum()

#remove duplicates
df = df.drop_duplicates(keep='first')
df.duplicated().sum()

df.shape
from sklearn.feature_extraction.text import TfidfVectorizer
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(df['Chemical Class'])
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

nn = NearestNeighbors(n_neighbors=6, metric='cosine').fit(tfidf_matrix)
distances, indices = nn.kneighbors(tfidf_matrix)
max_subs = 5 
for i in range(1, max_subs + 1):
    df[f'sub{i}'] = ''

for idx in range(len(df)):
    for i in range(1, max_subs + 1):
        neighbor_idx = indices[idx][i]
        if distances[idx][i] < 0.5:
            df.at[idx, f'sub{i}'] = df.iloc[neighbor_idx]['name']

df.to_csv('updated_merged_df.csv', index=False)
print("Substitutes added and file saved as 'merged_df(1).csv'.")
df.head(5)





