import click
import time
import json
import websocket
import os
from utils import get_config, CFClient
from bs4 import BeautifulSoup
from rich.console import Console
from rich.live import Live
from seleniumbase import Driver

console = Console()


lang_ids = {
    "py": "70",
    "c": "43",
    "cpp": "73",
    "cs": "79",  # C#
    "d": "28",  # D
    "go": "32",  # Golang
    "hs": "12",  # Haskell
    "java": "74",
    "kt": "83",  # Kotlin
    "ml": "19",  # Ocaml
    "php": "6",
    "rb": "67",  # Ruby
    "rs": "75",  # Rust
    "js": "55",  # Nodejs
}


@click.command()
@click.argument("file", required=True)
def submit(file: str):
    """
    Submits your solution
    """
    slash = "/" if os.name == "posix" else "\\"

    data = get_config(console)
    if data is None:
        return

    cf_dir = data.get("dir")
    if cf_dir is None:
        console.print(
            "[bold red]ERROR: [/]The default directory for parsing is not set.\nPlease run the `cf config` command."
        )
        return

    current_dir = os.getcwd()
    cf_dir = os.path.abspath(cf_dir)
    if not current_dir.startswith(cf_dir) and current_dir != cf_dir:
        console.print(
            "[bold red]ERROR: [/]The current directory is not a contest directory.\n"
        )
        return

    c_id = current_dir.split(slash)[-1]
    if not c_id.isdigit():
        console.print(
            "[bold red]ERROR: [/]The current directory is not a contest directory.\n"
        )
        return

    if not os.path.isfile(file):
        console.print("[bold red]ERROR: [/]The file does not exist.\n")
        return

    p_id = file.split(".")[0].lower()
    p_ext = file.split(".")[-1]

    if p_ext not in lang_ids:
        console.print("[bold red]ERROR: [/]The file extension is not supported.\n")
        return

    if "username" not in data or "password" not in data:
        console.print(
            "[bold red]ERROR: [/]Username and password not set. Please use `cf config`.\n"
        )
        return

    client = CFClient(data["username"], data["password"])
    if not client.login():
        console.print("[bold red]ERROR: [/]Unable to login")
        return

    url = f"https://codeforces.com/contest/{c_id}/submit"
    # csrf = client.get_csrf(url)
    # url += f"?csrf_token={csrf}"
    # resp = client.session.post(
    #     url=url,
    #     allow_redirects=True,
    #     data={
    #         "csrf_token": csrf,
    #         "ftaa": "",
    #         "bfaa": "",
    #         "action": "submitSolutionFormSubmitted",
    #         "submittedProblemIndex": p_id,
    #         "programTypeId": lang_ids[p_ext],
    #         "contestId": c_id,
    #         "source": open(file, "r").read(),
    #         "tabSize": "4",
    #         "sourceCodeConfirmed": "true",
    #     },
    # )

    # Submitting using SeleniumBase
    driver = Driver(uc=True, headless=True, browser="chrome")
    driver.get(url)
    driver.wait_for_element_visible("table", class_="table-form")
    driver.click('select[name="submittedProblemIndex"]')
    driver.click(f'option[value="{p_id}"]')
    driver.click('select[name="programTypeId"]')
    driver.click(f'option[value="{lang_ids[p_ext]}"]')
    driver.choose_file('input[type="file"]', file)
    driver.click('input[type="submit"]')
    driver.wait_for_element_visible("table", class_="status-frame-datatable")
    if not driver.get_current_url().startswith(
        f"https://codeforces.com/contest/{c_id}/my"
    ):
        console.print("[bold red]ERROR: [/] Submission failed.")
        return

    soup = BeautifulSoup(driver.page_source, "html.parser")

    table = soup.find("table", {"class": "status-frame-datatable"})
    last_sub = table.find_all("tr")[1]  # type: ignore
    submission_id = int(last_sub["data-submission-id"])
    submission_status = last_sub.find("td", {"class": "status-verdict-cell"})
    if submission_status["waiting"] == "true":
        submission_status = "In Queue"
    else:
        submission_status = "IDK"
    submission_time = last_sub.find("td", class_="time-consumed-cell").string
    submission_memory = last_sub.find("td", class_="memory-consumed-cell").string

    console.print(
        f"[bold green]SUBMITTED[/] [bold blue]https://codeforces.com/contest/{c_id}/submission/{submission_id}[/]"
    )
    live_text = f"""
Status:     [bold white]{submission_status.strip()}[/]
Time:       [bold white]{submission_time.strip()}[/]
Memory:     [bold white]{submission_memory.strip()}[/]
                    """

    pc = None
    cc = None
    metas = soup.find_all("meta")

    for meta in metas:
        if meta.get("name") == "pc":
            pc = meta.get("content")
        elif meta.get("name") == "cc":
            cc = meta.get("content")

    submission_watcher = websocket.WebSocket()
    submission_watcher.connect(
        f"wss://pubsub.codeforces.com/ws/s_{pc}/s_{cc}?_={int(time.time())}"
    )

    live = Live(live_text, console=console)
    live.start()
    live.refresh()
    while True:
        submission = json.loads(submission_watcher.recv())
        submission_data = json.loads(submission["text"])["d"]
        live_submission_id = submission_data[1]
        if live_submission_id == submission_id:
            status = submission_data[6].strip()
            test_case = submission_data[8]

            if status == "OK":
                status_text = "[bold green]ACCEPTED[/]"
            elif status == "TESTING":
                status_text = f"[bold]Running on test case: {test_case}[/]"
            else:
                status_text = f"[bold red]{' '.join(status.split('_'))}[/] on test case: {test_case}"

            timee = submission_data[9]
            memory = int(submission_data[10]) // 1000
            live_text = f"""
Status:     {status_text}
Time:       [bold]{timee} ms[/]
Memory:     [bold]{memory} KB[/]
            """
            live.update(live_text)
            live.refresh()
            if status != "TESTING":
                live.stop()
                submission_watcher.close()
                break
