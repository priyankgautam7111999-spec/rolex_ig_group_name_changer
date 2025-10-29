# Instagram Group Name Changer Bot (Selenium)

Yeh bot Instagram Web par DM (group thread) ka naam change karne ki koshish karta hai using Selenium (Chrome).

Warning & Disclaimer
- Yeh automation Instagram ke Terms of Service ke khilaf ho sakta hai. Use at your own risk.
- Instagram UI frequently change hota hai; selectors break ho sakte hain. Agar kaam na kare to README ke troubleshooting section dekhen.
- Do NOT store sensitive credentials in public repos.

Requirements
- Python 3.8+
- Chrome browser (matching ChromeDriver)
- Internet connection

Files
- bot.py              : Main script
- config_example.json : Example config file
- requirements.txt    : Python dependencies

Setup
1. Clone or download the files.
2. Create a virtualenv (recommended):
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
3. Install dependencies:
   pip install -r requirements.txt
4. Create a config.json (see config_example.json) or pass credentials via CLI.

Usage
Basic example:
python bot.py --username your_username --password your_password --target-name "Old Group Name" --new-name "New Group Name"

Options:
--username        Instagram username (or set in config.json)
--password        Instagram password (or set in config.json)
--config          Path to config.json (optional)
--target-name     Current group name (exact or unique substring) to find the thread
--members         Comma-separated usernames of members to identify thread (alternative to --target-name)
--new-name        New group name you want to set
--headless        Run Chrome in headless mode (optional; for debugging, run non-headless)

2FA and manual prompts
- Agar Instagram 2FA maangta hai, script console mein ruk kar aapse code maang sakti hai. Enter the code in console to continue.
- Agar script kisi element ko locate nahi kar paati (UI mismatch), script GUI mein thread details open kar degi aur aapko manual change karne ko bolegi.

Troubleshooting
- "Element not found" errors: Instagram UI updated; open DevTools and find equivalent selector. Update bot.py where selectors are used.
- Login failing: Check credentials and whether Instagram showing challenge/verification screens. Manually login in a browser to see the flow.

Security
- Prefer using environment variables or local config file with restricted permissions.
- Do not commit credentials to a repo.
