## REG.RU DDNS updater 
### Installation
1. Ensure to add your provider`s subnet in https://www.reg.ru/user/account/#/settings/api/
2. Rename and edit config.json
3. Add script to cron
4. Voila!

#### Notes
``` 
...
"ip_provider": "..." // A URL of service that returns your external IP address in plain text format. 
...
```