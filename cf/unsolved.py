import click
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from utils import CFClient, get_config

console = Console()


@click.command()
def unsolved():
    """Show unsolved problems"""
    config = get_config(console)
    if config is None:
        return

    if "username" not in config and "password" not in config:
        console.print(
            "[bold red]ERROR: [/]Username and password not found in config file"
        )
        return

    client = CFClient(config["username"], config["password"])
    if not client.login():
        console.print("[bold red]ERROR: [/]Login failed")
        return

    driver = client.driver
    driver.get("https://codeforces.com/problemset")
    if driver.current_url != "https://codeforces.com/problemset":
        console.print("[bold red]ERROR: [/]Failed to fetch unsolved problems.")
        return
    problemset_page_source = driver.page_source

    soup = BeautifulSoup(problemset_page_source, "html.parser")
    problem_table = soup.find("table", class_="problems")
    if problem_table is None:
        console.print("[bold red]ERROR: [/]Failed to fetch unsolved problems.")
        return
    accepted_problems = problem_table.find_all("tr", class_="accepted-problem")

    unsolved_problems = [
        problem
        for problem in problem_table.find_all("tr")[1:]  # Avoid the header row
        if problem not in accepted_problems
    ]

    if len(unsolved_problems) == 0:
        console.print("[bold green]WOW: [/]You do not have any unsolved problems.")
        console.print(
            "(This means any problem where you have submitted a solution but it was not accepted.)"
        )
        console.print(
            "Obviously you will have several problems that you haven't tried."
        )
        return

    table = Table(
        title="Unsolved Problems",
        show_header=True,
        header_style="bold green",
        show_lines=True,
    )
    table.add_column("Problem ID", style="bright", justify="left", no_wrap=True)
    table.add_column("Problem Name", style="bright", justify="left", no_wrap=True)
    table.add_column("Submit", style="bright", justify="left", no_wrap=True)
    table.add_column("Total Submissions", style="bright", justify="left", no_wrap=True)
    table.add_column("Tags", style="bright", justify="left", no_wrap=True)
    for problem in unsolved_problems:
        print(problem)
        data = problem.find_all("td")
        _id = data[0].a.string.strip()
        problem_url = data[0].a["href"].strip()
        name = data[1].a.string.strip()
        submission_url = data[2].a["href"].strip()
        submission_id = submission_url.split("/")[-1]
        total_submissions = data[4].string.strip() if data[4].string else "N/A"

        # Extract tags
        tags_div = data[1].find_all("div")[1]  # Get the second div for tags
        tags = [
            tag.string.strip() for tag in tags_div.find_all("a")
        ]  # Extract tag titles

        # Add tags to the table row
        table.add_row(
            f"[link=https://codeforces.com{problem_url}]{_id}[/]",
            name,
            f"[link=https://codeforces.com{submission_url}]{submission_id}[/]",
            f"{total_submissions}",
            ", ".join(tags),
        )

    console.print(table)
