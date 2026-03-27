import random
import tkinter as tk
from tkinter import messagebox


class BlindSnakeGame:
    def __init__(self, parent=None):
        self.parent = parent
        self.size = 5
        self.max_moves = 12
        self.moves_left = self.max_moves
        self.result = False

        self.snake_pos = [random.randint(0, self.size - 1), random.randint(0, self.size - 1)]
        self.target_pos = [random.randint(0, self.size - 1), random.randint(0, self.size - 1)]
        while self.target_pos == self.snake_pos:
            self.target_pos = [random.randint(0, self.size - 1), random.randint(0, self.size - 1)]

        self.last_distance = self._distance()

        self.win = tk.Toplevel(parent)
        self.win.title("Desafio: Cobra Cega")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)

        if parent is not None:
            x = parent.winfo_rootx() + 60
            y = parent.winfo_rooty() + 60
            self.win.geometry(f"+{x}+{y}")

        container = tk.Frame(self.win, padx=14, pady=12)
        container.pack(fill="both", expand=True)

        self.title_label = tk.Label(container, text="Cobra Cega", font=("Arial", 12, "bold"))
        self.title_label.pack(anchor="w")

        instructions = (
            "Leve a cobra até o alvo sem ver o mapa.\n"
            "Use os botões para mover e siga as pistas de distância."
        )
        tk.Label(container, text=instructions, justify="left").pack(anchor="w", pady=(6, 8))

        self.moves_label = tk.Label(container, text="")
        self.moves_label.pack(anchor="w")

        self.status_label = tk.Label(container, text="", fg="#2c3e50", justify="left")
        self.status_label.pack(anchor="w", pady=(6, 8))

        controls = tk.Frame(container)
        controls.pack(pady=(4, 8))

        tk.Button(controls, text="↑", width=5, command=lambda: self._move(-1, 0)).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(controls, text="←", width=5, command=lambda: self._move(0, -1)).grid(row=1, column=0, padx=4, pady=4)
        tk.Button(controls, text="→", width=5, command=lambda: self._move(0, 1)).grid(row=1, column=2, padx=4, pady=4)
        tk.Button(controls, text="↓", width=5, command=lambda: self._move(1, 0)).grid(row=2, column=1, padx=4, pady=4)

        tk.Button(container, text="Cancelar", command=self._cancel).pack(anchor="e")

        self._set_status("Comece a mover. Boa sorte.")
        self._refresh_moves()

    def _distance(self) -> int:
        return abs(self.snake_pos[0] - self.target_pos[0]) + abs(self.snake_pos[1] - self.target_pos[1])

    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text)

    def _refresh_moves(self) -> None:
        self.moves_label.config(text=f"Movimentos restantes: {self.moves_left}")

    def _move(self, dr: int, dc: int) -> None:
        next_r = self.snake_pos[0] + dr
        next_c = self.snake_pos[1] + dc

        if not (0 <= next_r < self.size and 0 <= next_c < self.size):
            self.moves_left -= 1
            self._refresh_moves()
            self._set_status("Bateu na parede. O alvo parece na mesma distância.")
            if self.moves_left <= 0:
                self._lose()
            return

        self.snake_pos = [next_r, next_c]
        self.moves_left -= 1

        dist = self._distance()
        if dist == 0:
            self.result = True
            messagebox.showinfo("Sucesso", "Você encontrou o alvo da cobra cega!", parent=self.win)
            self.win.destroy()
            return

        if dist < self.last_distance:
            hint = "Mais perto."
        elif dist > self.last_distance:
            hint = "Mais longe."
        else:
            hint = "Distância igual."

        self.last_distance = dist
        self._refresh_moves()
        self._set_status(f"{hint} Distância atual: {dist}.")

        if self.moves_left <= 0:
            self._lose()

    def _lose(self) -> None:
        messagebox.showerror("Falhou", "Você não encontrou o alvo a tempo.", parent=self.win)
        self.win.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.win.destroy()

    def run(self) -> bool:
        self.win.grab_set()
        self.win.wait_window()
        return self.result


def run_unlock_game(parent=None) -> bool:
    game = BlindSnakeGame(parent=parent)
    return game.run()
