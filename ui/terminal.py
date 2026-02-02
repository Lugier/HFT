"""
Terminal Dashboard using Rich
Displays real-time arbitrage opportunities
"""
import asyncio
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align

from core.arbitrage_engine import ArbitrageOpportunity, arbitrage_engine
from config.settings import DEFAULT_TRADE_SIZE_USD, MIN_PROFIT_USD

console = Console()


class TerminalDashboard:
    """Rich-based terminal dashboard for displaying arbitrage opportunities"""
    
    def __init__(self):
        self._opportunities: list[ArbitrageOpportunity] = []
        self._last_update: Optional[datetime] = None
        self._pairs_checked = 0
        self._scan_count = 0
        self._running = False
    
    def _create_header(self) -> Panel:
        """Create header panel"""
        header_text = Text()
        header_text.append("🔍 CRYPTO ARBITRAGE SCANNER v1.0", style="bold cyan")
        header_text.append("\n")
        
        status = "SCANNING" if self._running else "STOPPED"
        status_style = "bold green" if self._running else "bold red"
        
        header_text.append(f"Status: ", style="dim")
        header_text.append(f"{status}", style=status_style)
        header_text.append(" | ", style="dim")
        header_text.append(f"Last Update: ", style="dim")
        header_text.append(
            self._last_update.strftime("%H:%M:%S") if self._last_update else "Never",
            style="white"
        )
        header_text.append(" | ", style="dim")
        header_text.append(f"Pairs Checked: ", style="dim")
        header_text.append(f"{self._pairs_checked:,}", style="white")
        header_text.append(" | ", style="dim")
        header_text.append(f"Scans: ", style="dim")
        header_text.append(f"{self._scan_count}", style="white")
        
        return Panel(
            Align.center(header_text),
            border_style="blue",
            padding=(0, 2)
        )
    
    def _create_opportunities_table(self) -> Table:
        """Create opportunities table"""
        table = Table(
            title="💰 ARBITRAGE OPPORTUNITIES",
            show_header=True,
            header_style="bold magenta",
            border_style="dim"
        )
        
        table.add_column("#", style="dim", width=3)
        table.add_column("Level", width=10)
        table.add_column("Pair", style="cyan", width=12)
        table.add_column("Buy From", style="green", width=20)
        table.add_column("Buy Price", justify="right", style="green", width=12)
        table.add_column("Sell To", style="red", width=20)
        table.add_column("Sell Price", justify="right", style="red", width=12)
        table.add_column("Spread", justify="right", width=8)
        table.add_column("Gas", justify="right", width=8)
        table.add_column("Fees", justify="right", width=10)
        table.add_column("Net Profit", justify="right", width=12)
        
        if not self._opportunities:
            table.add_row(
                "", "", "", "", "", 
                Text("No profitable opportunities found yet...", style="dim italic"),
                "", "", "", ""
            )
        else:
            for i, opp in enumerate(self._opportunities[:15], 1):  # Show top 15
                level = opp.profit_level
                level_text = Text()
                if level:
                    level_text.append(f"{level.symbol} {level.name}", style=f"bold {level.color}")
                else:
                    level_text.append("LOW", style="dim")
                
                buy_from = f"{opp.buy_source.source_name}"
                if opp.buy_source.chain:
                    buy_from += f" ({opp.buy_source.chain.name})"
                
                sell_to = f"{opp.sell_source.source_name}"
                if opp.sell_source.chain:
                    sell_to += f" ({opp.sell_source.chain.name})"
                
                # Color profit based on amount
                profit_style = "green"
                if opp.net_profit_usd >= 50:
                    profit_style = "bold red"
                elif opp.net_profit_usd >= 20:
                    profit_style = "bold yellow"
                elif opp.net_profit_usd >= 10:
                    profit_style = "bold green"
                
                # Format prices nicely (handle very small numbers)
                def fmt_price(p):
                    return f"${p:,.2f}" if p > 1 else f"${p:.6f}"

                table.add_row(
                    str(i),
                    level_text,
                    opp.symbol,
                    buy_from,
                    fmt_price(opp.buy_price),
                    sell_to,
                    fmt_price(opp.sell_price),
                    f"{opp.spread_pct:.2f}%",
                    f"${opp.gas_cost_usd:.2f}",
                    f"${opp.withdrawal_fee_usd:.2f}",
                    Text(f"${opp.net_profit_usd:.2f}", style=profit_style)
                )
        
        return table
    
    def _create_info_panel(self) -> Panel:
        """Create info panel with settings"""
        info = Text()
        info.append("Settings:\n", style="bold")
        info.append(f"  Trade Size: ${DEFAULT_TRADE_SIZE_USD:,.0f}\n", style="dim")
        info.append(f"  Min Profit: ${MIN_PROFIT_USD:.0f}\n", style="dim")
        info.append("\n")
        info.append("Legend:\n", style="bold")
        info.append("  🚀 CRITICAL: >$50 profit\n", style="red")
        info.append("  💰 HIGH: >$20 profit\n", style="yellow")
        info.append("  💵 MEDIUM: >$5 profit\n", style="green")
        info.append("\n")
        info.append("Press Ctrl+C to exit", style="dim italic")
        
        return Panel(info, title="Info", border_style="dim")
    
    def _generate_display(self) -> Table:
        """Generate the full display"""
        layout = Table.grid(expand=True)
        layout.add_column(ratio=1)
        
        layout.add_row(self._create_header())
        layout.add_row("")
        layout.add_row(self._create_opportunities_table())
        layout.add_row("")
        layout.add_row(self._create_info_panel())
        
        return layout
    
    def update(self, opportunities: list[ArbitrageOpportunity]):
        """Update dashboard with new opportunities"""
        self._opportunities = opportunities
        self._last_update = datetime.now()
        self._pairs_checked = arbitrage_engine.total_pairs_checked
        self._scan_count += 1
    
    async def run(self):
        """Run the dashboard with live updates"""
        self._running = True
        self._last_update = datetime.now()
        
        console.print("\n[bold cyan]Starting Arbitrage Scanner...[/bold cyan]\n")
        
        # Initialize engine
        await arbitrage_engine.initialize()
        
        console.print("[bold green]✓ Initialization complete![/bold green]\n")
        
        async def scan_callback(opportunities: list[ArbitrageOpportunity]):
            self.update(opportunities)
        
        async def on_scan_start():
            # Update the time so the user knows a new scan has begun
            self._last_update = datetime.now()

        # Start scanning in background
        scan_task = asyncio.create_task(
            arbitrage_engine.run_continuous(callback=scan_callback, on_scan_start=on_scan_start)
        )
        
        try:
            with Live(self._generate_display(), refresh_per_second=2, console=console) as live:
                while True:
                    live.update(self._generate_display())
                    await asyncio.sleep(0.5)
                    
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            scan_task.cancel()
            try:
                await scan_task
            except asyncio.CancelledError:
                pass


# Global instance
dashboard = TerminalDashboard()
