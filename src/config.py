import os

from dotenv import load_dotenv

load_dotenv()

if "bot_token" in os.environ:
    staging = False
    bot_token = os.getenv("bot_token")
    records_channel = 692303437882458122
else:
    print("=== Running in Staging ===")
    bot_token = os.getenv("staging_token")
    staging = True
    records_channel = 1199677882730029086
webhook = os.getenv("webhook")

prefix = "-"
welcome_message = (
    f"### Welcome to TypeRacer Stats!\n"
    f"Run `{prefix}link [typeracer_username]` to start using the bot\n"
)

bot_owner = 155481579005804544
bot_admins = [
    bot_owner,
    191227023140585472,  # poem
    108328502591250432,  # charlie
    389528520201601026,  # ginoo
    476016555981930526,  # pasta
    300463822991392769,  # jisoo
    697048255254495312,  # eugene
    447787480461344779,  # josh
    581911124392411175,  # zak
]
supporters = [
    96023825640083456,  # jon
    83888634339528704,  # cameron
    108328502591250432,  # charlie
    191227023140585472,  # poem
    389528520201601026,  # ginoo
    697048255254495312,  # eugene
    1165304427830325379, # flaneur
]
bot_id = 1213306973374644256
legacy_bot_id = 742267194443956334

donate_link = "https://www.paypal.com/donate/?business=X9JW4MC3CLNAE&no_recurring=0&currency_code=USD&item_name=TypeRacer+Stats"
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
changelog_path = os.path.join(root_dir, "changelog.txt")
