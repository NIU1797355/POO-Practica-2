import os
import json
import random
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from abc import ABC, abstractmethod
import pygame

class PlayStrategy(ABC):
    @abstractmethod
    def order(self, components):
        pass
    
    @abstractmethod
    def get_name(self):
        pass

class SequentialPlayStrategy(PlayStrategy):
    def order(self, components):
        return list(components)
    
    def get_name(self):
        return "Sequential"

class RandomPlayStrategy(PlayStrategy):
    def order(self, components):
        shuffled = list(components)
        random.shuffle(shuffled)
        return shuffled
    
    def get_name(self):
        return "Random"

class ShortestFirstPlayStrategy(PlayStrategy):
    def order(self, components):
        return sorted(components, key=lambda c: c.get_duration())
    
    def get_name(self):
        return "ShortestFirst"

def get_strategy_by_name(name):
    strategies = {
        "Sequential": SequentialPlayStrategy(),
        "Random": RandomPlayStrategy(),
        "ShortestFirst": ShortestFirstPlayStrategy()
    }
    return strategies.get(name, SequentialPlayStrategy())

class MusicComponent(ABC):
    @abstractmethod
    def get_duration(self):
        pass
    
    @abstractmethod
    def print_structure(self, indent=0):
        pass
        
    @abstractmethod
    def get_ordered_songs(self):
        pass

    @abstractmethod
    def to_dict(self):
        pass

class Song(MusicComponent):
    def __init__(self, filename):
        self.filename = filename
        self.filepath = os.path.join("MusicDir", filename)
        self._duration = 0.0

        try:
            if os.path.exists(self.filepath):
                sound = pygame.mixer.Sound(self.filepath)
                self._duration = sound.get_length()
        except:
            self._duration = 0.0

    def get_duration(self):
        return self._duration

    def print_structure(self, indent=0):
        print("  " * indent + f"- {self.filename} ({self.get_duration():.2f}s)")

    def get_ordered_songs(self):
        return [self]

    def to_dict(self):
        return {"type": "Song", "filename": self.filename}

class PlayList(MusicComponent):
    def __init__(self, name, strategy=None):
        self.name = name
        self.components = []
        self.strategy = strategy if strategy else SequentialPlayStrategy()

    def add(self, component):
        self.components.append(component)

    def remove(self, component):
        if component in self.components:
            self.components.remove(component)

    def set_strategy(self, strategy):
        self.strategy = strategy

    def get_duration(self):
        return sum(c.get_duration() for c in self.components)

    def print_structure(self, indent=0):
        print("  " * indent + f"[{self.name}] - Strategy: {self.strategy.get_name()}")
        for component in self.strategy.order(self.components):
            component.print_structure(indent + 1)

    def get_ordered_songs(self):
        ordered_comps = self.strategy.order(self.components)
        
        result = []
        for comp in ordered_comps:
            result.extend(comp.get_ordered_songs())
        return result

    def to_dict(self):
        return {
            "type": "PlayList", 
            "name": self.name, 
            "strategy": self.strategy.get_name(),
            "components": [c.to_dict() for c in self.components]
        }

class MusicPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reproductor de Música MATCAD-UAB")
        self.root.geometry("500x600")
        
        pygame.mixer.init()
        
        self.music_dir = "MusicDir"
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)
            
        self.main_queue = []
        self.current_playback_list = []
        self.is_playing = False
        
        self.setup_ui()
        self.load_state()
        self.update_listbox()
        
    def setup_ui(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="Afegir Cançó (mp3)", command=self.add_song_uc1).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Afegir Llista (m3u)", command=self.add_playlist_uc2).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(btn_frame, text="Eliminar Element", command=self.remove_item_uc3).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Crear Nova Llista", command=self.create_playlist_uc4).grid(row=1, column=1, padx=5, pady=5)
        
        self.tree = ttk.Treeview(self.root, columns=("Type", "Strategy/Duration"), show='headings')
        self.tree.heading("Type", text="Nom")
        self.tree.heading("Strategy/Duration", text="Info")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        play_frame = tk.Frame(self.root)
        play_frame.pack(pady=10)
        
        tk.Button(play_frame, text="▶ PLAY", command=self.play_music_uc5, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(play_frame, text="⏹ STOP", command=self.stop_music, bg="lightcoral").pack(side=tk.LEFT, padx=5)
        tk.Button(play_frame, text="Cambiar Estrategia Llista", command=self.change_strategy).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Aturat")
        tk.Label(self.root, textvariable=self.status_var, fg="blue").pack(pady=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def get_files_by_ext(self, ext):
        return [f for f in os.listdir(self.music_dir) if f.endswith(ext)]

    def build_playlist_from_m3u(self, filename, strategy=None):
        pl = PlayList(filename, strategy)
        path = os.path.join(self.music_dir, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                for line in lines:
                    if line.endswith('.mp3'):
                        pl.add(Song(line))
                    elif line.endswith('.m3u'):
                        pl.add(self.build_playlist_from_m3u(line))
        return pl

    def add_song_uc1(self):
        songs = self.get_files_by_ext('.mp3')
        if not songs:
            messagebox.showinfo("Info", "No hi ha fitxers .mp3 a MusicDir")
            return
            
        def on_select():
            sel = listbox.get(tk.ACTIVE)
            if sel:
                self.main_queue.append(Song(sel))
                self.update_listbox()
            top.destroy()
            
        top = tk.Toplevel(self.root)
        top.title("Selecciona Cançó")
        listbox = tk.Listbox(top, width=40)
        listbox.pack(padx=10, pady=10)
        for s in songs: listbox.insert(tk.END, s)
        tk.Button(top, text="Afegir", command=on_select).pack(pady=5)

    def add_playlist_uc2(self):
        lists = self.get_files_by_ext('.m3u')
        if not lists:
            messagebox.showinfo("Info", "No hi ha fitxers .m3u a MusicDir")
            return
            
        def on_select():
            sel = listbox.get(tk.ACTIVE)
            if sel:
                pl = self.build_playlist_from_m3u(sel)
                self.main_queue.append(pl)
                self.update_listbox()
            top.destroy()
            
        top = tk.Toplevel(self.root)
        top.title("Selecciona Llista")
        listbox = tk.Listbox(top, width=40)
        listbox.pack(padx=10, pady=10)
        for l in lists: listbox.insert(tk.END, l)
        tk.Button(top, text="Afegir", command=on_select).pack(pady=5)

    def remove_item_uc3(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        if 0 <= idx < len(self.main_queue):
            del self.main_queue[idx]
            self.update_listbox()

    def create_playlist_uc4(self):
        name = simpledialog.askstring("Nom Llista", "Nom del fitxer de la nova llista (sense .m3u):")
        if not name: return
        filename = f"{name}.m3u"
        
        all_files = self.get_files_by_ext('.mp3') + self.get_files_by_ext('.m3u')
        
        top = tk.Toplevel(self.root)
        top.title(f"Afegeix a {filename}")
        listbox = tk.Listbox(top, selectmode=tk.MULTIPLE, width=40)
        listbox.pack(padx=10, pady=10)
        for f in all_files: listbox.insert(tk.END, f)
        
        def save_m3u():
            selected_indices = listbox.curselection()
            with open(os.path.join(self.music_dir, filename), 'w') as f:
                for idx in selected_indices:
                    f.write(listbox.get(idx) + '\n')
            messagebox.showinfo("Info", "Llista guardada!")
            top.destroy()
            
        tk.Button(top, text="Guardar Fitxer", command=save_m3u).pack(pady=5)

    def play_music_uc5(self):
        if self.is_playing: return
        
        self.current_playback_list = []
        for comp in self.main_queue:
            self.current_playback_list.extend(comp.get_ordered_songs())
            
        if not self.current_playback_list:
            messagebox.showinfo("Info", "No hi ha cançons per reproduir")
            return
            
        self.is_playing = True
        self.play_next_song()

    def play_next_song(self):
        if not self.is_playing: return
        
        if not self.current_playback_list:
            self.stop_music()
            self.status_var.set("Reproducció finalitzada")
            return
            
        next_song = self.current_playback_list.pop(0)
        
        if os.path.exists(next_song.filepath):
            pygame.mixer.music.load(next_song.filepath)
            pygame.mixer.music.play()
            self.status_var.set(f"Sonant: {next_song.filename}")
            self.monitor_playback()
        else:
            print(f"Fitxer no trobat: {next_song.filepath}")
            self.play_next_song()

    def monitor_playback(self):
        if not self.is_playing: return
        if not pygame.mixer.music.get_busy():
            self.play_next_song()
        else:
            self.root.after(500, self.monitor_playback)

    def stop_music(self):
        self.is_playing = False
        pygame.mixer.music.stop()
        self.status_var.set("Aturat")

    def change_strategy(self):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.index(selected[0])
        comp = self.main_queue[idx]
        
        if isinstance(comp, PlayList):
            top = tk.Toplevel(self.root)
            top.title("Tria Estratègia")
            var = tk.StringVar(value=comp.strategy.get_name())
            
            tk.Radiobutton(top, text="Seqüencial", variable=var, value="Sequential").pack(anchor=tk.W)
            tk.Radiobutton(top, text="Aleatòria", variable=var, value="Random").pack(anchor=tk.W)
            tk.Radiobutton(top, text="Més Curta Primer", variable=var, value="ShortestFirst").pack(anchor=tk.W)
            
            def apply():
                comp.set_strategy(get_strategy_by_name(var.get()))
                self.update_listbox()
                top.destroy()
                
            tk.Button(top, text="Aplicar", command=apply).pack(pady=10)
        else:
            messagebox.showinfo("Info", "Les cançons individuals no tenen estratègia.")

    def update_listbox(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for comp in self.main_queue:
            if isinstance(comp, Song):
                self.tree.insert("", "end", values=(comp.filename, f"{comp.get_duration():.1f}s"))
            else:
                self.tree.insert("", "end", values=(f"[{comp.name}]", f"Strat: {comp.strategy.get_name()}"))
                
        print("\n--- Estat Actual del Reproductor ---")
        for comp in self.main_queue:
            comp.print_structure()

    def parse_dict_to_comp(self, d):
        if d['type'] == 'Song':
            return Song(d['filename'])
        elif d['type'] == 'PlayList':
            pl = PlayList(d['name'], get_strategy_by_name(d.get('strategy', 'Sequential')))
            for child in d.get('components', []):
                pl.add(self.parse_dict_to_comp(child))
            return pl

    def on_close(self):
        state = [comp.to_dict() for comp in self.main_queue]
        with open('player_state.json', 'w') as f:
            json.dump(state, f, indent=4)
        self.root.destroy()

    def load_state(self):
        if os.path.exists('player_state.json'):
            with open('player_state.json', 'r') as f:
                try:
                    state = json.load(f)
                    for item in state:
                        self.main_queue.append(self.parse_dict_to_comp(item))
                except json.JSONDecodeError:
                    pass

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayerApp(root)
    root.mainloop()
