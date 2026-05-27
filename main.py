import os
import json
import random
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from abc import ABC, abstractmethod
import pygame

class PlayStrategy(ABC):
    @abstractmethod
    def order(self, components): pass
    @abstractmethod
    def get_name(self): pass

class SequentialPlayStrategy(PlayStrategy):
    def order(self, components): return list(components)
    def get_name(self): return "Sequential"

class RandomPlayStrategy(PlayStrategy):
    def order(self, components):
        shuffled = list(components)
        random.shuffle(shuffled)
        return shuffled
    def get_name(self): return "Random"

class ShortestFirstPlayStrategy(PlayStrategy):
    def order(self, components): return sorted(components, key=lambda c: c.get_duration())
    def get_name(self): return "ShortestFirst"

def get_strategy_by_name(name):
    strategies = {
        "Sequential": SequentialPlayStrategy(),
        "Random": RandomPlayStrategy(),
        "ShortestFirst": ShortestFirstPlayStrategy()
    }
    return strategies.get(name, SequentialPlayStrategy())

class MusicComponent(ABC):
    @abstractmethod
    def get_duration(self): pass
    @abstractmethod
    def print_structure(self, indent=0): pass
    @abstractmethod
    def get_ordered_songs(self): pass
    @abstractmethod
    def to_dict(self): pass

class Song(MusicComponent):
    def __init__(self, filename):
        self.filename = filename
        self.filepath = os.path.join("MusicDir", filename)
        self._duration = 0.0
        try:
            if os.path.exists(self.filepath):
                sound = pygame.mixer.Sound(self.filepath)
                self._duration = sound.get_length()
        except Exception:
            self._duration = 0.0

    def get_duration(self): return self._duration
    def print_structure(self, indent=0): print("  " * indent + f"- {self.filename} ({self.get_duration():.2f}s)")
    def get_ordered_songs(self): return [self]
    def to_dict(self): return {"type": "Song", "filename": self.filename}

class PlayList(MusicComponent):
    def __init__(self, name, strategy=None):
        self.name = name
        self.components = []
        self.strategy = strategy if strategy else SequentialPlayStrategy()

    def add(self, component): self.components.append(component)
    def remove(self, component):
        if component in self.components: self.components.remove(component)
    def set_strategy(self, strategy): self.strategy = strategy
    def get_duration(self): return sum(c.get_duration() for c in self.components)
    def print_structure(self, indent=0):
        print("  " * indent + f"[{self.name}] - Strategy: {self.strategy.get_name()}")
        for component in self.strategy.order(self.components):
            component.print_structure(indent + 1)
    def get_ordered_songs(self):
        result = []
        for comp in self.strategy.order(self.components):
            result.extend(comp.get_ordered_songs())
        return result
    def to_dict(self):
        return {
            "type": "PlayList", 
            "name": self.name, 
            "strategy": self.strategy.get_name(),
            "components": [c.to_dict() for c in self.components]
        }

class PlayerModel:
    def __init__(self):
        self.music_dir = "MusicDir"
        self.main_queue = []
        self.current_playback_list = []
        self.is_playing = False
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)
    
    def add_to_queue(self, component):
        self.main_queue.append(component)

    def remove_from_queue(self, index):
        if 0 <= index < len(self.main_queue):
            del self.main_queue[index]

    def prepare_playback(self):
        self.current_playback_list = []
        for comp in self.main_queue:
            self.current_playback_list.extend(comp.get_ordered_songs())
        return len(self.current_playback_list) > 0

    def get_files_by_ext(self, ext):
        return [f for f in os.listdir(self.music_dir) if f.endswith(ext)]

class PlayerView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller 
        self.root.title("Reproductor de música MATCAD")
        self.root.geometry("500x600")
        self.setup_ui()
    
    def setup_ui(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="Afegir Cançó", command=self.ui_add_song).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Afegir Llista", command=self.ui_add_playlist).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Eliminar Element", command=self.ui_remove_item).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Crear Nova Llista", command=self.ui_create_playlist).grid(row=1, column=1, padx=5, pady=5)
        
        self.tree = ttk.Treeview(self.root, columns=("Type", "Info"), show='headings')
        self.tree.heading("Type", text="Nom")
        self.tree.heading("Info", text="Info")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        play_frame = tk.Frame(self.root)
        play_frame.pack(pady=10)
        
        tk.Button(play_frame, text="▶ PLAY", command=self.controller.play_music, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(play_frame, text="⏹ STOP", command=self.controller.stop_music, bg="lightcoral").pack(side=tk.LEFT, padx=5)
        tk.Button(play_frame, text="Canviar Estratègia", command=self.ui_change_strategy).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Aturat")
        tk.Label(self.root, textvariable=self.status_var, fg="blue").pack(pady=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_close)

    def update_listbox(self, display_data):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in display_data:
            self.tree.insert("", "end", values=item)

    def update_status(self, text):
        self.status_var.set(text)

    def show_message(self, title, message):
        messagebox.showinfo(title, message)

    def ui_add_song(self):
        songs = self.controller.model.get_files_by_ext('.mp3')
        if not songs:
            self.show_message("Info", "No hi ha fitxers .mp3")
            return
            
        top = tk.Toplevel(self.root)
        listbox = tk.Listbox(top, width=40)
        listbox.pack(padx=10, pady=10)
        for s in songs: listbox.insert(tk.END, s)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                sel = listbox.get(selection[0])
                self.controller.add_song(sel)
                top.destroy()
        tk.Button(top, text="Afegir", command=on_select).pack(pady=5)

    def ui_add_playlist(self):
        lists = self.controller.model.get_files_by_ext('.m3u')
        if not lists:
            self.show_message("Info", "No hi ha fitxers .m3u")
            return
            
        top = tk.Toplevel(self.root)
        listbox = tk.Listbox(top, width=40)
        listbox.pack(padx=10, pady=10)
        for l in lists: listbox.insert(tk.END, l)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                sel = listbox.get(selection[0])
                self.controller.add_playlist(sel)
                top.destroy()
        tk.Button(top, text="Afegir", command=on_select).pack(pady=5)

    def ui_remove_item(self):
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            self.controller.remove_item(idx)

    def ui_create_playlist(self):
        name = simpledialog.askstring("Nom Llista", "Nom del fitxer (sense .m3u):")
        if not name: return
        filename = f"{name}.m3u"
        all_files = self.controller.model.get_files_by_ext('.mp3') + self.controller.model.get_files_by_ext('.m3u')
        
        top = tk.Toplevel(self.root)
        listbox = tk.Listbox(top, selectmode=tk.MULTIPLE, width=40)
        listbox.pack(padx=10, pady=10)
        for f in all_files: listbox.insert(tk.END, f)
        
        def save():
            selected = [listbox.get(i) for i in listbox.curselection()]
            self.controller.create_playlist(filename, selected)
            top.destroy()
        tk.Button(top, text="Guardar", command=save).pack(pady=5)

    def ui_change_strategy(self):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.index(selected[0])
        
        if not self.controller.is_playlist(idx):
            self.show_message("Info", "Només les llistes tenen estratègia.")
            return

        top = tk.Toplevel(self.root)
        var = tk.StringVar(value="Sequential")
        tk.Radiobutton(top, text="Seqüencial", variable=var, value="Sequential").pack(anchor=tk.W)
        tk.Radiobutton(top, text="Aleatòria", variable=var, value="Random").pack(anchor=tk.W)
        tk.Radiobutton(top, text="Més Curta", variable=var, value="ShortestFirst").pack(anchor=tk.W)
        
        def apply():
            self.controller.change_strategy(idx, var.get())
            top.destroy()
        tk.Button(top, text="Aplicar", command=apply).pack(pady=10)

class PlayerController:
    def __init__(self, root):
        self.model = PlayerModel()
        self.view = PlayerView(root, self)
        pygame.mixer.init()
        self.load_state()
        self.refresh_view()
    
    def refresh_view(self):
        display = []
        for comp in self.model.main_queue:
            if isinstance(comp, Song):
                display.append((comp.filename, f"{comp.get_duration():.1f}s"))
            else:
                display.append((f"[{comp.name}]", f"Strat: {comp.strategy.get_name()}"))
        self.view.update_listbox(display)

    def add_song(self, filename):
        self.model.add_to_queue(Song(filename))
        self.refresh_view()

    def add_playlist(self, filename):
        pl = self.build_playlist_from_m3u(filename)
        self.model.add_to_queue(pl)
        self.refresh_view()

    def remove_item(self, index):
        self.model.remove_from_queue(index)
        self.refresh_view()

    def create_playlist(self, filename, selected_files):
        with open(os.path.join(self.model.music_dir, filename), 'w') as f:
            for item in selected_files:
                f.write(item + '\n')
        self.view.show_message("Info", "Llista guardada!")

    def is_playlist(self, index):
        if 0 <= index < len(self.model.main_queue):
            return isinstance(self.model.main_queue[index], PlayList)
        return False

    def change_strategy(self, index, strategy_name):
        comp = self.model.main_queue[index]
        comp.set_strategy(get_strategy_by_name(strategy_name))
        self.refresh_view()

    def build_playlist_from_m3u(self, filename, strategy=None):
        pl = PlayList(filename, strategy)
        path = os.path.join(self.model.music_dir, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in [l.strip() for l in f.readlines() if l.strip()]:
                    if line.endswith('.mp3'): pl.add(Song(line))
                    elif line.endswith('.m3u'): pl.add(self.build_playlist_from_m3u(line))
        return pl

    def play_music(self):
        if self.model.is_playing: return
        if self.model.prepare_playback():
            self.model.is_playing = True
            self.play_next_song()
        else:
            self.view.show_message("Info", "No hi ha cançons per reproduir")

    def stop_music(self):
        self.model.is_playing = False
        pygame.mixer.music.stop()
        self.view.update_status("Aturat")

    def play_next_song(self):
        if not self.model.is_playing: return
        
        if not self.model.current_playback_list:
            self.stop_music()
            self.view.update_status("Reproducció finalitzada")
            return
            
        next_song = self.model.current_playback_list.pop(0)
        
        if os.path.exists(next_song.filepath):
            pygame.mixer.music.load(next_song.filepath)
            pygame.mixer.music.play()
            self.view.update_status(f"Sonant: {next_song.filename}")
            self.monitor_playback()
        else:
            self.play_next_song()

    def monitor_playback(self):
        if not self.model.is_playing: return
        if not pygame.mixer.music.get_busy():
            self.play_next_song()
        else:
            self.view.root.after(500, self.monitor_playback)

    def on_close(self):
        state = [comp.to_dict() for comp in self.model.main_queue]
        with open('player_state.json', 'w') as f:
            json.dump(state, f, indent=4)
        self.view.root.destroy()

    def load_state(self):
        if os.path.exists('player_state.json'):
            with open('player_state.json', 'r') as f:
                try:
                    for item in json.load(f):
                        self.model.main_queue.append(self.parse_dict_to_comp(item))
                except json.JSONDecodeError: pass

    def parse_dict_to_comp(self, d):
        if d['type'] == 'Song': return Song(d['filename'])
        elif d['type'] == 'PlayList':
            pl = PlayList(d['name'], get_strategy_by_name(d.get('strategy', 'Sequential')))
            for child in d.get('components', []):
                pl.add(self.parse_dict_to_comp(child))
            return pl

if __name__ == "__main__":
    root = tk.Tk()
    app = PlayerController(root)
    root.mainloop()
