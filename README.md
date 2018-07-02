# SalienBot
This is a bot that will play the 2018 Steam Summer Sale game Salians for you.

# WARNING - EXPERIMENTAL
This the first version of the bot with minimal testing.  Expect a lot of crashes if you use it.

## Getting Started
1. Install Python >= 3.6 https://www.python.org/getit/
1. `$ git clone https://github.com/masonelmore/salienbot.git`
1. (Optional, but recommended) Set up a virtual environment.
    1. `$ pip install virtualenv`
    1. `$ virtualenv venv`
        1. You might need to supply the path to the python executable:
        1. $ `virtualenv -p <path> venv` replace `<path>` with the actual location.
    1. Activate the virtual environment
        1. Windows: `$ venv\Scripts\activate.bat`
        1. Linux/Mac/Other: `$ ./venv/bin/activate`
    
1. Install requests `(venv) $ pip install requests`
1. Installation complete!

## Using SalienBot
`(venv) $ python main.py <token> [accountid]`

* You can get your `token` from https://steamcommunity.com/saliengame/gettoken. Make sure you are logged into steam.

* The optional `accountid` is your Steam32 ID, which can be found with a quick google search.  It is used to show your stats in a boss zone.
