import tkinter as tk
from tkinter import simpledialog, messagebox
import random
import json
import time

# Configuración básica
TAMANO_CELDA = 24
FILAS = 21
COLUMNAS = 21
TIEMPO_RECARGA_TRAMPA = 5.0
MAX_TRAMPAS_ACTIVAS = 3
TIEMPO_REAPARICION_ENEMIGO = 10.0
INTERVALO_TICK_MS = 250
ARCHIVO_PUNTAJES = "top_scores.json"

# Tipos de casilla
CAMINO = 0
PARED = 1
TUNEL = 2
LIANA = 3

class Posicion:
    #E: Enteros (fila, columna)
    #S:
    #R:
    #F: Representa una coordenada en la matriz
    def __init__(self, f, c):
        self.f = f
        self.c = c

    def __eq__(self, other):
        return isinstance(other, Posicion) and self.f == other.f and self.c == other.c

class Trampa:
    #E: Posicion, float
    #S:
    #R:
    #F: Representa una trampa colocada por el jugador
    def __init__(self, posicion, tiempo_colocacion):
        self.posicion = posicion
        self.tiempo_colocacion = tiempo_colocacion
        self.activa = True

class Enemigo:
    #E: Int, Posicion
    #S:
    #R:
    #F: Representa un enemigo en el juego
    def __init__(self, id_enemigo, posicion):
        self.id_enemigo = id_enemigo
        self.posicion = posicion
        self.muerto = False
        self.tiempo_muerte = None

def generar_laberinto(filas, columnas):
    #E: Enteros
    #S: Matriz de enteros
    #R: Dimensiones impares
    #F: Genera un laberinto usando DFS
    laberinto = [[PARED for _ in range(columnas)] for _ in range(filas)]

    def vecinos(celda):
        f, c = celda
        direcciones = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        random.shuffle(direcciones)
        for df, dc in direcciones:
            nf, nc = f + df, c + dc
            if 0 < nf < filas - 1 and 0 < nc < columnas - 1 and laberinto[nf][nc] == PARED:
                yield (nf, nc, df, dc)

    pila = [(1, 1)]
    laberinto[1][1] = CAMINO
    while pila:
        celda = pila[-1]
        encontrado = False
        for nf, nc, df, dc in vecinos(celda):
            if laberinto[nf][nc] == PARED:
                laberinto[celda[0] + df // 2][celda[1] + dc // 2] = CAMINO
                laberinto[nf][nc] = CAMINO
                pila.append((nf, nc))
                encontrado = True
                break
        if not encontrado:
            pila.pop()
    return laberinto

def distribuir_celdas_especiales(matriz, frac_tunel=0.03, frac_liana=0.03):
    #E: Matriz, floats
    #S:
    #R:
    #F: Convierte caminos en túneles o lianas aleatoriamente
    filas = len(matriz)
    cols = len(matriz[0])
    for f in range(1, filas - 1):
        for c in range(1, cols - 1):
            if matriz[f][c] == CAMINO:
                rnd = random.random()
                if rnd < frac_tunel:
                    matriz[f][c] = TUNEL
                elif rnd < frac_tunel + frac_liana:
                    matriz[f][c] = LIANA

def cargar_puntajes():
    #E:
    #S: Diccionario
    #R:
    #F: Carga los puntajes desde archivo JSON
    try:
        with open(ARCHIVO_PUNTAJES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"Escapa": [], "Cazador": []}

def guardar_puntajes(datos):
    #E: Diccionario
    #S:
    #R:
    #F: Guarda los puntajes en archivo JSON
    with open(ARCHIVO_PUNTAJES, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def actualizar_puntajes(modo, nombre, puntaje):
    #E: Strings, int
    #S:
    #R:
    #F: Actualiza la lista de mejores puntajes
    datos = cargar_puntajes()
    lista = datos.get(modo, [])
    lista.append({"name": nombre, "score": puntaje})
    lista = sorted(lista, key=lambda x: x["score"], reverse=True)[:5]
    datos[modo] = lista
    guardar_puntajes(datos)

class AplicacionJuego:
    #E: Tk root
    #S:
    #R:
    #F: Clase principal de la interfaz y lógica del juego
    def __init__(self, root):
        self.root = root
        root.title("Escapa / Cazador - Proyecto")

        self.nombre_jugador = None
        self.modo = None
        self.mapa = None
        self.pos_jugador = Posicion(1, 1)
        self.pos_salida = Posicion(FILAS - 2, COLUMNAS - 2)
        self.enemigos = []
        self.trampas = []
        self.tiempo_ultima_trampa = -999.0
        self.puntaje = 0
        self.tiempo_inicio = None
        self.jugando = False
        self.energia = 100
        self.energia_max = 100
        self.corriendo = False

        self.frame_superior = tk.Frame(root)
        self.frame_superior.pack(side=tk.TOP, fill=tk.X)
        self.frame_izquierdo = tk.Frame(root)
        self.frame_izquierdo.pack(side=tk.LEFT)
        self.frame_derecho = tk.Frame(root)
        self.frame_derecho.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(self.frame_superior, text="Registrar Jugador", command=self.registrar_jugador).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(self.frame_superior, text="Modo Escapa", command=lambda: self.iniciar_modo("Escapa")).pack(side=tk.LEFT, padx=4)
        tk.Button(self.frame_superior, text="Modo Cazador", command=lambda: self.iniciar_modo("Cazador")).pack(side=tk.LEFT, padx=4)
        tk.Button(self.frame_superior, text="Ver Top 5", command=self.mostrar_top5).pack(side=tk.LEFT, padx=4)
        tk.Button(self.frame_superior, text="Salir", command=root.quit).pack(side=tk.RIGHT, padx=4)

        ancho_canvas = COLUMNAS * TAMANO_CELDA
        alto_canvas = FILAS * TAMANO_CELDA
        self.canvas = tk.Canvas(self.frame_izquierdo, width=ancho_canvas, height=alto_canvas, bg="black")
        self.canvas.pack()

        self.lbl_nombre = tk.Label(self.frame_derecho, text="Jugador: -")
        self.lbl_nombre.pack(pady=6)
        self.lbl_modo = tk.Label(self.frame_derecho, text="Modo: -")
        self.lbl_modo.pack(pady=6)
        self.lbl_puntaje = tk.Label(self.frame_derecho, text="Puntaje: 0")
        self.lbl_puntaje.pack(pady=6)
        self.lbl_energia = tk.Label(self.frame_derecho, text="Energía:")
        self.lbl_energia.pack(pady=2)
        self.canvas_energia = tk.Canvas(self.frame_derecho, width=150, height=20, bg="white")
        self.canvas_energia.pack(pady=4)
        self.btn_correr = tk.Button(self.frame_derecho, text="Correr: OFF", command=self.alternar_correr)
        self.btn_correr.pack(pady=6)
        self.btn_trampa = tk.Button(self.frame_derecho, text="Colocar Trampa", command=self.colocar_trampa)
        self.btn_trampa.pack(pady=6)
        
        tk.Label(self.frame_derecho, text="Mov: WASD/Flechas\nTrampa: Botón\nCorrer: Botón").pack(pady=6)

        root.bind("<Key>", self.al_presionar_tecla)

        self.dibujar_inicio()
        cargar_puntajes()
        self.root.after(INTERVALO_TICK_MS, self.ciclo_juego)

    def dibujar_inicio(self):
        #E:
        #S:
        #R:
        #F: Dibuja pantalla inicial
        self.canvas.delete("all")
        self.canvas.create_text(COLUMNAS * TAMANO_CELDA // 2, FILAS * TAMANO_CELDA // 2, text="Registra y elige modo", fill="white", font=("Arial", 16))

    def dibujar_mapa(self):
        #E:
        #S:
        #R:
        #F: Dibuja el estado actual del juego
        self.canvas.delete("all")
        for f in range(FILAS):
            for c in range(COLUMNAS):
                x1 = c * TAMANO_CELDA
                y1 = f * TAMANO_CELDA
                x2 = x1 + TAMANO_CELDA
                y2 = y1 + TAMANO_CELDA
                tipo = self.mapa[f][c]
                color = "black"
                if tipo == PARED: color = "gray20"
                elif tipo == CAMINO: color = "lightgray"
                elif tipo == TUNEL: color = "sandybrown"
                elif tipo == LIANA: color = "darkgreen"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
        
        ex1 = self.pos_salida.c * TAMANO_CELDA
        ey1 = self.pos_salida.f * TAMANO_CELDA
        self.canvas.create_rectangle(ex1, ey1, ex1 + TAMANO_CELDA, ey1 + TAMANO_CELDA, fill="gold", outline="black")

        for t in self.trampas:
            x = t.posicion.c * TAMANO_CELDA + TAMANO_CELDA // 4
            y = t.posicion.f * TAMANO_CELDA + TAMANO_CELDA // 4
            self.canvas.create_oval(x, y, x + TAMANO_CELDA // 2, y + TAMANO_CELDA // 2, fill="red")

        for e in self.enemigos:
            if not e.muerto:
                x = e.posicion.c * TAMANO_CELDA + 3
                y = e.posicion.f * TAMANO_CELDA + 3
                self.canvas.create_rectangle(x, y, x + TAMANO_CELDA - 6, y + TAMANO_CELDA - 6, fill="blue")

        x = self.pos_jugador.c * TAMANO_CELDA + 3
        y = self.pos_jugador.f * TAMANO_CELDA + 3
        self.canvas.create_oval(x, y, x + TAMANO_CELDA - 6, y + TAMANO_CELDA - 6, fill="orange")

    def actualizar_etiquetas_ui(self):
        #E:
        #S:
        #R:
        #F: Actualiza textos y barras de la interfaz
        self.lbl_nombre.config(text=f"Jugador: {self.nombre_jugador or '-'}")
        self.lbl_modo.config(text=f"Modo: {self.modo or '-'}")
        self.lbl_puntaje.config(text=f"Puntaje: {self.puntaje}")
        
        self.canvas_energia.delete("all")
        ancho = int((self.energia / self.energia_max) * 150)
        self.canvas_energia.create_rectangle(0, 0, ancho, 20, fill="green")
        self.canvas_energia.create_rectangle(ancho, 0, 150, 20, fill="white")

    def registrar_jugador(self):
        #E:
        #S:
        #R:
        #F: Solicita nombre del jugador
        nombre = simpledialog.askstring("Registro", "Ingrese nombre de jugador (obligatorio):", parent=self.root)
        if nombre and nombre.strip():
            self.nombre_jugador = nombre.strip()
            self.lbl_nombre.config(text=f"Jugador: {self.nombre_jugador}")
        else:
            messagebox.showwarning("Registro", "Nombre obligatorio.")

    def mostrar_top5(self):
        #E:
        #S:
        #R:
        #F: Muestra mejores puntajes
        datos = cargar_puntajes()
        s = "Top 5 - Escapa\n"
        for i, e in enumerate(datos.get("Escapa", []), start=1):
            s += f"{i}. {e['name']} - {e['score']}\n"
        s += "\nTop 5 - Cazador\n"
        for i, e in enumerate(datos.get("Cazador", []), start=1):
            s += f"{i}. {e['name']} - {e['score']}\n"
        messagebox.showinfo("Top 5", s)

    def iniciar_modo(self, modo):
        #E: String
        #S:
        #R:
        #F: Inicia el juego en el modo seleccionado
        if not self.nombre_jugador:
            messagebox.showwarning("Registro", "Registre su nombre antes de jugar.")
            return
        self.modo = modo
        self.puntaje = 0
        self.corriendo = False
        self.btn_correr.config(text="Correr: OFF")
        
        self.mapa = generar_laberinto(FILAS, COLUMNAS)
        distribuir_celdas_especiales(self.mapa, frac_tunel=0.03, frac_liana=0.04)
        
        self.pos_jugador = Posicion(1, 1)
        self.pos_salida = Posicion(FILAS - 2, COLUMNAS - 2)
        
        self.enemigos = []
        num_enemigos = 3 if modo == "Escapa" else 4
        for i in range(num_enemigos):
            spawn = self.encontrar_celda_libre(cerca_borde=True)
            self.enemigos.append(Enemigo(i + 1, spawn))
            
        self.trampas = []
        self.tiempo_ultima_trampa = -999.0
        self.tiempo_inicio = time.time()
        self.jugando = True
        self.energia = self.energia_max
        
        self.dibujar_mapa()
        self.actualizar_etiquetas_ui()

    def encontrar_celda_libre(self, cerca_borde=False):
        #E: Bool
        #S: Posicion
        #R:
        #F: Encuentra una celda válida aleatoria
        candidatos = []
        for f in range(1, FILAS - 1):
            for c in range(1, COLUMNAS - 1):
                tipo = self.mapa[f][c]
                if tipo in (CAMINO, LIANA):
                    if cerca_borde:
                        if f <= 2 or c <= 2 or f >= FILAS - 3 or c >= COLUMNAS - 3:
                            candidatos.append(Posicion(f, c))
                    else:
                        candidatos.append(Posicion(f, c))
        return random.choice(candidatos) if candidatos else Posicion(1, 1)

    def al_presionar_tecla(self, event):
        #E: Evento Tk
        #S:
        #R:
        #F: Maneja input de teclado
        if not self.jugando:
            return
        tecla = event.keysym.lower()
        movimientos = {
            'w': (-1, 0), 'up': (-1, 0),
            's': (1, 0), 'down': (1, 0),
            'a': (0, -1), 'left': (0, -1),
            'd': (0, 1), 'right': (0, 1)
        }
        if tecla in movimientos:
            df, dc = movimientos[tecla]
            pasos = 2 if self.corriendo and self.energia > 0 else 1
            movido = False
            for _ in range(pasos):
                nf = self.pos_jugador.f + df
                nc = self.pos_jugador.c + dc
                if 0 <= nf < FILAS and 0 <= nc < COLUMNAS:
                    tipo = self.mapa[nf][nc]
                    if tipo in (CAMINO, TUNEL):
                        self.pos_jugador = Posicion(nf, nc)
                        movido = True
            if self.corriendo and movido:
                self.energia = max(0, self.energia - 6)
                if self.energia == 0:
                    self.corriendo = False
                    self.btn_correr.config(text="Correr: OFF")
            
            self.verificar_colisiones_movimiento()
            self.dibujar_mapa()
            self.actualizar_etiquetas_ui()

    def alternar_correr(self):
        #E:
        #S:
        #R:
        #F: Activa o desactiva modo correr
        if not self.jugando:
            return
        if self.energia <= 0:
            messagebox.showinfo("Energía", "Sin energía para correr. Espera a recuperar.")
            return
        self.corriendo = not self.corriendo
        self.btn_correr.config(text=f"Correr: {'ON' if self.corriendo else 'OFF'}")

    def colocar_trampa(self):
        #E:
        #S:
        #R:
        #F: Intenta colocar una trampa en la posición actual
        if not self.jugando:
            return
        ahora = time.time()
        activas = sum(1 for t in self.trampas if t.activa)
        if activas >= MAX_TRAMPAS_ACTIVAS:
            messagebox.showinfo("Trampa", f"Máximo {MAX_TRAMPAS_ACTIVAS} trampas activas.")
            return
        if ahora - self.tiempo_ultima_trampa < TIEMPO_RECARGA_TRAMPA:
            restante = TIEMPO_RECARGA_TRAMPA - (ahora - self.tiempo_ultima_trampa)
            messagebox.showinfo("Trampa", f"Espera {restante:.1f}s para volver a colocar.")
            return
        
        self.trampas.append(Trampa(Posicion(self.pos_jugador.f, self.pos_jugador.c), ahora))
        self.tiempo_ultima_trampa = ahora
        self.dibujar_mapa()
        self.actualizar_etiquetas_ui()

    def verificar_colisiones_movimiento(self):
        #E:
        #S:
        #R:
        #F: Verifica condiciones de victoria o derrota tras movimiento
        if self.modo == "Escapa" and self.pos_jugador == self.pos_salida:
            tiempo_transcurrido = time.time() - self.tiempo_inicio if self.tiempo_inicio else 0.0
            pts = max(10, int(1000 - tiempo_transcurrido))
            final = self.puntaje + pts
            messagebox.showinfo("Victoria", f"¡Has escapado! Puntos ganados: {pts}\nTotal: {final}")
            actualizar_puntajes("Escapa", self.nombre_jugador, final)
            self.jugando = False
            self.dibujar_mapa()
        
        for e in self.enemigos:
            if not e.muerto and e.posicion == self.pos_jugador:
                if self.modo == "Escapa":
                    messagebox.showinfo("Derrota", "Un enemigo te alcanzó. Perdiste.")
                    actualizar_puntajes("Escapa", self.nombre_jugador, self.puntaje)
                    self.jugando = False
                elif self.modo == "Cazador":
                    pts = 50
                    self.puntaje += pts
                    e.muerto = True
                    e.tiempo_muerte = time.time()
                    messagebox.showinfo("Cazador", f"Cazaste a un enemigo! +{pts} pts")
                self.dibujar_mapa()
                self.actualizar_etiquetas_ui()
                break

    def ciclo_juego(self):
        #E:
        #S:
        #R:
        #F: Loop principal del juego (tick)
        if self.jugando:
            ahora = time.time()
            if not self.corriendo:
                self.energia = min(self.energia_max, self.energia + 2)

            for e in self.enemigos:
                if e.muerto:
                    if e.tiempo_muerte and (ahora - e.tiempo_muerte >= TIEMPO_REAPARICION_ENEMIGO):
                        e.posicion = self.encontrar_celda_libre(cerca_borde=True)
                        e.muerto = False
                        e.tiempo_muerte = None
                else:
                    if self.modo == "Escapa":
                        self.mover_enemigo_hacia(e, self.pos_jugador)
                    else:
                        self.mover_enemigo_lejos(e, self.pos_jugador)
            
            for e in self.enemigos:
                if not e.muerto:
                    for t in list(self.trampas):
                        if t.activa and e.posicion == t.posicion:
                            e.muerto = True
                            e.tiempo_muerte = ahora
                            t.activa = False
                            self.puntaje += 30
            
            self.trampas = [t for t in self.trampas if t.activa or (ahora - t.tiempo_colocacion) < 0.6]

            if self.modo == "Cazador":
                for e in self.enemigos:
                    if not e.muerto and e.posicion == self.pos_salida:
                        perdida = 40
                        self.puntaje = max(0, self.puntaje - perdida)
                        e.muerto = True
                        e.tiempo_muerte = ahora
                        print(f"Enemigo escapó a la salida: -{perdida} pts")

            self.dibujar_mapa()
            self.actualizar_etiquetas_ui()

        self.root.after(INTERVALO_TICK_MS, self.ciclo_juego)

    def es_celda_enemigo_valida(self, pos):
        #E: Posicion
        #S: Bool
        #R:
        #F: Verifica si un enemigo puede estar en esa celda
        if not (0 <= pos.f < FILAS and 0 <= pos.c < COLUMNAS):
            return False
        tipo = self.mapa[pos.f][pos.c]
        return tipo in (CAMINO, LIANA)

    def mover_enemigo_hacia(self, enemigo, objetivo):
        #E: Enemigo, Posicion
        #S:
        #R:
        #F: Mueve al enemigo acercándolo al objetivo
        mejor = enemigo.posicion
        mejor_dist = abs(enemigo.posicion.f - objetivo.f) + abs(enemigo.posicion.c - objetivo.c)
        for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cand = Posicion(enemigo.posicion.f + df, enemigo.posicion.c + dc)
            if self.es_celda_enemigo_valida(cand):
                d = abs(cand.f - objetivo.f) + abs(cand.c - objetivo.c)
                if d < mejor_dist:
                    mejor_dist = d
                    mejor = cand
        enemigo.posicion = mejor

    def mover_enemigo_lejos(self, enemigo, desde_pos):
        #E: Enemigo, Posicion
        #S:
        #R:
        #F: Mueve al enemigo alejándolo de la posición
        mejor = enemigo.posicion
        opciones = []
        for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cand = Posicion(enemigo.posicion.f + df, enemigo.posicion.c + dc)
            if self.es_celda_enemigo_valida(cand):
                d = abs(cand.f - desde_pos.f) + abs(cand.c - desde_pos.c)
                opciones.append((d, cand))
        if opciones:
            opciones.sort(key=lambda x: x[0], reverse=True)
            mejor = opciones[0][1]
        enemigo.posicion = mejor

if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionJuego(root)
    root.mainloop()
