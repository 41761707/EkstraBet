"""Errors raised by the database migration runner."""


class MigrationError(Exception):
    """Runner failure with an English message."""


class MigrationSqlError(MigrationError):
    """MySQL rejected one statement. Later statements are not run."""

    def __init__(self, index: int, detail: str) -> None:
        self.index = index
        self.detail = detail
        # Numer statementu zostaje w komunikacie, bo CLI drukuje sam str()
        super().__init__(f"Statement {index} failed: {detail}")
