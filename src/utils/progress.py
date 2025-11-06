"""Progress tracking and status display utilities."""

from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


class AuditProgress:
    """Progress tracker for audit operations."""

    def __init__(self) -> None:
        """Initialize the progress tracker."""
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        )
        self.task_ids: dict[str, TaskID] = {}

    def start(self) -> None:
        """Start the progress display."""
        self.progress.start()

    def stop(self) -> None:
        """Stop the progress display."""
        self.progress.stop()

    def add_task(
        self,
        name: str,
        description: str,
        total: Optional[int] = None,
    ) -> TaskID:
        """Add a new task to track.

        Args:
            name: Internal name for the task
            description: Display description
            total: Total number of items (None for indeterminate)

        Returns:
            Task ID
        """
        task_id = self.progress.add_task(description, total=total)
        self.task_ids[name] = task_id
        return task_id

    def update_task(
        self,
        name: str,
        advance: int = 1,
        description: Optional[str] = None,
    ) -> None:
        """Update a task's progress.

        Args:
            name: Task name
            advance: Amount to advance progress
            description: Optional new description
        """
        if name in self.task_ids:
            task_id = self.task_ids[name]
            if description:
                self.progress.update(task_id, advance=advance, description=description)
            else:
                self.progress.update(task_id, advance=advance)

    def complete_task(self, name: str, description: Optional[str] = None) -> None:
        """Mark a task as complete.

        Args:
            name: Task name
            description: Optional completion message
        """
        if name in self.task_ids:
            task_id = self.task_ids[name]
            if description:
                self.progress.update(task_id, description=f"{description} ✓")
            self.progress.update(task_id, completed=True)

    def print(self, message: str) -> None:
        """Print a message without disrupting progress.

        Args:
            message: Message to print
        """
        self.console.print(message)

    def print_header(self, title: str) -> None:
        """Print a section header.

        Args:
            title: Header title
        """
        self.console.print()
        self.console.rule(f"[bold cyan]{title}")
        self.console.print()

    def print_success(self, message: str) -> None:
        """Print a success message.

        Args:
            message: Success message
        """
        self.console.print(f"[green]✓[/green] {message}")

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: Error message
        """
        self.console.print(f"[red]✗[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.

        Args:
            message: Info message
        """
        self.console.print(f"[blue]ℹ[/blue] {message}")
