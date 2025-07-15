"""
File operations tools for Columbia Lake Partners agents
"""

import os
import pandas as pd
import openpyxl
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import setup_logging

class FileProcessor:
    """Handles file operations for agents"""
    
    def __init__(self):
        self.logger = setup_logging("file_processor")
        self.supported_formats = ['.xlsx', '.xls', '.csv', '.json']
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file format is supported"""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.supported_formats
    
    def read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file and return DataFrame"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Basic data cleaning
            df = df.dropna(how='all')  # Remove empty rows
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # Remove unnamed columns
            
            self.logger.info(f"Successfully read Excel file: {file_path} ({len(df)} rows)")
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading Excel file {file_path}: {str(e)}")
            return None
    
    def read_csv_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read CSV file and return DataFrame"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    self.logger.info(f"Successfully read CSV file: {file_path} ({len(df)} rows)")
                    return df
                except UnicodeDecodeError:
                    continue
            
            self.logger.error(f"Could not read CSV file with any encoding: {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading CSV file {file_path}: {str(e)}")
            return None
    
    def read_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read JSON file and return dictionary"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"Successfully read JSON file: {file_path}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error reading JSON file {file_path}: {str(e)}")
            return None
    
    def write_excel_file(self, df: pd.DataFrame, file_path: str) -> bool:
        """Write DataFrame to Excel file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to Excel
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            self.logger.info(f"Successfully wrote Excel file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing Excel file {file_path}: {str(e)}")
            return False
    
    def write_csv_file(self, df: pd.DataFrame, file_path: str) -> bool:
        """Write DataFrame to CSV file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to CSV
            df.to_csv(file_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Successfully wrote CSV file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing CSV file {file_path}: {str(e)}")
            return False
    
    def write_json_file(self, data: Dict[str, Any], file_path: str) -> bool:
        """Write dictionary to JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Successfully wrote JSON file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing JSON file {file_path}: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return {'exists': False}
            
            stat = os.stat(file_path)
            
            return {
                'exists': True,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'extension': os.path.splitext(file_path)[1].lower(),
                'is_supported': self.is_supported_file(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def validate_excel_structure(self, df: pd.DataFrame, required_columns: List[str]) -> Dict[str, Any]:
        """Validate Excel file structure"""
        try:
            validation_result = {
                'is_valid': True,
                'missing_columns': [],
                'extra_columns': [],
                'row_count': len(df),
                'column_count': len(df.columns),
                'warnings': []
            }
            
            # Check for required columns
            df_columns = [col.lower().strip() for col in df.columns]
            required_columns_lower = [col.lower().strip() for col in required_columns]
            
            for req_col in required_columns_lower:
                if req_col not in df_columns:
                    validation_result['missing_columns'].append(req_col)
                    validation_result['is_valid'] = False
            
            # Check for extra columns
            for col in df_columns:
                if col not in required_columns_lower:
                    validation_result['extra_columns'].append(col)
            
            # Check for empty data
            if len(df) == 0:
                validation_result['warnings'].append("File contains no data rows")
            
            # Check for missing data in required columns
            for col in df.columns:
                if col.lower().strip() in required_columns_lower:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        validation_result['warnings'].append(f"Column '{col}' has {null_count} missing values")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating Excel structure: {str(e)}")
            return {'is_valid': False, 'error': str(e)}
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame by removing empty rows and columns"""
        try:
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # Remove completely empty columns
            df = df.dropna(axis=1, how='all')
            
            # Remove unnamed columns
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            # Strip whitespace from string columns
            string_columns = df.select_dtypes(include=['object']).columns
            df[string_columns] = df[string_columns].apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            # Replace empty strings with NaN
            df = df.replace('', pd.NA)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error cleaning DataFrame: {str(e)}")
            return df
    
    def backup_file(self, file_path: str) -> str:
        """Create backup of file"""
        try:
            if not os.path.exists(file_path):
                return ""
            
            # Generate backup filename
            base_name, ext = os.path.splitext(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{base_name}_backup_{timestamp}{ext}"
            
            # Copy file
            import shutil
            shutil.copy2(file_path, backup_path)
            
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup for {file_path}: {str(e)}")
            return ""
    
    def list_files_in_directory(self, directory_path: str, 
                               extensions: Optional[List[str]] = None) -> List[str]:
        """List files in directory with optional extension filter"""
        try:
            if not os.path.exists(directory_path):
                self.logger.error(f"Directory not found: {directory_path}")
                return []
            
            files = []
            for file_name in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file_name)
                
                if os.path.isfile(file_path):
                    if extensions is None:
                        files.append(file_path)
                    else:
                        _, ext = os.path.splitext(file_name)
                        if ext.lower() in extensions:
                            files.append(file_path)
            
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Error listing files in {directory_path}: {str(e)}")
            return []