import requests
import json
import os
from dotenv import load_dotenv

# 
def get_transaction_history():
    url = "http://i2techinventory:8703/public-api/transactions/streamgridrequestcsv"

    payload = json.dumps({
    "AdditionalSkipCount": 0,
    "PageSize": 0,
    "PageNumber": 0,
    "Sort": [
        {
        "Field": "UserTransactionDate",
        "Dir": "desc"
        }
    ],
    "FieldTitles": [
        {
        "Key": "AssetTransQuantity",
        "Value": "TransactionQuantity"
        },
        {
        "Key": "OrderNumber",
        "Value": "OrderNumber"
        },
        {
        "Key": "AssetDescription",
        "Value": "ItemDescription"
        },
        {
        "Key": "AssetTag",
        "Value": "WASPNumber"
        },
        {
        "Key": "AssetTypeNumber",
        "Value": "ItemType"
        },
        {
        "Key": "LocationCode",
        "Value": "Location"
        },
        {
        "Key": "SiteDescription",
        "Value": "SiteDescription"
        },
        {
        "Key": "SiteName",
        "Value": "Site"
        },
        {
        "Key": "TransTypeDescription",
        "Value": "TransactionType"
        },
        {
        "Key": "SerialNumber",
        "Value": "SerialNumber"
        },
        {
        "Key": "UserTransactionDate",
        "Value": "TransactionDate"
        },
        {
        "Key": "TransactionCost",
        "Value": "TransactionCost"
        },
        {
        "Key": "Category",
        "Value": "Category"
        },
        {
        "Key": "ManufacturerName",
        "Value": "Manufacturer"
        },
        {
        "Key": "Lot",
        "Value": "Lot"
        }
    ],
    "FilterBehavior": 0
    })
    load_dotenv()
    headers = {
    'Authorization': f"Bearer {os.getenv('WASP_TOKEN')}",
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
