
import requests
import pandas as pd
import json
api_key: str = "TUIC1EDE34L1LOYA"
symbol = "IBM"
function = "TIME_SERIES_DAILY"
url = f'https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}'
# url= 'https://search.worldbank.org/api/v3/wds?format=json&qterm=wind%20turbine&fl=docdt,count'
response = requests.get(url)
data = response.json()
print(json.dumps(data, indent=2))
#  
# dataframe = pd.DataFrame(data["Time Series (Daily)"])
# dataframe = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
# dataframe = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
# dataframe.reset_index(inplace=True)
# dataframe.rename(columns={"index":"date", "1. open": "open"}, inplace=True)
# print(dataframe)
