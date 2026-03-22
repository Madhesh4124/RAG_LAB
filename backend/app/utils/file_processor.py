import os
import io
import PyPDF2
from fastapi import UploadFile

class FileProcessor:
    @staticmethod
    async def process_upload(file: UploadFile) -> dict:
        filename = file.filename
        if not filename:
            raise ValueError("No filename provided")
            
        # Detect file type from extension
        ext = os.path.splitext(filename)[1].lower()
        file_type = ext.lstrip('.')
        
        # Read the file bytes
        content_bytes = await file.read()
        file_size = len(content_bytes)
        
        extracted_text = ""
        
        # Process based on file extension
        if file_type == 'txt':
            try:
                extracted_text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                extracted_text = content_bytes.decode('latin-1', errors='replace')
                
        elif file_type == 'pdf':
            pdf_file = io.BytesIO(content_bytes)
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                extracted_text = "\n".join(text_parts)
            except Exception as e:
                raise ValueError(f"Failed to read PDF file: {str(e)}")
                
        else:
            raise ValueError(f"Unsupported file type: {ext}. Only .txt and .pdf are supported.")
            
        return {
            "content": extracted_text,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size
        }
