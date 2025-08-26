import sys
import os
import time
import tkinter as tk
from tkinter import font as tkfont

# ---------------- Configuración ----------------
DEFAULT_ROWS = 30
COLS_LEFT  = list("abcde")
COLS_RIGHT = list("fghij")
ALL_COLS   = COLS_LEFT + COLS_RIGHT
RAIL_KEYS  = ("L+", "L-", "R+", "R-")  # Left Red, Left Blue, Right Red, Right Blue
SEP = " --- "
CELL_W     = 4   # antes 3: ahora caben '23+' o '123' sin mover nada
RAIL_W     = 4
EMPTY      = "·"  # mejor que ▢ en algunas monospace; puedes volver a "▢" si quieres



# ---------------- Utilidades de formato ----------------
# --- Utilidades de formato ---
def fix_width(s: str, width: int) -> str:
    """Devuelve s encajada exactamente en 'width' caracteres (sin romper layout)."""
    s = str(s)
    if len(s) > width:
        # Clipping duro: prioriza ver el final (sufijos +/-), ej: '1234+' -> '234+'
        s = s[-width:]
    # centrado estable:
    pad = width - len(s)
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right

def header_line() -> str:
    left_cols  = " ".join(fix_width(c, CELL_W) for c in COLS_LEFT)
    right_cols = " ".join(fix_width(c, CELL_W) for c in COLS_RIGHT)
    parts = [
        fix_width("000 |", 5), fix_width("rojo", 6), "|", fix_width("azul", 6), "|",
        fix_width("---", 5), "| ",
        left_cols, " |", SEP, "| ",
        right_cols, " |", SEP, "|",
        fix_width("rojo", 6), "|", fix_width("azul", 6), "|"
    ]
    return "".join(parts)

def row_line(row: int, grid, rails) -> str:
    rkey = f"{row:03d}"
    left_vals  = " ".join(fix_width(grid.get((rkey, c), EMPTY), CELL_W) for c in COLS_LEFT)
    right_vals = " ".join(fix_width(grid.get((rkey, c), EMPTY), CELL_W) for c in COLS_RIGHT)

    l_red  = fix_width(rails["L+"].get(rkey, EMPTY), RAIL_W)
    l_blue = fix_width(rails["L-"].get(rkey, EMPTY), RAIL_W)
    r_red  = fix_width(rails["R+"].get(rkey, EMPTY), RAIL_W)
    r_blue = fix_width(rails["R-"].get(rkey, EMPTY), RAIL_W)

    return (
        f"{rkey} | {l_red} | {l_blue} | {fix_width('---',3)} | "
        f"{left_vals} |{SEP}| {right_vals} |{SEP}| {r_red} | {r_blue} |"
    )


def center(s: str, width: int) -> str:
    s = s[:width]
    pad = width - len(s)
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right




# ---------------- Parser del fichero de conexiones ----------------
def parse_connections(path: str, rows: int):
    grid = {}  # (row_str, col_letter) -> token
    rails = {k: {} for k in RAIL_KEYS}  # "L+"/"L-"/"R+"/"R-" -> {row_str: token}

    if not os.path.exists(path):
        return grid, rails

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # Formatos admitidos:
            # 1) RIEL:   L+:010=+, L-:012=1-, R+:014=+, R-:014=3-
            # 2) CELDA:  012f=1+, 010e=2, 014i=3-, etc.
            if ":" in line and "=" in line:
                # Riel
                try:
                    rail_part, val = line.split("=", 1)
                    rail_code, row_str = rail_part.split(":", 1)
                    rail_code = rail_code.strip().upper()  # L+ L- R+ R-
                    row_str = row_str.strip()
                    val = val.strip() if val.strip() else EMPTY
                    if rail_code in RAIL_KEYS and row_str.isdigit() and len(row_str) == 3:
                        r = int(row_str)
                        if 1 <= r <= rows:
                            rails[rail_code][row_str] = val
                except ValueError:
                    continue
            elif "=" in line:
                # Celda
                try:
                    coord, val = line.split("=", 1)
                    coord = coord.strip().lower()
                    val = val.strip() if val.strip() else EMPTY
                    if len(coord) == 4 and coord[:3].isdigit() and coord[3] in ALL_COLS:
                        row_str = coord[:3]
                        r = int(row_str)
                        if 1 <= r <= rows:
                            col = coord[3]
                            grid[(row_str, col)] = val
                except ValueError:
                    continue
            # cualquier otra cosa se ignora silenciosamente
    return grid, rails

# ---------------- Render del tablero completo ----------------
def render_board(rows: int, grid, rails) -> str:
    lines = [header_line()]
    for r in range(1, rows + 1):
        lines.append(row_line(r, grid, rails))
    lines.append(header_line())   # <-- cabecera también al pie
    return "\n".join(lines)

# ---------------- UI (tkinter) ----------------
class ProtoBoardApp:
    def __init__(self, path: str, rows: int):
        self.path = path
        self.rows = rows
        self.last_mtime = 0.0

        self.root = tk.Tk()

        self.root.title("Protoboard Viewer")
        self.text = tk.Text(self.root, wrap="none")
        self.text.pack(fill="both", expand=True)

        # Definir tags de color
        self.text.tag_configure("rojo", foreground="red")
        self.text.tag_configure("azul", foreground="blue")
        self.text.tag_configure("jumper", foreground="orange")

        # Monoespaciada: Consolas en Windows; fallback si no está
        try:
            self.text.configure(font=tkfont.Font(family="Consolas", size=12))
        except tk.TclError:
            self.text.configure(font=("Courier New", 12))

        # Primera carga y arranque del watcher
        self.refresh(force=True)
        self.schedule_watch()

    def refresh(self, force=False):
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            mtime = -1

        if force or mtime != self.last_mtime:
            grid, rails = parse_connections(self.path, self.rows)
            board_str = render_board(self.rows, grid, rails)
            # Calcular ajuste a contenido
            lines = board_str.splitlines()
            num_cols = max(len(line) for line in lines)
            num_rows = len(lines)

            f = tkfont.Font(family="Consolas", size=12)
            char_w = f.measure("M")
            char_h = f.metrics("linespace")

            win_w = num_cols * char_w + 40
            win_h = num_rows * char_h + 40

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - win_w) // 2
            y = (screen_h - win_h) // 2

            self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

            self.text.configure(state="normal")
            self.text.delete("1.0", "end")

            # Insertar línea por línea y colorear columnas "rojo" y "azul" (encabezados y valores)

            for idx, line in enumerate(lines):
                line_start = f"{idx+1}.0"
                self.text.insert(line_start, line + "\n")

                # Colorear encabezados por nombre
                col = 0
                while True:
                    i = line.find("rojo", col)
                    if i == -1:
                        break
                    tag_start = f"{idx+1}.{i}"
                    tag_end = f"{idx+1}.{i+4}"
                    self.text.tag_add("rojo", tag_start, tag_end)
                    col = i + 4
                col = 0
                while True:
                    i = line.find("azul", col)
                    if i == -1:
                        break
                    tag_start = f"{idx+1}.{i}"
                    tag_end = f"{idx+1}.{i+4}"
                    self.text.tag_add("azul", tag_start, tag_end)
                    col = i + 4

                # Colorear jumpers (J+ o J-) en toda la línea
                col = 0
                while True:
                    i = line.find("J+", col)
                    if i == -1:
                        break
                    tag_start = f"{idx+1}.{i}"
                    tag_end = f"{idx+1}.{i+2}"
                    self.text.tag_add("jumper", tag_start, tag_end)
                    col = i + 2
                col = 0
                while True:
                    i = line.find("J-", col)
                    if i == -1:
                        break
                    tag_start = f"{idx+1}.{i}"
                    tag_end = f"{idx+1}.{i+2}"
                    self.text.tag_add("jumper", tag_start, tag_end)
                    col = i + 2

                # Colorear valores de las columnas "rojo" y "azul" (usando posiciones fijas)
                # Formato: 000 | rojo | azul | --- | ... | ... | rojo | azul |
                # Buscar los separadores "|" para ubicar las columnas
                sep_indices = [i for i, c in enumerate(line) if c == '|']
                if len(sep_indices) >= 9:
                    # Primer bloque de rojo y azul
                    rojo1_ini = sep_indices[0] + 2
                    rojo1_fin = sep_indices[1] - 1
                    azul1_ini = sep_indices[1] + 2
                    azul1_fin = sep_indices[2] - 1
                    # Segundo bloque de rojo y azul (al final)
                    rojo2_ini = sep_indices[-3] + 2
                    rojo2_fin = sep_indices[-2] - 1
                    azul2_ini = sep_indices[-2] + 2
                    azul2_fin = sep_indices[-1] - 1
                    # Aplicar tags si hay contenido
                    if rojo1_ini < rojo1_fin:
                        self.text.tag_add("rojo", f"{idx+1}.{rojo1_ini}", f"{idx+1}.{rojo1_fin}")
                    if azul1_ini < azul1_fin:
                        self.text.tag_add("azul", f"{idx+1}.{azul1_ini}", f"{idx+1}.{azul1_fin}")
                    if rojo2_ini < rojo2_fin:
                        self.text.tag_add("rojo", f"{idx+1}.{rojo2_ini}", f"{idx+1}.{rojo2_fin}")
                    if azul2_ini < azul2_fin:
                        self.text.tag_add("azul", f"{idx+1}.{azul2_ini}", f"{idx+1}.{azul2_fin}")

            self.text.configure(state="disabled")
            self.last_mtime = mtime

    def schedule_watch(self):
        # Revisa cada 1000 ms si el archivo cambia
        self.refresh()
        self.root.after(1000, self.schedule_watch)

    def run(self):
        self.root.mainloop()

def main():
    if len(sys.argv) < 2:
        print("Uso: python protoboard_app.py <ruta_conexiones.txt> [num_filas]")
        sys.exit(1)
    path = sys.argv[1]
    rows = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_ROWS
    app = ProtoBoardApp(path, rows)
    app.run()

if __name__ == "__main__":
    main()
