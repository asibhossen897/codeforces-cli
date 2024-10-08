import click
import os
import requests
from rich.console import Console
from bs4 import BeautifulSoup
from utils import get_config, get_bp
from seleniumbase import Driver

driver = Driver(undetected=True, headless=True, browser="chrome", headed=False)

console = Console()


def parse_problem(
    contest_id: int, problem: str, cf_dir: str, print_info: bool = True, bp: str = "_"
):
    slash = "/" if os.name == "posix" else "\\\\"

    url = f"https://codeforces.com/contest/{contest_id}/problem/{problem}"
    driver.get(url)
    problem_page_source = driver.page_source
    # driver.quit()

    if len(problem_page_source) == 0:
        console.print(
            "[bold red]ERROR:[/] Contest or problem not found OR Contest has not started yet."
        )
        return
    if (
        driver.current_url
        != f"https://codeforces.com/contest/{contest_id}/problem/{problem}"
    ):
        console.print("[bold red]ERROR: [/]Unable to fetch problem details.")
        return

    contest_dir = f"{cf_dir}{slash}{contest_id}"

    if not os.path.isdir(contest_dir):
        os.mkdir(contest_dir)
        console.print(f"[bold green]INFO: [/]Created directory: `{contest_id}`")

    soup = BeautifulSoup(problem_page_source, "html.parser")
    tests = soup.find("div", class_="sample-test")

    inputs = tests.find_all("div", class_="input")  # type: ignore
    outputs = tests.find_all("div", class_="output")  # type: ignore

    final_inps = []
    final_outs = []

    for inp in inputs:
        final_inps.append(
            "\n".join(
                e.strip() if type(e) == str else e.string.strip()
                for e in inp.find("pre").contents
                if not (type(e) != str and e.string is None)
            )
        )

    for out in outputs:
        final_outs.append(
            "\n".join(
                e.strip() if type(e) == str else e.string.strip()
                for e in out.find("pre").contents
                if not (type(e) != str and e.string is None)
            )
        )

    for i in range(len(final_inps)):
        console.print(f"[bold green]INFO: [/]Parsing sample test case #{i + 1}...")
        inp = final_inps[i]
        out = final_outs[i]

        with open(f"{contest_dir}{slash}{problem}.{i}.input.test", "w") as f:
            f.write(inp)

        with open(f"{contest_dir}{slash}{problem}.{i}.output.test", "w") as f:
            f.write(out)

    if bp != "_":
        bp_text = get_bp(bp)
        if bp_text is None:
            console.print(f"[bold red]ERROR: [/]No boilerplate file found for `{bp}`.")
        else:
            with open(f"{contest_dir}{slash}{problem}.{bp}", "w") as f:
                f.write(bp_text)
                console.print(
                    f"[bold green]INFO: [/]Created boilerplate `{problem}.{bp}` file."
                )

    console.print(
        f"[bold green]Problem {contest_id} {problem} parsed successfully.[/]\n"
    )
    if print_info:
        console.print(f"Use `cd {contest_dir}` to move the contest directory.")
        console.print("Then use `cf run FILENAME` to check the sample test cases.\n")


@click.command()
@click.argument("contest_id", required=True)
@click.argument("problem", default="_", required=False)
@click.option("--lang", required=False, default="_")
def parse(contest_id: int, problem: str, lang: str):
    """
    Parse the sample test cases for a problem OR a contest.
    """
    problem = problem.lower()
    data = get_config(console)
    if data is None:
        return

    cf_dir = data.get("dir")
    if cf_dir is None:
        console.print(
            "[bold red]ERROR: [/]The default directory for parsing is not set.\nPlease run the `cf config` command."
        )
        return

    if problem == "_":
        r = driver.get(url=f"https://codeforces.com/contest/{contest_id}")
        contest_page_source = driver.page_source
        if len(contest_page_source) == 0:
            console.print(
                "[bold red]ERROR: [/]Contest has not started yet OR it doesn't exist.\n"
            )
            return

        if driver.current_url != f"https://codeforces.com/contest/{contest_id}":
            console.print(
                f"[bold red]ERROR: [/]Unable to fetch contest details.\nSTATUS CODE: [bold red]{r.status_code}[/]\n"
            )
            return

        soup = BeautifulSoup(contest_page_source, "html.parser")
        problems_table = soup.find("table", class_="problems")
        if problems_table is None:
            console.print("[bold red]ERROR:[/] Unable to parse problems table.")
            return

        problems = problems_table.find_all("tr")[1:]
        for i, p in enumerate(problems):
            items = p.find_all("td")
            problem_id = items[0].a.string.strip().lower()
            parse_problem(
                contest_id,
                problem_id,
                cf_dir,
                print_info=(i == len(problems) - 1),
                bp=lang,
            )
    else:
        parse_problem(contest_id, problem, cf_dir, bp=lang)
