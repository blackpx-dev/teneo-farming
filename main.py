import asyncio
import json
from functions import FarmingUI, process_account
from rich.live import Live
from rich.console import Console
console = Console()
async def main():
    try:
        with open('accounts.json') as f:
            accounts = json.load(f)
        ui = FarmingUI()
        tasks = []
        async def update_ui():
            with Live(ui.make_layout(), refresh_per_second=4, screen=True) as live:
                while True:
                    live.update(ui.make_layout())
                    await asyncio.sleep(0.25)
        await asyncio.gather(
            update_ui(),
            *[process_account(acc, ui) for acc in accounts]
        )
    except FileNotFoundError:
        console.print("[red]Error: accounts.json not found[/red]")
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid accounts.json format[/red]")
    except KeyboardInterrupt:
        console.print("\n[green]Shutting down gracefully...[/green]")
    except Exception as e:
        console.print(f"[red]Critical error: {str(e)}[/red]")
    finally:
        console.print("[blue]Script finished[/blue]")
if __name__ == "__main__":
    asyncio.run(main())