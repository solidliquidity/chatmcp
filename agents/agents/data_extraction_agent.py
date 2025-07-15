"""
Data Extraction Agent for Columbia Lake Partners
Extracts relevant data from Excel sheets and populates the database using Google ADK
"""

import pandas as pd
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import asyncio

from ..shared.config import GOOGLE_ADK_CONFIG, DATABASE_CONFIG, AGENT_CONFIG
from ..shared.types import (
    CompanyData, ExcelProcessingResult, AgentResponse, 
    CompanyStatus, AlertSeverity
)
from ..shared.utils import (
    setup_logging, create_success_response, create_error_response,
    validate_company_data, parse_excel_data, calculate_company_health_score,
    get_current_timestamp
)
from ..tools.database import DatabaseManager
from ..tools.file_operations import FileProcessor

class DataExtractionAgent:
    """Agent for extracting data from Excel sheets and populating database"""
    
    def __init__(self):
        self.logger = setup_logging("data_extraction_agent")
        self.config = AGENT_CONFIG
        self.config.agent_name = "data_extraction_agent"
        
        # Initialize Google ADK
        genai.configure(api_key=GOOGLE_ADK_CONFIG.api_key)
        self.model = genai.GenerativeModel(self.config.model)
        
        # Initialize database and file processor
        self.db_manager = DatabaseManager(DATABASE_CONFIG)
        self.file_processor = FileProcessor()
        
        self.logger.info(f"Data Extraction Agent initialized with model: {self.config.model}")
    
    async def process_excel_file(self, file_path: str) -> ExcelProcessingResult:
        """Process an Excel file and extract company data"""
        try:
            self.logger.info(f"Processing Excel file: {file_path}")
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            processed_rows = 0
            errors = []
            warnings = []
            company_data_list = []
            
            for index, row in df.iterrows():
                try:
                    # Convert row to dictionary
                    row_dict = row.to_dict()
                    
                    # Parse and clean data
                    cleaned_data = parse_excel_data(row_dict)
                    
                    # Use Google ADK to extract and structure data
                    structured_data = await self._extract_structured_data(cleaned_data)
                    
                    if structured_data:
                        # Validate data
                        validation_errors = validate_company_data(structured_data)
                        if validation_errors:
                            errors.extend([f"Row {index + 1}: {error}" for error in validation_errors])
                            continue
                        
                        # Create CompanyData object
                        company_data = self._create_company_data(structured_data)
                        company_data_list.append(company_data)
                        
                        # Store in database
                        await self.db_manager.insert_company_data(company_data)
                        
                        processed_rows += 1
                        
                    else:
                        warnings.append(f"Row {index + 1}: Could not extract structured data")
                        
                except Exception as e:
                    error_msg = f"Row {index + 1}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            success = len(errors) == 0
            
            return ExcelProcessingResult(
                success=success,
                company_data=company_data_list[0] if company_data_list else None,
                errors=errors,
                warnings=warnings,
                processed_rows=processed_rows
            )
            
        except Exception as e:
            error_msg = f"Failed to process Excel file: {str(e)}"
            self.logger.error(error_msg)
            return ExcelProcessingResult(
                success=False,
                company_data=None,
                errors=[error_msg],
                warnings=[],
                processed_rows=0
            )
    
    async def _extract_structured_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use Google ADK to extract structured data from raw Excel data"""
        try:
            prompt = f"""
            Extract and structure the following company data from an Excel row.
            Return a JSON object with the following fields:
            - company_id: Generate a unique ID if not present
            - name: Company name
            - contact_email: Primary contact email
            - status: One of 'active', 'failing', 'suspended', 'closed'
            - financial_data: Object with financial metrics
            - metrics: Object with numerical performance metrics
            
            Raw data: {raw_data}
            
            Return only valid JSON, no additional text.
            """
            
            response = await self.model.generate_content_async(prompt)
            
            if response.text:
                # Parse JSON response
                import json
                try:
                    structured_data = json.loads(response.text)
                    
                    # Ensure required fields exist
                    if 'company_id' not in structured_data:
                        structured_data['company_id'] = str(uuid.uuid4())
                    
                    if 'status' not in structured_data:
                        structured_data['status'] = 'active'
                    
                    return structured_data
                    
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse JSON from ADK response: {response.text}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {str(e)}")
            return None
    
    def _create_company_data(self, structured_data: Dict[str, Any]) -> CompanyData:
        """Create CompanyData object from structured data"""
        return CompanyData(
            company_id=structured_data.get('company_id'),
            name=structured_data.get('name', ''),
            contact_email=structured_data.get('contact_email', ''),
            status=CompanyStatus(structured_data.get('status', 'active')),
            last_updated=get_current_timestamp(),
            financial_data=structured_data.get('financial_data', {}),
            metrics=structured_data.get('metrics', {})
        )
    
    async def batch_process_files(self, file_paths: List[str]) -> List[ExcelProcessingResult]:
        """Process multiple Excel files in batch"""
        results = []
        
        for file_path in file_paths:
            result = await self.process_excel_file(file_path)
            results.append(result)
        
        return results
    
    async def analyze_company_health(self, company_id: str) -> AgentResponse:
        """Analyze company health using Google ADK"""
        try:
            # Get company data from database
            company_data = await self.db_manager.get_company_data(company_id)
            
            if not company_data:
                return create_error_response(f"Company not found: {company_id}")
            
            # Calculate health score
            health_score = calculate_company_health_score(company_data.metrics)
            
            # Use Google ADK for detailed analysis
            prompt = f"""
            Analyze the following company data and provide insights:
            
            Company: {company_data.name}
            Status: {company_data.status.value}
            Health Score: {health_score}/100
            Financial Data: {company_data.financial_data}
            Metrics: {company_data.metrics}
            
            Provide a detailed analysis including:
            1. Current health assessment
            2. Key risk factors
            3. Recommendations for improvement
            4. Predicted trend for next quarter
            """
            
            response = await self.model.generate_content_async(prompt)
            
            analysis_data = {
                'company_id': company_id,
                'health_score': health_score,
                'analysis': response.text,
                'timestamp': get_current_timestamp()
            }
            
            return create_success_response(
                "Company health analysis completed",
                data=analysis_data
            )
            
        except Exception as e:
            error_msg = f"Failed to analyze company health: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def get_processing_status(self) -> AgentResponse:
        """Get current processing status"""
        try:
            # Get statistics from database
            stats = await self.db_manager.get_processing_statistics()
            
            return create_success_response(
                "Processing status retrieved",
                data=stats
            )
            
        except Exception as e:
            error_msg = f"Failed to get processing status: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)

# Usage example
async def main():
    agent = DataExtractionAgent()
    
    # Process a single Excel file
    result = await agent.process_excel_file("path/to/excel/file.xlsx")
    
    if result.success:
        print(f"Successfully processed {result.processed_rows} rows")
    else:
        print(f"Processing failed with {len(result.errors)} errors")
        for error in result.errors:
            print(f"  - {error}")

if __name__ == "__main__":
    asyncio.run(main())