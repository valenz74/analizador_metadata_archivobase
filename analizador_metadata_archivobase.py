# pdf_metadata_analyzer_auto_cache.py
import os
import hashlib
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from datetime import datetime, timedelta
import fitz  # PyMuPDF
import webbrowser
import time
import json
import winsound

class PDFMetadataAnalyzer:
    def __init__(self):
        self.reference_file = None
        self.search_folder = None
        self.cache_file = Path("C:/Users/Jose/Proyectos/analizador_metadata_archivobase/cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_folder_modification_time(self, folder_path):
        """Obtiene el tiempo de modificación de una carpeta recursivamente"""
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return None
            
            # Obtener el tiempo de modificación de la carpeta principal
            latest_time = folder.stat().st_mtime
            
            # Buscar recursivamente en subcarpetas
            for item in folder.rglob('*'):
                if item.is_file():
                    item_time = item.stat().st_mtime
                    if item_time > latest_time:
                        latest_time = item_time
            
            return latest_time
        except Exception as e:
            print(f"Error obteniendo tiempo de modificación de carpeta: {e}")
            return None
    
    def load_cache(self, search_folder):
        """Carga el caché si existe y es válido - Ahora completamente automático"""
        try:
            if not self.cache_file.exists():
                return None, "No existe archivo de caché"
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Verificar si la carpeta es la misma
            cached_folder = cache_data.get('search_folder')
            if cached_folder != search_folder:
                return None, "Carpeta diferente"
            
            # Verificar si la carpeta ha sido modificada
            current_mod_time = self.get_folder_modification_time(search_folder)
            cached_mod_time = cache_data.get('folder_modification_time')
            
            if current_mod_time != cached_mod_time:
                return None, "Carpeta modificada"
            
            # Verificar integridad de los archivos en caché
            pdf_files = cache_data.get('pdf_files', {})
            for file_path, file_data in pdf_files.items():
                if not Path(file_path).exists():
                    return None, "Archivo en caché no existe"
                
                # Verificar si el archivo ha sido modificado
                current_file_time = Path(file_path).stat().st_mtime
                cached_file_time = file_data.get('modification_time')
                if current_file_time != cached_file_time:
                    return None, "Archivo modificado"
            
            return pdf_files, "Caché válido"
            
        except Exception as e:
            print(f"Error cargando caché: {e}")
            return None, f"Error: {str(e)}"
    
    def save_cache(self, search_folder, pdf_files):
        """Guarda los metadatos en caché"""
        try:
            # Convertir objetos datetime a strings para serialización JSON
            serializable_pdf_files = {}
            for file_path, file_data in pdf_files.items():
                serializable_data = file_data.copy()
                # Convertir datetime a string ISO format
                if isinstance(serializable_data.get('modificado'), datetime):
                    serializable_data['modificado'] = serializable_data['modificado'].isoformat()
                serializable_pdf_files[file_path] = serializable_data
            
            cache_data = {
                'search_folder': search_folder,
                'folder_modification_time': self.get_folder_modification_time(search_folder),
                'cache_timestamp': time.time(),
                'cache_date': datetime.now().isoformat(),
                'total_files': len(pdf_files),
                'pdf_files': serializable_pdf_files
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"Caché guardado exitosamente: {len(pdf_files)} archivos")
            
        except Exception as e:
            print(f"Error guardando caché: {e}")
    
    def get_pdf_metadata(self, pdf_path):
        """Extrae metadatos completos de un PDF"""
        try:
            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
                
                # Calcular hash SHA256 (solo para información, no para comparación)
                with open(pdf_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                # Obtener información del sistema de archivos
                file_stat = pdf_path.stat()
                file_size = file_stat.st_size
                file_modified = datetime.fromtimestamp(file_stat.st_mtime)
                
                # Formatear fecha de creación
                creation_date = self.format_pdf_date(metadata.get('creationDate', 'No disponible'))
                mod_date = self.format_pdf_date(metadata.get('modDate', 'No disponible'))
                
                # Información completa
                full_metadata = {
                    'ruta': str(pdf_path),
                    'nombre': pdf_path.name,
                    'tamaño': file_size,
                    'modificado': file_modified,
                    'hash_sha256': file_hash,
                    'creador': metadata.get('creator', 'No disponible'),
                    'productor': metadata.get('producer', 'No disponible'),
                    'titulo': metadata.get('title', 'No disponible'),
                    'asunto': metadata.get('subject', 'No disponible'),
                    'palabras_clave': metadata.get('keywords', 'No disponible'),
                    'fecha_creacion': creation_date,
                    'fecha_modificacion': mod_date,
                    'paginas': len(doc),
                    'modification_time': file_stat.st_mtime
                }
                
                return True, full_metadata
                
        except Exception as e:
            return False, f"Error al leer metadatos: {str(e)}"
    
    def format_pdf_date(self, pdf_date_string):
        """Convierte el formato de fecha PDF a formato legible"""
        if pdf_date_string == 'No disponible' or not pdf_date_string:
            return 'No disponible'
        
        try:
            if pdf_date_string.startswith('D:'):
                date_str = pdf_date_string[2:]
                
                year = int(date_str[0:4]) if len(date_str) >= 4 else 2024
                month = int(date_str[4:6]) if len(date_str) >= 6 else 1
                day = int(date_str[6:8]) if len(date_str) >= 8 else 1
                hour = int(date_str[8:10]) if len(date_str) >= 10 else 0
                minute = int(date_str[10:12]) if len(date_str) >= 12 else 0
                second = int(date_str[12:14]) if len(date_str) >= 14 else 0
                
                pdf_date = datetime(year, month, day, hour, minute, second)
                return pdf_date.strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            print(f"Error formateando fecha PDF: {pdf_date_string}, Error: {e}")
        
        return pdf_date_string
    
    def normalize_metadata_value(self, value):
        """Normaliza valores de metadatos para comparación"""
        if value == 'No disponible' or not value:
            return None
        return str(value).strip().lower()
    
    def find_similar_by_metadata(self, reference_metadata, search_folder, include_hash=False, min_matches=2, progress_callback=None):
        """Busca PDFs con metadatos similares - Ahora con caché automático"""
        similar_files = []
        pdf_files_data = {}
        cache_used = False
        
        # SIEMPRE intentar cargar desde caché primero
        cached_data, cache_status = self.load_cache(search_folder)
        if cached_data:
            pdf_files_data = cached_data
            cache_used = True
            print(f"✓ Caché automático: {cache_status}")
            
            # Convertir strings de fecha de vuelta a objetos datetime para archivos en caché
            for file_path, file_data in pdf_files_data.items():
                if 'modificado' in file_data and isinstance(file_data['modificado'], str):
                    try:
                        pdf_files_data[file_path]['modificado'] = datetime.fromisoformat(file_data['modificado'])
                    except:
                        # Si falla la conversión, mantener el string
                        pass
        else:
            print(f"✗ Caché no disponible: {cache_status}")
            # Escanear archivos si el caché no es válido
            pdf_files = [f for f in Path(search_folder).rglob("*.pdf") 
                        if not f.name.startswith('~$')]
            total_files = len(pdf_files)
            
            for i, pdf_file in enumerate(pdf_files):
                if progress_callback and hasattr(progress_callback, '__call__'):
                    progress_callback(i, total_files, f"Analizando: {pdf_file.name}")
                
                success, metadata = self.get_pdf_metadata(pdf_file)
                if success:
                    pdf_files_data[str(pdf_file)] = metadata
                
                if i % 10 == 0:
                    print(f"Escaneando: {i}/{total_files} archivos")
            
            # GUARDAR CACHÉ automáticamente después del escaneo
            self.save_cache(search_folder, pdf_files_data)
        
        # Normalizar metadatos de referencia
        ref_creator = self.normalize_metadata_value(reference_metadata.get('creador'))
        ref_producer = self.normalize_metadata_value(reference_metadata.get('productor'))
        ref_creation_date = self.normalize_metadata_value(reference_metadata.get('fecha_creacion'))
        ref_hash = reference_metadata.get('hash_sha256') if include_hash else None
        
        total_files_to_compare = len(pdf_files_data)
        
        # Buscar coincidencias
        for i, (file_path, metadata) in enumerate(pdf_files_data.items()):
            if file_path == self.reference_file:
                continue
            
            if progress_callback and hasattr(progress_callback, '__call__'):
                progress_callback(i, total_files_to_compare, f"Comparando: {Path(file_path).name}")
            
            comp_creator = self.normalize_metadata_value(metadata.get('creador'))
            comp_producer = self.normalize_metadata_value(metadata.get('productor'))
            comp_creation_date = self.normalize_metadata_value(metadata.get('fecha_creacion'))
            comp_hash = metadata.get('hash_sha256') if include_hash else None
            
            matches = 0
            total_possible = 3 + (1 if include_hash else 0)
            match_details = []
            
            # Campos base
            creator_match = False
            producer_match = False  
            creation_date_match = False
            hash_match = False
            
            if ref_creator and comp_creator and ref_creator == comp_creator:
                matches += 1
                creator_match = True
                match_details.append("✓ Creator")
            else:
                match_details.append("✗ Creator")
            
            if ref_producer and comp_producer and ref_producer == comp_producer:
                matches += 1
                producer_match = True
                match_details.append("✓ Producer")
            else:
                match_details.append("✗ Producer")
            
            if ref_creation_date and comp_creation_date and ref_creation_date == comp_creation_date:
                matches += 1
                creation_date_match = True
                match_details.append("✓ Create Date")
            else:
                match_details.append("✗ Create Date")
            
            if include_hash:
                if ref_hash and comp_hash and ref_hash == comp_hash:
                    matches += 1
                    hash_match = True
                    match_details.append("✓ Hash SHA256")
                else:
                    match_details.append("✗ Hash SHA256")
            
            # 🔥 NUEVA LÓGICA MEJORADA para detección de trampas
            similarity_level = "BAJA"
            is_similar = False
            
            if min_matches == 1:  # Nivel Bajo - Cualquier coincidencia
                is_similar = matches >= 1
                similarity_level = "BAJA"
            
            elif min_matches == 2:  # Nivel Medio - CREATE DATE OBLIGATORIO
                # Requiere Create Date + al menos otro campo
                if creation_date_match and (creator_match or producer_match or (include_hash and hash_match)):
                    is_similar = True
                    similarity_level = "MEDIA"
                else:
                    is_similar = False
            
            elif min_matches >= 3:  # Nivel Alto - Todas las coincidencias
                is_similar = matches >= min_matches
                similarity_level = "ALTA"
            
            if is_similar:
                similar_files.append({
                    'metadata': metadata,
                    'matches': matches,
                    'total_possible': total_possible,
                    'similarity_level': similarity_level,
                    'match_details': match_details,
                    'ruta_completa': file_path,
                    'from_cache': cache_used
                })
        
        similar_files.sort(key=lambda x: x['matches'], reverse=True)
        return similar_files, cache_used

class PDFSearchTab:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.is_searching = False
        self.stop_search = False
        self.cache_file = Path("C:/Users/Jose/Proyectos/analizador_metadata_archivobase/cache_text.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.setup_search_tab()
    
    def get_folder_modification_time(self, folder_path):
        """Obtiene el tiempo de modificación de una carpeta recursivamente"""
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return None
            
            # Obtener el tiempo de modificación de la carpeta principal
            latest_time = folder.stat().st_mtime
            
            # Buscar recursivamente en subcarpetas
            for item in folder.rglob('*'):
                if item.is_file():
                    item_time = item.stat().st_mtime
                    if item_time > latest_time:
                        latest_time = item_time
            
            return latest_time
        except Exception as e:
            print(f"Error obteniendo tiempo de modificación de carpeta: {e}")
            return None
    
    def load_text_cache(self, search_folder):
        """Carga el caché de texto si existe y es válido"""
        try:
            if not self.cache_file.exists():
                return None, "No existe archivo de caché de texto"
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Verificar si la carpeta es la misma
            cached_folder = cache_data.get('search_folder')
            if cached_folder != search_folder:
                return None, "Carpeta diferente"
            
            # Verificar si la carpeta ha sido modificada
            current_mod_time = self.get_folder_modification_time(search_folder)
            cached_mod_time = cache_data.get('folder_modification_time')
            
            if current_mod_time != cached_mod_time:
                return None, "Carpeta modificada"
            
            # Verificar integridad de los archivos en caché
            text_cache = cache_data.get('text_cache', {})
            for file_path, file_data in text_cache.items():
                if not Path(file_path).exists():
                    return None, "Archivo en caché no existe"
                
                # Verificar si el archivo ha sido modificado
                current_file_time = Path(file_path).stat().st_mtime
                cached_file_time = file_data.get('modification_time')
                if current_file_time != cached_file_time:
                    return None, "Archivo modificado"
            
            return text_cache, "Caché de texto válido"
            
        except Exception as e:
            print(f"Error cargando caché de texto: {e}")
            return None, f"Error: {str(e)}"
    
    def save_text_cache(self, search_folder, text_cache):
        """Guarda el texto extraído en caché"""
        try:
            cache_data = {
                'search_folder': search_folder,
                'folder_modification_time': self.get_folder_modification_time(search_folder),
                'cache_timestamp': time.time(),
                'cache_date': datetime.now().isoformat(),
                'total_files': len(text_cache),
                'text_cache': text_cache
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"Caché de texto guardado exitosamente: {len(text_cache)} archivos")
            
        except Exception as e:
            print(f"Error guardando caché de texto: {e}")
    
    def setup_search_tab(self):
        # Variables
        self.folder_path = tk.StringVar()
        self.search_text = tk.StringVar()
        
        # Marco principal de búsqueda
        search_main_frame = ttk.Frame(self.parent)
        search_main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(search_main_frame, 
                               text="🔍 Buscador de Texto en PDFs - Con Caché Automático", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Frame de selección
        selection_frame = ttk.LabelFrame(search_main_frame, text="Configuración de Búsqueda", padding="10")
        selection_frame.pack(fill=tk.X, pady=5)
        
        # Selección de carpeta
        ttk.Label(selection_frame, text="Carpeta:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_entry = ttk.Entry(selection_frame, textvariable=self.folder_path, width=60)
        folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(selection_frame, text="📁 Seleccionar Carpeta", 
                  command=self.select_folder).grid(row=0, column=2, pady=5)
        
        # Texto de búsqueda
        ttk.Label(selection_frame, text="Texto a buscar:").grid(row=1, column=0, sticky=tk.W, pady=5)
        search_entry = ttk.Entry(selection_frame, textvariable=self.search_text, width=60)
        search_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Frame para botones de búsqueda
        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=1, column=2, pady=5)
        
        self.search_button = ttk.Button(button_frame, text="🔍 Buscar", 
                                       command=self.start_search)
        self.search_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Detener", 
                                     command=self.stop_search_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        selection_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        progress_frame = ttk.Frame(search_main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # Label de estado
        self.status_label = ttk.Label(progress_frame, text="Listo para buscar")
        self.status_label.pack(pady=2)
        
        # Lista de resultados
        results_frame = ttk.LabelFrame(search_main_frame, text="Resultados de Búsqueda", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Frame para controles de resultados
        results_controls = ttk.Frame(results_frame)
        results_controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(results_controls, text="Archivos encontrados:").pack(side=tk.LEFT)
        
        # Botón siempre habilitado
        self.open_selected_btn = ttk.Button(results_controls, text="📖 Abrir Seleccionado", 
                                          command=self.open_selected_file, state=tk.NORMAL)
        self.open_selected_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Listbox con scrollbar
        listbox_frame = ttk.Frame(results_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_list = tk.Listbox(listbox_frame, width=80, height=15)
        self.results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.results_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_list.configure(yscrollcommand=scrollbar.set)
        
        # Bind para abrir archivo con doble click
        self.results_list.bind('<Double-Button-1>', lambda e: self.open_selected_file())
    
    def select_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta para buscar en PDFs")
        if folder:
            self.folder_path.set(folder)
    
    def start_search(self):
        if not self.folder_path.get():
            messagebox.showwarning("Advertencia", "Selecciona una carpeta primero")
            return
            
        if not self.search_text.get().strip():
            messagebox.showwarning("Advertencia", "Ingresa un texto a buscar")
            return
        
        # Limpiar resultados anteriores
        self.results_list.delete(0, tk.END)
        
        # Configurar interfaz para búsqueda
        self.is_searching = True
        self.stop_search = False
        self.search_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start(10)
        self.status_label.config(text="Buscando...")
        
        # Ejecutar búsqueda en hilo separado
        search_thread = threading.Thread(target=self.search_pdfs_thread)
        search_thread.daemon = True
        search_thread.start()
        
        # Verificar estado del hilo periódicamente
        self.check_search_thread()
    
    def stop_search_process(self):
        self.stop_search = True
        self.status_label.config(text="Deteniendo búsqueda...")
    
    def check_search_thread(self):
        if self.is_searching:
            # Revisar nuevamente en 100ms
            self.parent.after(100, self.check_search_thread)
        else:
            # La búsqueda terminó
            self.progress.stop()
            self.search_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def search_pdfs_thread(self):
        try:
            found_files = []
            search_string = self.search_text.get().strip()
            
            # Excluir archivos temporales que comienzan con ~$
            pdf_files = [f for f in Path(self.folder_path.get()).rglob("*.pdf") 
                        if not f.name.startswith('~$')]
            total_files = len(pdf_files)
            
            # 🔥 NUEVO: CARGAR CACHÉ DE TEXTO
            text_cache = {}
            cache_used = False
            
            cached_data, cache_status = self.load_text_cache(self.folder_path.get())
            if cached_data:
                text_cache = cached_data
                cache_used = True
                print(f"✓ Caché de texto: {cache_status}")
                self.parent.after(0, lambda: self.status_label.config(text=f"Usando caché de texto - Buscando en {len(text_cache)} archivos..."))
            else:
                print(f"✗ Caché de texto no disponible: {cache_status}")
                # Si no hay caché válido, extraer texto de todos los archivos
                text_cache = {}
                for i, pdf_file in enumerate(pdf_files):
                    if self.stop_search:
                        break
                        
                    self.parent.after(0, lambda f=pdf_file.name, i=i, total=total_files: 
                                   self.status_label.config(text=f"Extrayendo texto {i+1}/{total_files}: {f}"))
                    
                    try:
                        with fitz.open(pdf_file) as doc:
                            text = ""
                            for page in doc:
                                if self.stop_search:
                                    break
                                text += page.get_text()
                            
                            text_cache[str(pdf_file)] = {
                                'full_text': text,
                                'modification_time': pdf_file.stat().st_mtime
                            }
                            
                    except Exception as e:
                        print(f"Error leyendo {pdf_file}: {str(e)}")
                
                # Guardar caché de texto
                self.save_text_cache(self.folder_path.get(), text_cache)
            
            # 🔥 BÚSQUEDA EN CACHÉ DE TEXTO (MUY RÁPIDO)
            self.parent.after(0, lambda: self.status_label.config(text="Buscando en caché de texto..."))
            
            for file_path, text_data in text_cache.items():
                if self.stop_search:
                    break
                
                if search_string.lower() in text_data['full_text'].lower():
                    found_files.append(file_path)
                    # Actualizar lista en el hilo principal
                    self.parent.after(0, lambda f=file_path: self.results_list.insert(tk.END, f))
            
            # Mostrar resultados finales
            self.parent.after(0, self.show_search_results, found_files, self.stop_search, cache_used)
            
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Error durante la búsqueda: {str(e)}"))
        finally:
            self.is_searching = False
    
    def show_search_results(self, found_files, was_cancelled, cache_used):
        cache_status = " (con caché)" if cache_used else " (sin caché - escaneo completo)"
        
        if was_cancelled:
            self.status_label.config(text=f"Búsqueda cancelada. Se encontraron {len(found_files)} archivos{cache_status}")
            messagebox.showinfo("Búsqueda cancelada", f"Se encontraron {len(found_files)} archivos antes de cancelar")
        elif found_files:
            self.status_label.config(text=f"Búsqueda completada. Se encontraron {len(found_files)} archivos{cache_status}")
            messagebox.showinfo("Resultados", f"Se encontraron {len(found_files)} archivos con el texto")
        else:
            self.status_label.config(text=f"Búsqueda completada. No se encontraron archivos{cache_status}")
            messagebox.showinfo("Resultados", "No se encontraron archivos con el texto buscado")
    
    def open_selected_file(self):
        selection = self.results_list.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Selecciona un archivo de la lista")
            return
            
        file_path = self.results_list.get(selection[0])
        try:
            os.startfile(file_path)
        except:
            try:
                webbrowser.open(file_path)
            except:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {file_path}")

class MetadataAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Metadatos - Caché Automático + Buscador de Texto")
        self.root.geometry("1400x1000")
        
        self.analyzer = PDFMetadataAnalyzer()
        self.reference_metadata = None
        self.detected_files = []
        self.analysis_start_time = None
        self.is_analyzing = False
        self.total_estimated_time = None
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(main_frame, 
                               text="Analizador de Metadatos de PDFs - Caché Automático + Buscador de Texto", 
                               font=("Arial", 14, "bold"),
                               justify=tk.CENTER)
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        selection_frame = ttk.LabelFrame(main_frame, text="Selección de Archivos", padding="10")
        selection_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        selection_frame.columnconfigure(1, weight=1)
        
        ttk.Label(selection_frame, text="PDF de referencia:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reference_entry = ttk.Entry(selection_frame)
        self.reference_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        
        reference_buttons_frame = ttk.Frame(selection_frame)
        reference_buttons_frame.grid(row=0, column=2, pady=5)
        
        ttk.Button(reference_buttons_frame, text="📄 Seleccionar PDF", 
                  command=self.select_reference).pack(side=tk.LEFT, padx=(0, 5))
        self.open_reference_btn = ttk.Button(reference_buttons_frame, text="📖 Abrir Referencia", 
                                           command=self.open_reference_file, state='disabled')
        self.open_reference_btn.pack(side=tk.LEFT)
        
        ttk.Label(selection_frame, text="Carpeta de búsqueda:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.folder_entry = ttk.Entry(selection_frame)
        self.folder_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(selection_frame, text="📁 Seleccionar Carpeta", command=self.select_search_folder).grid(row=1, column=2, pady=5)
        
        config_frame = ttk.LabelFrame(main_frame, text="Configuración de Búsqueda", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)
        
        left_config = ttk.Frame(config_frame)
        left_config.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        self.include_hash_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left_config, text="Incluir Hash SHA256 en la comparación", 
                       variable=self.include_hash_var).pack(anchor=tk.W, pady=2)
        
        ttk.Label(left_config, text="Nivel de detección:").pack(anchor=tk.W, pady=(10, 5))
        
        self.similarity_var = tk.StringVar(value="media")  # PREDETERMINADO: MEDIA
        similarity_frame = ttk.Frame(left_config)
        similarity_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(similarity_frame, text="Baja (1+ coincidencia)", 
                       variable=self.similarity_var, value="baja").pack(side=tk.LEFT)
        ttk.Radiobutton(similarity_frame, text="Media (Create Date + otro campo)", 
                       variable=self.similarity_var, value="media").pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(similarity_frame, text="Alta (3+ coincidencias)", 
                       variable=self.similarity_var, value="alta").pack(side=tk.LEFT, padx=(20, 0))
        
        right_config = ttk.Frame(config_frame)
        right_config.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        info_text = (
            "💡 SISTEMA DE CACHÉ AUTOMÁTICO:\n"
            "• Siempre usa caché cuando es válido\n"
            "• Regenera automáticamente si hay cambios\n"
            "• No requiere configuración manual\n"
            "• Ubicación: C:/Users/Jose/Proyectos/analizador_metadata_archivobase/\n\n"
            "🎯 RECOMENDACIÓN (PREDETERMINADO):\n"
            "• 'Media' para máxima detección de trampas\n"
            "• Create Date + otro campo\n"
            "• Hash solo para archivos idénticos"
        )
        ttk.Label(right_config, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        progress_frame = ttk.LabelFrame(main_frame, text="Progreso del Análisis", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        progress_frame.columnconfigure(1, weight=1)
        
        self.progress_indicator = ttk.Label(progress_frame, text="●", font=("Arial", 20), foreground="blue")
        self.progress_indicator.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Esperando para iniciar análisis...")
        self.status_label.grid(row=1, column=1, sticky=tk.W)
        
        self.current_file_label = ttk.Label(progress_frame, text="Archivo actual: --")
        self.current_file_label.grid(row=1, column=1)
        
        self.time_label = ttk.Label(progress_frame, text="Tiempo total: --")
        self.time_label.grid(row=1, column=1, sticky=tk.E)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=15)
        
        self.analyze_btn = ttk.Button(button_frame, text="🔍 INICIAR ANÁLISIS", 
                                     command=self.start_analysis)
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_all_btn = ttk.Button(button_frame, text="📂 ABRIR TODOS LOS DETECTADOS", 
                                      command=self.open_all_detected, state='disabled')
        self.open_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ DETENER ANÁLISIS", 
                                  command=self.stop_analysis, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(button_frame, text="🗑️ LIMPIAR TODO", 
                                   command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT)
        
        # NOTEBOOK CON PESTAÑAS
        results_notebook = ttk.Notebook(main_frame)
        results_notebook.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Pestaña de metadatos de referencia
        self.reference_frame = ttk.Frame(results_notebook, padding="10")
        results_notebook.add(self.reference_frame, text="📋 Metadatos de Referencia")
        
        # Pestaña de archivos detectados
        self.results_frame = ttk.Frame(results_notebook, padding="10")
        results_notebook.add(self.results_frame, text="📊 Archivos Detectados")
        
        # NUEVA PESTAÑA: Buscador de texto en PDFs
        self.search_frame = ttk.Frame(results_notebook, padding="10")
        results_notebook.add(self.search_frame, text="🔍 Buscador de Texto")
        
        main_frame.rowconfigure(5, weight=1)
        
        self.setup_reference_frame()
        self.setup_results_frame()
        self.setup_search_frame()
    
    def setup_search_frame(self):
        """Configura la pestaña de búsqueda de texto"""
        self.pdf_search_tab = PDFSearchTab(self.search_frame)
    
    def setup_reference_frame(self):
        self.reference_text = tk.Text(self.reference_frame, height=20, wrap=tk.WORD, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(self.reference_frame, orient=tk.VERTICAL, command=self.reference_text.yview)
        self.reference_text.configure(yscrollcommand=scrollbar.set)
        
        self.reference_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.reference_frame.columnconfigure(0, weight=1)
        self.reference_frame.rowconfigure(0, weight=1)
    
    def setup_results_frame(self):
        results_controls = ttk.Frame(self.results_frame)
        results_controls.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(results_controls, text="Archivos con metadatos similares:").pack(side=tk.LEFT)
        
        self.open_selected_btn = ttk.Button(results_controls, text="📖 Abrir Seleccionado", 
                                          command=self.open_selected_file, state='disabled')
        self.open_selected_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        files_frame = ttk.Frame(self.results_frame)
        files_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        columns = ('similitud', 'nombre', 'coincidencias', 'creador', 'productor', 'fecha_creacion', 'cache', 'ruta')
        self.results_tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=12)
        
        self.results_tree.heading('similitud', text='Nivel')
        self.results_tree.heading('nombre', text='Nombre Archivo')
        self.results_tree.heading('coincidencias', text='Coincidencias')
        self.results_tree.heading('creador', text='Creator')
        self.results_tree.heading('productor', text='Producer')
        self.results_tree.heading('fecha_creacion', text='Create Date')
        self.results_tree.heading('cache', text='Cache')
        self.results_tree.heading('ruta', text='Ruta')
        
        self.results_tree.column('similitud', width=80)
        self.results_tree.column('nombre', width=200)
        self.results_tree.column('coincidencias', width=100)
        self.results_tree.column('creador', width=150)
        self.results_tree.column('productor', width=150)
        self.results_tree.column('fecha_creacion', width=150)
        self.results_tree.column('cache', width=60)
        self.results_tree.column('ruta', width=300)
        
        tree_scroll_y = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(files_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        details_frame = ttk.LabelFrame(self.results_frame, text="🔍 Detalles Completos del Archivo Seleccionado", padding="10")
        details_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.details_text = tk.Text(details_frame, height=10, wrap=tk.WORD, font=("Consolas", 8))
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(1, weight=1)
        
        self.results_tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def update_progress(self, current, total, current_file):
        """Actualiza la barra de progreso y la información actual"""
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress['value'] = progress_percent
            
            # Actualizar etiquetas en el hilo principal
            self.root.after(0, lambda: self.status_label.config(text=f"Procesando: {current}/{total} archivos"))
            self.root.after(0, lambda: self.current_file_label.config(text=f"Archivo: {current_file}"))
    
    def play_completion_sound(self):
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except Exception as e:
            print(f"No se pudo reproducir sonido: {e}")
    
    def animate_progress(self):
        if not self.is_analyzing:
            self.progress_indicator.config(text="●", foreground="blue")
            return
        
        current_text = self.progress_indicator.cget("text")
        if current_text == "●":
            self.progress_indicator.config(text="◐", foreground="green")
        elif current_text == "◐":
            self.progress_indicator.config(text="◑", foreground="orange")
        elif current_text == "◑":
            self.progress_indicator.config(text="◒", foreground="red")
        else:
            self.progress_indicator.config(text="●", foreground="blue")
        
        self.root.after(300, self.animate_progress)
    
    def update_time_display(self, start_time, processed=0, total=0):
        if not self.is_analyzing:
            return
        
        elapsed = time.time() - start_time
        
        if processed > 0 and total > 0:
            if processed < 10:
                time_per_file = elapsed / processed if processed > 0 else 0
                estimated_total = time_per_file * total
                self.total_estimated_time = estimated_total
            else:
                progress_ratio = processed / total
                if progress_ratio > 0:
                    estimated_total = elapsed / progress_ratio
                    self.total_estimated_time = estimated_total
            
            if self.total_estimated_time:
                remaining = max(0, self.total_estimated_time - elapsed)
                elapsed_str = self.format_time(elapsed)
                remaining_str = self.format_time(remaining)
                total_estimated_str = self.format_time(self.total_estimated_time)
                
                self.time_label.config(text=f"Transcurrido: {elapsed_str} | Estimado: {total_estimated_str} | Restante: {remaining_str}")
            else:
                elapsed_str = self.format_time(elapsed)
                self.time_label.config(text=f"Transcurrido: {elapsed_str} | Calculando estimación...")
        else:
            elapsed_str = self.format_time(elapsed)
            self.time_label.config(text=f"Transcurrido: {elapsed_str}")
        
        self.root.after(1000, self.update_time_display, start_time, processed, total)
    
    def format_time(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def select_reference(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar PDF de referencia",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.analyzer.reference_file = file_path
            self.reference_entry.delete(0, tk.END)
            self.reference_entry.insert(0, file_path)
            self.open_reference_btn.config(state='normal')
            self.analyze_reference_metadata()
    
    def open_reference_file(self):
        if self.analyzer.reference_file:
            self.open_pdf_file(self.analyzer.reference_file)
    
    def select_search_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta para buscar duplicados")
        if folder:
            self.analyzer.search_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def analyze_reference_metadata(self):
        if not self.analyzer.reference_file:
            return
        
        success, metadata = self.analyzer.get_pdf_metadata(Path(self.analyzer.reference_file))
        
        if success:
            self.reference_metadata = metadata
            self.display_reference_metadata(metadata)
        else:
            messagebox.showerror("Error", f"No se pudieron leer los metadatos: {metadata}")
    
    def display_reference_metadata(self, metadata):
        self.reference_text.delete(1.0, tk.END)
        
        include_hash = self.include_hash_var.get()
        
        # Determinar nivel mínimo basado en la selección
        if self.similarity_var.get() == "baja":
            min_matches = 1
            nivel_text = "BAJA (1+ coincidencia)"
        elif self.similarity_var.get() == "media":
            min_matches = 2  
            nivel_text = "MEDIA (Create Date + otro campo)"
        else:
            min_matches = 3
            nivel_text = "ALTA (3+ coincidencias)"
        
        info_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                   METADATOS DE REFERENCIA                    ║
╚══════════════════════════════════════════════════════════════╝

📄 ARCHIVO:
   • Nombre: {metadata['nombre']}
   • Ruta: {metadata['ruta']}
   • Tamaño: {self.format_file_size(metadata['tamaño'])}
   • Modificado: {metadata['modificado'].strftime('%Y-%m-%d %H:%M:%S')}
   • Páginas: {metadata['paginas']}

🎯 METADATOS PRINCIPALES PARA BÚSQUEDA:

   • Creator: {metadata['creador']}
   • Producer: {metadata['productor']}
   • Create Date: {metadata['fecha_creacion']}
   • Hash SHA256: {metadata['hash_sha256'][:32]}...{' (INCLUIDO)' if include_hash else ' (NO incluido)'}

📊 CONFIGURACIÓN ACTUAL:
   • Incluir Hash: {'SÍ' if include_hash else 'NO'}
   • Caché: AUTOMÁTICO (siempre activo)
   • Nivel: {nivel_text}

🔍 METADATOS ADICIONALES:
   • Title: {metadata['titulo']}
   • Subject: {metadata['asunto']}
   • Keywords: {metadata['palabras_clave']}
   • Modify Date: {metadata['fecha_modificacion']}
"""
        self.reference_text.insert(1.0, info_text)
    
    def format_file_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
    
    def start_analysis(self):
        if not self.analyzer.reference_file:
            messagebox.showerror("Error", "Por favor selecciona un PDF de referencia")
            return
        
        if not self.analyzer.search_folder:
            messagebox.showerror("Error", "Por favor selecciona una carpeta para buscar")
            return
        
        if not self.reference_metadata:
            messagebox.showerror("Error", "No se pudieron leer los metadatos del archivo de referencia")
            return
        
        self.clear_results()
        
        self.is_analyzing = True
        self.analysis_start_time = time.time()
        self.total_estimated_time = None
        
        self.analyze_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.open_all_btn.config(state='disabled')
        self.progress['value'] = 0
        
        self.animate_progress()
        self.update_time_display(self.analysis_start_time)
        
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
    
    def stop_analysis(self):
        self.is_analyzing = False
        self.status_label.config(text="Análisis detenido por el usuario")
    
    def clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.details_text.delete(1.0, tk.END)
        self.open_selected_btn.config(state='disabled')
        self.open_all_btn.config(state='disabled')
        self.detected_files = []
    
    def run_analysis(self):
        try:
            include_hash = self.include_hash_var.get()
            
            # Determinar nivel mínimo basado en la selección
            if self.similarity_var.get() == "baja":
                min_matches = 1
            elif self.similarity_var.get() == "media":
                min_matches = 2
            else:  # alta
                min_matches = 3
            
            self.status_label.config(text="Iniciando análisis con caché automático...")
            
            similar_files, cache_used = self.analyzer.find_similar_by_metadata(
                self.reference_metadata, 
                self.analyzer.search_folder, 
                include_hash, 
                min_matches,
                progress_callback=self.update_progress
            )
            
            self.detected_files = similar_files
            self.display_results(similar_files, cache_used)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error durante el análisis: {str(e)}")
        finally:
            self.analysis_finished()
    
    def analysis_finished(self):
        self.is_analyzing = False
        self.analyze_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress['value'] = 100
        self.current_file_label.config(text="Completado")
        
        elapsed = time.time() - self.analysis_start_time
        elapsed_str = self.format_time(elapsed)
        
        self.status_label.config(text=f"Análisis completado en {elapsed_str}")
        self.time_label.config(text=f"Tiempo total: {elapsed_str}")
        
        self.play_completion_sound()
    
    def display_results(self, similar_files, cache_used):
        for file_info in similar_files:
            metadata = file_info['metadata']
            
            tags = ()
            if file_info['similarity_level'] == 'ALTA':
                tags = ('high',)
            elif file_info['similarity_level'] == 'MEDIA':
                tags = ('medium',)
            else:
                tags = ('low',)
            
            cache_indicator = "✓" if file_info.get('from_cache', False) else "✗"
            
            self.results_tree.insert('', 'end', values=(
                file_info['similarity_level'],
                metadata['nombre'],
                f"{file_info['matches']}/{file_info['total_possible']}",
                self.truncate_text(metadata['creador'], 25),
                self.truncate_text(metadata['productor'], 25),
                metadata['fecha_creacion'],
                cache_indicator,
                metadata['ruta']
            ), tags=tags)
        
        self.results_tree.tag_configure('high', background='#e8f5e8')
        self.results_tree.tag_configure('medium', background='#fff9e6')
        self.results_tree.tag_configure('low', background='#ffe6e6')
        
        total_matches = len(similar_files)
        cache_status = " (con caché)" if cache_used else " (sin caché - escaneo completo)"
        self.status_label.config(text=f"Análisis completado: {total_matches} archivos detectados{cache_status}")
        
        if total_matches > 0:
            self.open_all_btn.config(state='normal')
    
    def truncate_text(self, text, max_length):
        if not text or text == 'No disponible':
            return "N/D"
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def on_tree_select(self, event):
        selection = self.results_tree.selection()
        if selection:
            self.open_selected_btn.config(state='normal')
            item = selection[0]
            values = self.results_tree.item(item, 'values')
            self.show_file_details(values[7])
        else:
            self.open_selected_btn.config(state='disabled')
    
    def show_file_details(self, file_path):
        success, metadata = self.analyzer.get_pdf_metadata(Path(file_path))
        
        if success:
            match_info = next((f for f in self.detected_files if f['metadata']['ruta'] == file_path), None)
            
            cache_status = "SÍ" if match_info and match_info.get('from_cache') else "NO"
            
            details_text = f"""
📄 ARCHIVO SELECCIONADO:
   • Nombre: {metadata['nombre']}
   • Ruta: {metadata['ruta']}
   • Tamaño: {self.format_file_size(metadata['tamaño'])}
   • Modificado: {metadata['modificado'].strftime('%Y-%m-%d %H:%M:%S')}
   • Páginas: {metadata['paginas']}
   • Desde caché: {cache_status}

🎯 COINCIDENCIAS CON REFERENCIA:
   • Nivel: {match_info['similarity_level'] if match_info else 'N/A'}
   • Coincidencias: {match_info['matches'] if match_info else 'N/A'}/{match_info['total_possible'] if match_info else 'N/A'}
   • Detalles: {', '.join(match_info['match_details']) if match_info else 'N/A'}

📋 METADATOS PRINCIPALES:
   • Creator: {metadata['creador']}
   • Producer: {metadata['productor']}
   • Create Date: {metadata['fecha_creacion']}

🔍 METADATOS ADICIONALES:
   • Title: {metadata['titulo']}
   • Subject: {metadata['asunto']}
   • Keywords: {metadata['palabras_clave']}
   • Modify Date: {metadata['fecha_modificacion']}
   • Hash SHA256: {metadata['hash_sha256']}
"""
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, details_text)
    
    def open_selected_file(self):
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            values = self.results_tree.item(item, 'values')
            file_path = values[7]
            self.open_pdf_file(file_path)
    
    def open_all_detected(self):
        if not self.detected_files:
            return
        
        if self.analyzer.reference_file:
            self.open_pdf_file(self.analyzer.reference_file)
        
        for file_info in self.detected_files:
            self.open_pdf_file(file_info['metadata']['ruta'])
    
    def open_pdf_file(self, file_path):
        try:
            os.startfile(file_path)
        except:
            try:
                webbrowser.open(file_path)
            except:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {file_path}")
    
    def clear_all(self):
        self.analyzer.reference_file = None
        self.analyzer.search_folder = None
        self.reference_metadata = None
        self.detected_files = []
        
        self.reference_entry.delete(0, tk.END)
        self.folder_entry.delete(0, tk.END)
        self.reference_text.delete(1.0, tk.END)
        self.clear_results()
        
        self.open_reference_btn.config(state='disabled')
        self.status_label.config(text="Esperando para iniciar...")
        self.current_file_label.config(text="Archivo actual: --")
        self.time_label.config(text="Tiempo total: --")
        self.progress['value'] = 0

if __name__ == "__main__":
    try:
        import fitz
    except ImportError:
        print("❌ Error: Se requiere PyMuPDF. Instala con: pip install PyMuPDF")
        exit(1)
    
    root = tk.Tk()
    app = MetadataAnalyzerGUI(root)
    root.mainloop()