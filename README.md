# teneo-farming
Teneo Pro farming bot

The script imitates the work of Teneo browser node. Current version as of 25.03.2025.

Each account works with one dedicated proxy to prevent Teneo from detecting groups of accounts using the same IP.

The script keeps track of the traffic passing through the proxy.

How to setup accounts:
1) Open https://dashboard.teneo.pro/dashboard
2) F12 -> Application -> Local storage -> accessToken
3) Copy your token to access_token in accounts.json
4) Repeat steps 1-3 for each account
5) Set your socks5 proxy in accounts.json, every account setups with one proxy
6) Start main.py

Screenshot:
![{10993D15-EBB4-459D-958B-1E7E22E3B2AF}](https://github.com/user-attachments/assets/e3e6f05b-7698-4156-a2b0-ccbc825af15a)
