import os
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional
from rich.console import Console
from seleniumbase import Driver

driver = Driver(undetected=True, headless=True, browser="chrome")


def get_config(console: Console) -> Optional[dict]:
    slash = "/" if os.name == "posix" else "\\\\"

    config_path = os.path.expanduser("~") + slash + "codeforces.uwu"
    if not config_path:
        console.print(
            "[bold red]ERROR: [/]Config file not found.\nPlease run `cf config`\n"
        )
        return

    if not os.path.isfile(config_path):
        console.print(
            "[bold red]ERROR: [/]Config file not found.\nPlease run `cf config`\n"
        )
        return

    data = None
    with open(config_path, "r+") as f:
        data = json.loads("".join(f.readlines()))

    return data


def get_bp(lang: str) -> Optional[str]:
    slash = "/" if os.name == "posix" else "\\\\"
    bp_dir = os.path.expanduser("~") + slash + "cf_boilerplates"

    if not os.path.isdir(bp_dir):
        return
    if not os.path.isfile(bp_dir + slash + "template." + lang):
        return

    with open(bp_dir + slash + "template." + lang, "r") as f:
        return f.read()


class CFClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.console = Console()
        self.driver = Driver(
            undetected=True, headless=True, browser="chrome", headed=False
        )

    def login(self) -> bool:
        self.console.log("Logging in...")
        self.driver.open("https://codeforces.com/enter")
        self.driver.wait_for_element_visible("#handleOrEmail")
        self.driver.send_keys("#handleOrEmail", self.username)
        self.driver.send_keys("#password", self.password)
        self.driver.click('input[type="submit"][value="Login"]')
        self.driver.sleep(5)
        self.driver.open("https://codeforces.com/")

        # Use the driver's page_source directly instead of writing to a file
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        # Look for the user profile link in the top-right corner
        user_link = soup.find("a", href=f"/profile/{self.username}")

        if user_link and self.username in user_link.text.strip():
            self.console.log("Logged in successfully")
            return True
        else:
            self.console.log("[bold red]ERROR: [/]Login failed.")
            return False
