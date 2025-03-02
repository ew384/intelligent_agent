/usr/local/bin/chrome-for-testing --remote-debugging-port=9222 --user-data-dir="~/endian/intelligent_agent/browser_data/credit_card/user_data"
curl -X POST http://localhost:8001/tasks \
   -H "Content-Type: application/json" \
   -d '{
     "scenario_type": "credit_card",
     "parameters": {
       "url": "https://e.creditcard.ecitic.com/citiccard/ebank-ocp/ebankpc/myaccount.html",
       "notify_wechat": true,
       "wechat_contact": "endian"
     }
   }'