# pdf_metadata_analyzer_enhanced.py
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

class PDFMetadataAnalyzer:
    def __init__(self):
        self.reference_file = None
        self.search_folder = None
    
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
                    'paginas': len(doc)
                }
                
                return True, full_metadata
                
        except Exception as e:
            return False, f"Error al leer metadatos: {str(e)}"
    
    def format_pdf_date(self, pdf_date_string):
        """Convierte el formato de fecha PDF a formato legible"""
        if pdf_date_string == 'No disponible' or not pdf_date_string:
            return 'No disponible'
        
        try:
            # El formato típico es: D:YYYYMMDDHHMMSS...
            if pdf_date_string.startswith('D:'):
                date_str = pdf_date_string[2:]  # Remover 'D:'
                
                # Extraer componentes básicos
                year = int(date_str[0:4]) if len(date_str) >= 4 else 2024
                month = int(date_str[4:6]) if len(date_str) >= 6 else 1
                day = int(date_str[6:8]) if len(date_str) >= 8 else 1
                hour = int(date_str[8:10]) if len(date_str) >= 10 else 0
                minute = int(date_str[10:12]) if len(date_str) >= 12 else 0
                second = int(date_str[12:14]) if len(date_str) >= 14 else 0
                
                # Crear objeto datetime
                pdf_date = datetime(year, month, day, hour, minute, second)
                
                # Formatear a string legible
                return pdf_date.strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            print(f"Error formateando fecha PDF: {pdf_date_string}, Error: {e}")
        
        # Si falla el parsing, retornar el string original
        return pdf_date_string
    
    def normalize_metadata_value(self, value):
        """Normaliza valores de metadatos para comparación"""
        if value == 'No disponible' or not value:
            return None
        return str(value).strip().lower()
    
    def find_similar_by_metadata(self, reference_metadata, search_folder, include_hash=False, min_matches=2):
        """Busca PDFs con metadatos similares"""
        similar_files = []
        
        # Normalizar metadatos de referencia
        ref_creator = self.normalize_metadata_value(reference_metadata.get('creador'))
        ref_producer = self.normalize_metadata_value(reference_metadata.get('productor'))
        ref_creation_date = self.normalize_metadata_value(reference_metadata.get('fecha_creacion'))
        ref_hash = reference_metadata.get('hash_sha256') if include_hash else None
        
        # Buscar todos los PDFs
        pdf_files = list(Path(search_folder).rglob("*.pdf"))
        
        for pdf_file in pdf_files:
            if pdf_file == Path(self.reference_file):
                continue
                
            success, metadata = self.get_pdf_metadata(pdf_file)
            if not success:
                continue
            
            # Normalizar metadatos del archivo actual
            comp_creator = self.normalize_metadata_value(metadata.get('creador'))
            comp_producer = self.normalize_metadata_value(metadata.get('productor'))
            comp_creation_date = self.normalize_metadata_value(metadata.get('fecha_creacion'))
            comp_hash = metadata.get('hash_sha256') if include_hash else None
            
            # Calcular coincidencias
            matches = 0
            total_possible = 3 + (1 if include_hash else 0)  # 3 metadatos + hash (opcional)
            match_details = []
            
            # Comparar Creator
            if ref_creator and comp_creator and ref_creator == comp_creator:
                matches += 1
                match_details.append("✓ Creator")
            else:
                match_details.append("✗ Creator")
            
            # Comparar Producer
            if ref_producer and comp_producer and ref_producer == comp_producer:
                matches += 1
                match_details.append("✓ Producer")
            else:
                match_details.append("✗ Producer")
            
            # Comparar Create Date
            if ref_creation_date and comp_creation_date and ref_creation_date == comp_creation_date:
                matches += 1
                match_details.append("✓ Create Date")
            else:
                match_details.append("✗ Create Date")
            
            # Comparar Hash (si está habilitado)
            if include_hash:
                if ref_hash and comp_hash and ref_hash == comp_hash:
                    matches += 1
                    match_details.append("✓ Hash SHA256")
                else:
                    match_details.append("✗ Hash SHA256")
            
            # Solo considerar archivos con el mínimo de coincidencias requerido
            if matches >= min_matches:
                similarity_level = "ALTA" if matches >= total_possible - 1 else "MEDIA"
                
                similar_files.append({
                    'metadata': metadata,
                    'matches': matches,
                    'total_possible': total_possible,
                    'similarity_level': similarity_level,
                    'match_details': match_details,
                    'ruta_completa': str(pdf_file)
                })
        
        # Ordenar por número de coincidencias (descendente)
        similar_files.sort(key=lambda x: x['matches'], reverse=True)
        return similar_files

class MetadataAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Metadatos - Mejorado")
        self.root.geometry("1400x1000")
        
        self.analyzer = PDFMetadataAnalyzer()
        self.reference_metadata = None
        self.detected_files = []  # Para almacenar archivos detectados
        self.analysis_start_time = None
        self.is_analyzing = False
        
        self.setup_ui()
    
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, 
                               text="Analizador de Metadatos de PDFs - By José Valenzuela", 
                               font=("Arial", 14, "bold"),
                               justify=tk.CENTER)
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Panel de selección
        selection_frame = ttk.LabelFrame(main_frame, text="Selección de Archivos", padding="10")
        selection_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        selection_frame.columnconfigure(1, weight=1)
        
        # PDF de referencia
        ttk.Label(selection_frame, text="PDF de referencia:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reference_entry = ttk.Entry(selection_frame)
        self.reference_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(selection_frame, text="📄 Seleccionar PDF", command=self.select_reference).grid(row=0, column=2, pady=5)
        
        # Carpeta de búsqueda
        ttk.Label(selection_frame, text="Carpeta de búsqueda:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.folder_entry = ttk.Entry(selection_frame)
        self.folder_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(selection_frame, text="📁 Seleccionar Carpeta", command=self.select_search_folder).grid(row=1, column=2, pady=5)
        
        # Panel de configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración de Búsqueda", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Configuración en dos columnas
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)
        
        # Columna izquierda - Opciones de búsqueda
        left_config = ttk.Frame(config_frame)
        left_config.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        self.include_hash_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left_config, text="Incluir Hash SHA256 en la comparación", 
                       variable=self.include_hash_var).pack(anchor=tk.W, pady=2)
        
        ttk.Label(left_config, text="Nivel mínimo de coincidencias:").pack(anchor=tk.W, pady=(10, 5))
        
        self.similarity_var = tk.StringVar(value="media")
        similarity_frame = ttk.Frame(left_config)
        similarity_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(similarity_frame, text="Alta (3+ coincidencias)", 
                       variable=self.similarity_var, value="alta").pack(side=tk.LEFT)
        ttk.Radiobutton(similarity_frame, text="Media (2+ coincidencias)", 
                       variable=self.similarity_var, value="media").pack(side=tk.LEFT, padx=(20, 0))
        
        # Columna derecha - Información
        right_config = ttk.Frame(config_frame)
        right_config.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        info_text = (
            "💡 INFORMACIÓN:\n"
            "• Creator: Programa que creó el PDF\n"
            "• Producer: Programa que produjo el PDF\n"
            "• Create Date: Fecha de creación\n"
            "• Hash SHA256: Identificador único del archivo\n\n"
            "🎯 RECOMENDACIÓN:\n"
            "• Usar 'Media' para máxima detección\n"
            "• 'Alta' para menos falsos positivos\n"
            "• Hash solo para archivos idénticos"
        )
        ttk.Label(right_config, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Panel de progreso y tiempo
        progress_frame = ttk.LabelFrame(main_frame, text="Progreso del Análisis", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        progress_frame.columnconfigure(1, weight=1)
        
        # Indicador de progreso animado
        self.progress_indicator = ttk.Label(progress_frame, text="●", font=("Arial", 20), foreground="blue")
        self.progress_indicator.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        
        # Barra de progreso
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Información de tiempo y estado
        self.status_label = ttk.Label(progress_frame, text="Esperando para iniciar análisis...")
        self.status_label.grid(row=1, column=1, sticky=tk.W)
        
        self.time_label = ttk.Label(progress_frame, text="Tiempo estimado: --")
        self.time_label.grid(row=1, column=1, sticky=tk.E)
        
        # Botones de control
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
        
        # Panel de resultados
        results_notebook = ttk.Notebook(main_frame)
        results_notebook.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Pestaña de metadatos de referencia
        self.reference_frame = ttk.Frame(results_notebook, padding="10")
        results_notebook.add(self.reference_frame, text="📋 Metadatos de Referencia")
        
        # Pestaña de resultados
        self.results_frame = ttk.Frame(results_notebook, padding="10")
        results_notebook.add(self.results_frame, text="📊 Archivos Detectados")
        
        # Configurar expansión
        main_frame.rowconfigure(5, weight=1)
        
        # Inicializar frames
        self.setup_reference_frame()
        self.setup_results_frame()
    
    def setup_reference_frame(self):
        """Configura el frame de metadatos de referencia"""
        # Área de texto para mostrar metadatos
        self.reference_text = tk.Text(self.reference_frame, height=20, wrap=tk.WORD, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(self.reference_frame, orient=tk.VERTICAL, command=self.reference_text.yview)
        self.reference_text.configure(yscrollcommand=scrollbar.set)
        
        self.reference_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.reference_frame.columnconfigure(0, weight=1)
        self.reference_frame.rowconfigure(0, weight=1)
    
    def setup_results_frame(self):
        """Configura el frame de resultados"""
        # Frame para controles de resultados
        results_controls = ttk.Frame(self.results_frame)
        results_controls.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(results_controls, text="Archivos con metadatos similares:").pack(side=tk.LEFT)
        
        self.open_selected_btn = ttk.Button(results_controls, text="📖 Abrir Seleccionado", 
                                          command=self.open_selected_file, state='disabled')
        self.open_selected_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Lista de archivos detectados
        files_frame = ttk.Frame(self.results_frame)
        files_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Treeview para mostrar archivos
        columns = ('similitud', 'nombre', 'coincidencias', 'creador', 'productor', 'fecha_creacion', 'ruta')
        self.results_tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=12)
        
        # Configurar columnas
        self.results_tree.heading('similitud', text='Nivel')
        self.results_tree.heading('nombre', text='Nombre Archivo')
        self.results_tree.heading('coincidencias', text='Coincidencias')
        self.results_tree.heading('creador', text='Creator')
        self.results_tree.heading('productor', text='Producer')
        self.results_tree.heading('fecha_creacion', text='Create Date')
        self.results_tree.heading('ruta', text='Ruta')
        
        self.results_tree.column('similitud', width=80)
        self.results_tree.column('nombre', width=200)
        self.results_tree.column('coincidencias', width=100)
        self.results_tree.column('creador', width=150)
        self.results_tree.column('productor', width=150)
        self.results_tree.column('fecha_creacion', width=150)
        self.results_tree.column('ruta', width=350)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(files_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Grid
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # Frame para detalles
        details_frame = ttk.LabelFrame(self.results_frame, text="🔍 Detalles Completos del Archivo Seleccionado", padding="10")
        details_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.details_text = tk.Text(details_frame, height=10, wrap=tk.WORD, font=("Consolas", 8))
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        
        # Configurar expansión
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(1, weight=1)
        
        # Bind selección
        self.results_tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def animate_progress(self):
        """Animación del indicador de progreso"""
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
        
        # Programar siguiente animación
        self.root.after(300, self.animate_progress)
    
    def update_time_estimate(self, processed, total, start_time):
        """Actualiza la estimación de tiempo restante"""
        if not self.is_analyzing:
            return
        
        elapsed = time.time() - start_time
        if processed > 0:
            time_per_file = elapsed / processed
            remaining_files = total - processed
            estimated_remaining = time_per_file * remaining_files
            
            # Formatear tiempo
            elapsed_str = self.format_time(elapsed)
            remaining_str = self.format_time(estimated_remaining)
            
            self.time_label.config(text=f"Tiempo: {elapsed_str} / Estimado: {remaining_str}")
        
        # Programar próxima actualización
        self.root.after(1000, self.update_time_estimate, processed, total, start_time)
    
    def format_time(self, seconds):
        """Formatea segundos a string legible"""
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
            
            # Analizar metadatos del archivo de referencia
            self.analyze_reference_metadata()
    
    def select_search_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta para buscar duplicados")
        if folder:
            self.analyzer.search_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def analyze_reference_metadata(self):
        """Analiza y muestra los metadatos del archivo de referencia"""
        if not self.analyzer.reference_file:
            return
        
        success, metadata = self.analyzer.get_pdf_metadata(Path(self.analyzer.reference_file))
        
        if success:
            self.reference_metadata = metadata
            self.display_reference_metadata(metadata)
        else:
            messagebox.showerror("Error", f"No se pudieron leer los metadatos: {metadata}")
    
    def display_reference_metadata(self, metadata):
        """Muestra los metadatos en el área de texto"""
        self.reference_text.delete(1.0, tk.END)
        
        include_hash = self.include_hash_var.get()
        min_matches = 3 if self.similarity_var.get() == "alta" else 2
        
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
   • Mínimo coincidencias: {min_matches}
   • Nivel: {self.similarity_var.get().upper()}

🔍 METADATOS ADICIONALES:
   • Title: {metadata['titulo']}
   • Subject: {metadata['asunto']}
   • Keywords: {metadata['palabras_clave']}
   • Modify Date: {metadata['fecha_modificacion']}
"""
        self.reference_text.insert(1.0, info_text)
    
    def format_file_size(self, size_bytes):
        """Formatea el tamaño del archivo en unidades legibles"""
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
        
        # Limpiar resultados anteriores
        self.clear_results()
        
        # Configurar estado de análisis
        self.is_analyzing = True
        self.analysis_start_time = time.time()
        
        # Actualizar interfaz
        self.analyze_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.open_all_btn.config(state='disabled')
        self.progress['value'] = 0
        
        # Iniciar animación
        self.animate_progress()
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
    
    def stop_analysis(self):
        """Detiene el análisis en curso"""
        self.is_analyzing = False
        self.status_label.config(text="Análisis detenido por el usuario")
    
    def clear_results(self):
        """Limpia los resultados anteriores"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.details_text.delete(1.0, tk.END)
        self.open_selected_btn.config(state='disabled')
        self.open_all_btn.config(state='disabled')
        self.detected_files = []
    
    def run_analysis(self):
        try:
            # Obtener configuración
            include_hash = self.include_hash_var.get()
            min_matches = 3 if self.similarity_var.get() == "alta" else 2
            
            self.status_label.config(text="Buscando archivos PDF...")
            
            # Buscar archivos PDF
            pdf_files = list(Path(self.analyzer.search_folder).rglob("*.pdf"))
            total_files = len(pdf_files)
            
            if total_files == 0:
                self.status_label.config(text="No se encontraron archivos PDF")
                return
            
            # Iniciar actualización de tiempo
            self.update_time_estimate(0, total_files, self.analysis_start_time)
            
            # Buscar coincidencias por metadatos
            similar_files = []
            processed = 0
            
            for pdf_file in pdf_files:
                if not self.is_analyzing:
                    break
                    
                if pdf_file == Path(self.analyzer.reference_file):
                    processed += 1
                    continue
                
                success, metadata = self.analyzer.get_pdf_metadata(pdf_file)
                processed += 1
                
                # Actualizar progreso
                progress_percent = (processed / total_files) * 100
                self.progress['value'] = progress_percent
                self.status_label.config(text=f"Analizando {processed}/{total_files} archivos...")
                
                if not success:
                    continue
                
                # Comparar metadatos
                ref_creator = self.analyzer.normalize_metadata_value(self.reference_metadata.get('creador'))
                ref_producer = self.analyzer.normalize_metadata_value(self.reference_metadata.get('productor'))
                ref_creation_date = self.analyzer.normalize_metadata_value(self.reference_metadata.get('fecha_creacion'))
                ref_hash = self.reference_metadata.get('hash_sha256') if include_hash else None
                
                comp_creator = self.analyzer.normalize_metadata_value(metadata.get('creador'))
                comp_producer = self.analyzer.normalize_metadata_value(metadata.get('productor'))
                comp_creation_date = self.analyzer.normalize_metadata_value(metadata.get('fecha_creacion'))
                comp_hash = metadata.get('hash_sha256') if include_hash else None
                
                # Calcular coincidencias
                matches = 0
                total_possible = 3 + (1 if include_hash else 0)
                match_details = []
                
                if ref_creator and comp_creator and ref_creator == comp_creator:
                    matches += 1
                    match_details.append("✓ Creator")
                else:
                    match_details.append("✗ Creator")
                
                if ref_producer and comp_producer and ref_producer == comp_producer:
                    matches += 1
                    match_details.append("✓ Producer")
                else:
                    match_details.append("✗ Producer")
                
                if ref_creation_date and comp_creation_date and ref_creation_date == comp_creation_date:
                    matches += 1
                    match_details.append("✓ Create Date")
                else:
                    match_details.append("✗ Create Date")
                
                if include_hash:
                    if ref_hash and comp_hash and ref_hash == comp_hash:
                        matches += 1
                        match_details.append("✓ Hash SHA256")
                    else:
                        match_details.append("✗ Hash SHA256")
                
                if matches >= min_matches:
                    similarity_level = "ALTA" if matches >= total_possible - 1 else "MEDIA"
                    
                    similar_files.append({
                        'metadata': metadata,
                        'matches': matches,
                        'total_possible': total_possible,
                        'similarity_level': similarity_level,
                        'match_details': match_details,
                        'ruta_completa': str(pdf_file)
                    })
            
            # Guardar archivos detectados
            self.detected_files = similar_files
            
            # Mostrar resultados
            self.display_results(similar_files)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error durante el análisis: {str(e)}")
        finally:
            self.analysis_finished()
    
    def analysis_finished(self):
        """Finaliza el análisis y actualiza la interfaz"""
        self.is_analyzing = False
        self.analyze_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress['value'] = 100
        
        elapsed = time.time() - self.analysis_start_time
        elapsed_str = self.format_time(elapsed)
        
        self.status_label.config(text=f"Análisis completado en {elapsed_str}")
        self.time_label.config(text=f"Tiempo total: {elapsed_str}")
    
    def display_results(self, similar_files):
        """Muestra los resultados en el Treeview"""
        for file_info in similar_files:
            metadata = file_info['metadata']
            
            # Determinar color según nivel de similitud
            tags = ()
            if file_info['similarity_level'] == 'ALTA':
                tags = ('high',)
            else:
                tags = ('medium',)
            
            self.results_tree.insert('', 'end', values=(
                file_info['similarity_level'],
                metadata['nombre'],
                f"{file_info['matches']}/{file_info['total_possible']}",
                self.truncate_text(metadata['creador'], 25),
                self.truncate_text(metadata['productor'], 25),
                metadata['fecha_creacion'],
                metadata['ruta']
            ), tags=tags)
        
        # Configurar tags para colores
        self.results_tree.tag_configure('high', background='#e8f5e8')
        self.results_tree.tag_configure('medium', background='#fff9e6')
        
        # Actualizar estadísticas y habilitar botones
        total_matches = len(similar_files)
        self.status_label.config(text=f"Análisis completado: {total_matches} archivos detectados")
        
        if total_matches > 0:
            self.open_all_btn.config(state='normal')
    
    def truncate_text(self, text, max_length):
        """Trunca texto si es muy largo"""
        if not text or text == 'No disponible':
            return "N/D"
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def on_tree_select(self, event):
        """Maneja la selección de un archivo en el Treeview"""
        selection = self.results_tree.selection()
        if selection:
            self.open_selected_btn.config(state='normal')
            item = selection[0]
            values = self.results_tree.item(item, 'values')
            
            # Mostrar detalles completos
            self.show_file_details(values[6])
        else:
            self.open_selected_btn.config(state='disabled')
    
    def show_file_details(self, file_path):
        """Muestra los detalles completos del archivo seleccionado"""
        success, metadata = self.analyzer.get_pdf_metadata(Path(file_path))
        
        if success:
            # Encontrar información de coincidencias
            match_info = next((f for f in self.detected_files if f['metadata']['ruta'] == file_path), None)
            
            details_text = f"""
📄 ARCHIVO SELECCIONADO:
   • Nombre: {metadata['nombre']}
   • Ruta: {metadata['ruta']}
   • Tamaño: {self.format_file_size(metadata['tamaño'])}
   • Modificado: {metadata['modificado'].strftime('%Y-%m-%d %H:%M:%S')}
   • Páginas: {metadata['paginas']}

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
        """Abre el archivo PDF seleccionado"""
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            values = self.results_tree.item(item, 'values')
            file_path = values[6]
            
            self.open_pdf_file(file_path)
    
    def open_all_detected(self):
        """Abre todos los archivos detectados"""
        if not self.detected_files:
            return
        
        # Abrir archivo de referencia primero
        if self.analyzer.reference_file:
            self.open_pdf_file(self.analyzer.reference_file)
        
        # Abrir archivos detectados
        for file_info in self.detected_files:
            self.open_pdf_file(file_info['metadata']['ruta'])
    
    def open_pdf_file(self, file_path):
        """Abre un archivo PDF"""
        try:
            os.startfile(file_path)
        except:
            try:
                webbrowser.open(file_path)
            except:
                messagebox.showerror("Error", f"No se pudo abrir el archivo: {file_path}")
    
    def clear_all(self):
        """Limpia toda la selección y resultados"""
        self.analyzer.reference_file = None
        self.analyzer.search_folder = None
        self.reference_metadata = None
        self.detected_files = []
        
        self.reference_entry.delete(0, tk.END)
        self.folder_entry.delete(0, tk.END)
        self.reference_text.delete(1.0, tk.END)
        self.clear_results()
        
        self.status_label.config(text="Esperando para iniciar...")
        self.time_label.config(text="Tiempo estimado: --")
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