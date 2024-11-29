import os
import sys
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, scrolledtext
import PyPDF2
import winreg
from groq import Groq

class PDFToMarkdownConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF a Markdown Converter")
        self.root.geometry("600x500")
        
        # Configuración de logging
        logging.basicConfig(filename='pdf_converter.log', level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Variable para almacenar la ruta del PDF
        self.pdf_path = None
        
        # Título
        self.title_label = tk.Label(root, text="Convertidor PDF a Markdown", font=("Arial", 16))
        self.title_label.pack(pady=20)
        
        # Botón de selección de PDF
        self.select_pdf_btn = tk.Button(root, text="Seleccionar PDF", command=self.select_pdf)
        self.select_pdf_btn.pack(pady=10)
        
        # Log de eventos
        self.log_text = scrolledtext.ScrolledText(root, height=10, width=60)
        self.log_text.pack(pady=10)
    
    def log_message(self, message, level='info'):
        """Registrar mensajes en el widget de log y en el archivo"""
        timestamp = f"{message}\n"
        self.log_text.insert(tk.END, timestamp)
        self.log_text.see(tk.END)
        
        # Logging al archivo
        if level == 'info':
            logging.info(message)
        elif level == 'error':
            logging.error(message)
    
    def select_pdf(self):
        """Abrir diálogo para seleccionar PDF"""
        try:
            self.pdf_path = filedialog.askopenfilename(
                title="Selecciona un archivo PDF",
                filetypes=[("Archivos PDF", "*.pdf")]
            )
            if self.pdf_path:
                self.log_message(f"Archivo seleccionado: {self.pdf_path}")
                self.ask_conversion_type()
        except Exception as e:
            self.log_message(f"Error al seleccionar PDF: {e}", 'error')
            messagebox.showerror("Error", f"No se pudo seleccionar el PDF:\n{e}")
    
    def ask_conversion_type(self):
        """Preguntar al usuario el tipo de conversión"""
        conversion_type = messagebox.askyesno(
            "Tipo de Conversión", 
            "¿Deseas generar un Markdown con mejora de IA?"
        )
        
        if conversion_type:
            self.convert_with_ai()
        else:
            self.convert_standard_markdown()
    
    def get_groq_api_key(self):
        """Obtener o solicitar la API key de Groq"""
        try:
            # Intentar obtener la API key del registro de Windows
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                r"SOFTWARE\PDFMarkdownConverter", 
                0, 
                winreg.KEY_READ
            )
            api_key, _ = winreg.QueryValueEx(key, "GroqAPIKey")
            winreg.CloseKey(key)
            return api_key
        except FileNotFoundError:
            # Si no existe, solicitar al usuario
            api_key = simpledialog.askstring(
                "API Key", 
                "Introduce tu API Key de Groq:", 
                show='*'
            )
            
            if api_key:
                # Guardar en el registro de Windows
                try:
                    key = winreg.CreateKey(
                        winreg.HKEY_CURRENT_USER, 
                        r"SOFTWARE\PDFMarkdownConverter"
                    )
                    winreg.SetValueEx(key, "GroqAPIKey", 0, winreg.REG_SZ, api_key)
                    winreg.CloseKey(key)
                except Exception as e:
                    self.log_message(f"Error guardando API Key: {e}", 'error')
            
            return api_key
    
    def convert_standard_markdown(self):
        """Convertir PDF a Markdown estándar"""
        try:
            # Abrir el PDF
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extraer texto de todas las páginas
                full_text = []
                for page in pdf_reader.pages:
                    full_text.append(page.extract_text())
                
                # Nombre del archivo de salida
                base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
                
                # Diálogo para guardar archivo
                md_path = filedialog.asksaveasfilename(
                    defaultextension=".md",
                    filetypes=[("Markdown files", "*.md")],
                    initialfile=f"{base_name}_convertido.md"
                )
                
                if md_path:
                    # Escribir texto en Markdown
                    with open(md_path, 'w', encoding='utf-8') as md_file:
                        md_file.write(f"# {base_name}\n\n")
                        for i, page_text in enumerate(full_text, 1):
                            md_file.write(f"## Página {i}\n\n")
                            md_file.write(page_text + "\n\n")
                    
                    # Registrar y mostrar mensaje de éxito
                    success_msg = f"El archivo Markdown ha sido guardado como: {md_path}"
                    self.log_message(success_msg)
                    messagebox.showinfo("Conversión Exitosa", success_msg)
                else:
                    self.log_message("Guardado de archivo cancelado por el usuario")
        
        except Exception as e:
            error_msg = f"No se pudo convertir el PDF: {e}"
            self.log_message(error_msg, 'error')
            messagebox.showerror("Error", error_msg)
    
    def convert_with_ai(self):
        """Convertir PDF a Markdown mejorado con IA"""
        # Obtener API Key
        api_key = self.get_groq_api_key()
        
        if not api_key:
            messagebox.showwarning("API Key", "No se proporcionó una API Key. Cancelando conversión.")
            return
        
        try:
            # Convertir PDF a texto plano primero
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                full_text = "\n".join([page.extract_text() for page in pdf_reader.pages])
            
            # Inicializar cliente Groq
            client = Groq(api_key=api_key)
            
            # Prompt para mejorar el documento
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente experto en transformar documentos técnicos en contenido claro y pedagógico."
                    },
                    {
                        "role": "user",
                        "content": f"Transforma el siguiente texto en un documento Markdown estructurado, claro y pedagógico. Organiza la información, crea secciones, añade títulos descriptivos y mejora la legibilidad:\n\n{full_text}"
                    }
                ],
                model="llama-3.2-90b-vision-preview"
            )
            
            # Obtener texto mejorado
            improved_text = chat_completion.choices[0].message.content
            
            # Nombre del archivo de salida
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            
            # Diálogo para guardar archivo
            md_path = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md")],
                initialfile=f"{base_name}_mejorado.md"
            )
            
            if md_path:
                # Escribir texto mejorado
                with open(md_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(improved_text)
                
                # Registrar y mostrar mensaje de éxito
                success_msg = f"El archivo Markdown mejorado ha sido guardado como: {md_path}"
                self.log_message(success_msg)
                messagebox.showinfo("Conversión con IA Exitosa", success_msg)
            else:
                self.log_message("Guardado de archivo cancelado por el usuario")
        
        except Exception as e:
            error_msg = f"No se pudo convertir el PDF con IA: {e}"
            self.log_message(error_msg, 'error')
            messagebox.showerror("Error", error_msg)

def main():
    root = tk.Tk()
    app = PDFToMarkdownConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
