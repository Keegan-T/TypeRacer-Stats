from dotenv import load_dotenv
import os

load_dotenv()

prefix = "-"
bot_token = os.getenv("bot_token")
staging_token = os.getenv("staging_token")
records_channel = 1199677882730029086
bot_owner = 155481579005804544
bot_admins = [
    bot_owner,
    191227023140585472, # poem
    108328502591250432, # charlie
    389528520201601026, # ginoo
    476016555981930526, # pasta
    300463822991392769,  # jisoo
]
supporters = [
    389528520201601026, # ginoo
    108328502591250432, # charlie
]
log_channel = 1219730445269471345
donate_link = "https://www.paypal.com/donate/?business=X9JW4MC3CLNAE&no_recurring=0&currency_code=USD&item_name=TypeRacer+Stats"