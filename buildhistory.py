import requests
import json

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
    headers = {
    'Authorization': 'Bearer JlJlZnJlc2hfdG9rZW49UlQ6Rl0qOW8hSXQxI3RAamRsZWNmRyVLb1VJUXNxJi5pc3N1ZWQ9MjAyNi0wMy0yN1QyMTowODowNS43ODE5NDE4WiYuZXhwaXJlcz0yMDk5LTEyLTMxVDAwOjAwOjAwLjAwMDAwMDBaJlRva2VuPWh2WWlyMEM5bDhZOEdETnBDQnk2VHBQYk5XcEgwanA5Z1VpbENabVNaalpfNUJsWVJHcXB5QV9JdUJYOWtrX250LTNhWTZsLWRaRXZkR19KWFRJYXlldXJ4WmlROUdQcjAxcGNDWkxJaHh5eklsd0lYLXdOckNXV0xRdGhRV0NhZDJYVkFkV0xRbEtSVzhwdlpSZGxpWVRKZmlXeC1ja0ZMMzFZaU53dDFpUkpUVmZzSzlKM1AzMjlNNHN4NDhaeHFrYTRmMUtWN1BiX01CbE5EbExLZmxSUDFXQlZTU3BSM2ROaHA1ai1QeDZmR3BTRHQ0VkJST05oRTVjQ0FCMjIyWkdoY2k0R05EVXlDdW9tZ3BqMXNfUHpKMDJiQmpHOTBvSy1Kcnp4U01PeTFYMkJhbFJxQ2ZKbXVGNW9NT3FZcUFwUjhueDFwWks4djV2eGQ5MWRFX3FxVnF3JmNsaWVudF9pZD1JbnZlbnRvcnlDb250cm9sX2xvY2FsaG9zdCZVc2VySWQ9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUzJnJvbGVzPUFQSSBMb2dpbiZodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lPWJyYW5kb24uZGluaEBpMnRlY2hpbmMuY29tJmh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL25hbWVpZGVudGlmaWVyPTU2ZTVlNzU0LTc3NDQtNDJlYi1hNzZmLTU4MjdlMTM4YzllMyZodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL2FjY2Vzc2NvbnRyb2xzZXJ2aWNlLzIwMTAvMDcvY2xhaW1zL2lkZW50aXR5cHJvdmlkZXI9NTZlNWU3NTQtNzc0NC00MmViLWE3NmYtNTgyN2UxMzhjOWUz',
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
