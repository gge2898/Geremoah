"""Terminal output helpers with ANSI colors."""


class Display:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    def task_start(self, task: str) -> None:
        print(f"\n{self.BOLD}{self.CYAN}Task:{self.RESET} {task}")
        print(f"{self.DIM}{'─' * 60}{self.RESET}")

    def iteration(self, n: int) -> None:
        print(f"\n{self.DIM}[Iteration {n}]{self.RESET}")

    def gemma_text(self, text: str) -> None:
        if text.strip():
            print(f"{self.CYAN}[GEMMA]{self.RESET} {text.strip()}")

    def action(self, name: str, args: dict) -> None:
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        print(f"{self.YELLOW}[ACTION]{self.RESET} {name}({args_str})")

    def task_done(self, message: str) -> None:
        print(f"\n{self.GREEN}{self.BOLD}[DONE]{self.RESET} {message}")
        print(f"{self.DIM}{'─' * 60}{self.RESET}\n")

    def error(self, message: str) -> None:
        print(f"{self.RED}[ERROR]{self.RESET} {message}")

    def warning(self, message: str) -> None:
        print(f"{self.YELLOW}[WARN]{self.RESET} {message}")

    def connected(self, addr: str) -> None:
        print(f"{self.GREEN}[BT]{self.RESET} Connected: {addr}")

    def disconnected(self) -> None:
        print(f"{self.YELLOW}[BT]{self.RESET} Client disconnected. Waiting for next connection...")
