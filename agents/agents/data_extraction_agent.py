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
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import GOOGLE_ADK_CONFIG, DATABASE_CONFIG, AGENT_CONFIG
from shared.types import (
    CompanyData, ExcelProcessingResult, AgentResponse, 
    CompanyStatus, AlertSeverity
)
from shared.utils import (
    setup_logging, create_success_response, create_error_response,
    validate_company_data, parse_excel_data, calculate_company_health_score,
    get_current_timestamp
)
from tools.database import DatabaseManager
from tools.file_operations import FileProcessor
from mcp_tools_client import get_unified_mcp_client

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
        
        # Store reference to unified MCP tools client
        self.mcp_tools = None
        
        self.logger.info(f"Data Extraction Agent initialized with model: {self.config.model}")
    
    async def initialize_mcp_tools(self):
        """Initialize unified MCP tools client with access to ALL MCP servers"""
        if self.mcp_tools is None:
            self.mcp_tools = await get_unified_mcp_client(self.logger)
            available_tools = self.mcp_tools.get_available_tools()
            total_tools = sum(len(tools) for tools in available_tools.values())
            self.logger.info(f"Initialized with {total_tools} MCP tools from {len(available_tools)} servers")
            
            # Log available tools for debugging
            for server, tools in available_tools.items():
                self.logger.info(f"  {server}: {len(tools)} tools - {tools[:3]}...")
    
    def set_mcp_tools(self, mcp_tools):
        """Set MCP tools for backwards compatibility"""
        self.mcp_tools = mcp_tools
        self.logger.info("MCP tools configured for operations")
    
    async def process_excel_file(self, file_path: str) -> ExcelProcessingResult:
        """Process an Excel file and extract company data using MCP Excel tools"""
        try:
            # Initialize MCP tools if not already done
            await self.initialize_mcp_tools()
            
            self.logger.info(f"Processing Excel file: {file_path}")
            
            # Get workbook metadata first
            workbook_info = await self._get_workbook_info(file_path)
            if not workbook_info:
                return ExcelProcessingResult(
                    success=False,
                    company_data=None,
                    errors=["Failed to read workbook metadata"],
                    warnings=[],
                    processed_rows=0
                )
            
            # Process the first sheet (or main data sheet)
            sheet_name = workbook_info.get('sheets', [{}])[0].get('name', 'Sheet1')
            
            # Read data from Excel using MCP tools
            excel_data = await self._read_excel_data(file_path, sheet_name)
            if not excel_data:
                return ExcelProcessingResult(
                    success=False,
                    company_data=None,
                    errors=["Failed to read Excel data"],
                    warnings=[],
                    processed_rows=0
                )
            
            processed_rows = 0
            errors = []
            warnings = []
            company_data_list = []
            
            # Process each row of data
            for index, cell_data in enumerate(excel_data.get('cells', [])):
                try:
                    # Convert cell data to row dictionary
                    row_dict = self._convert_cells_to_row(cell_data, index)
                    
                    if not row_dict:  # Skip empty rows
                        continue
                    
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
    
    async def _get_workbook_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get workbook metadata using MCP Excel tools"""
        try:
            if not self.mcp_tools:
                self.logger.warning("MCP tools not configured, falling back to pandas")
                return {"sheets": [{"name": "Sheet1"}]}
            
            # Use MCP tool to get workbook metadata
            result = await self.mcp_tools.call_tool("get_workbook_metadata", {
                "filepath": file_path,
                "include_ranges": True
            })
            
            if isinstance(result, str):
                # Parse string response
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse workbook metadata: {result}")
                    return {"sheets": [{"name": "Sheet1"}]}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting workbook info: {str(e)}")
            return None
    
    async def _read_excel_data(self, file_path: str, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Read Excel data using MCP Excel tools"""
        try:
            if not self.mcp_tools:
                self.logger.warning("MCP tools not configured, falling back to pandas")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # Convert to MCP-like format
                cells = []
                for idx, row in df.iterrows():
                    for col, value in row.items():
                        cells.append({
                            "address": f"{col}{idx+1}",
                            "value": value,
                            "row": idx+1,
                            "column": col
                        })
                return {"cells": cells}
            
            # Use MCP tool to read Excel data
            result = await self.mcp_tools.call_tool("read_data_from_excel", {
                "filepath": file_path,
                "sheet_name": sheet_name,
                "start_cell": "A1",
                "preview_only": False
            })
            
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse Excel data: {result}")
                    return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading Excel data: {str(e)}")
            return None
    
    def _convert_cells_to_row(self, cell_data: Dict[str, Any], row_index: int) -> Optional[Dict[str, Any]]:
        """Convert cell data to row dictionary"""
        try:
            if not isinstance(cell_data, dict):
                return None
            
            # Group cells by row
            row_data = {}
            for cell in cell_data.get('cells', []):
                if cell.get('row') == row_index + 1:  # Excel rows are 1-indexed
                    column = cell.get('column', '')
                    value = cell.get('value')
                    if value is not None:
                        row_data[column] = value
            
            return row_data if row_data else None
            
        except Exception as e:
            self.logger.error(f"Error converting cells to row: {str(e)}")
            return None
    
    async def research_company_online(self, company_name: str, company_website: str = None) -> AgentResponse:
        """Research a company online using web scraping tools"""
        try:
            await self.initialize_mcp_tools()
            
            research_data = {
                "company_name": company_name,
                "website_data": None,
                "search_results": None,
                "analysis": None,
                "timestamp": get_current_timestamp()
            }
            
            # If we have a website, scrape it directly
            if company_website:
                try:
                    website_content = await self.mcp_tools.call_tool("firecrawl_scrape", {
                        "url": company_website,
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    })
                    research_data["website_data"] = website_content
                    self.logger.info(f"Successfully scraped {company_website}")
                except Exception as e:
                    self.logger.warning(f"Failed to scrape {company_website}: {str(e)}")
            
            # Search for company information online
            try:
                search_query = f"{company_name} financial data revenue business information"
                search_results = await self.mcp_tools.call_tool("firecrawl_search", {
                    "query": search_query,
                    "limit": 5,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    }
                })
                research_data["search_results"] = search_results
                self.logger.info(f"Found search results for {company_name}")
            except Exception as e:
                self.logger.warning(f"Failed to search for {company_name}: {str(e)}")
            
            # Use Google ADK to analyze the gathered data
            if research_data["website_data"] or research_data["search_results"]:
                analysis_prompt = f"""
                Analyze the following web data about {company_name} and provide insights:
                
                Website Data: {research_data.get("website_data", "Not available")}
                Search Results: {research_data.get("search_results", "Not available")}
                
                Provide analysis including:
                1. Company overview and business model
                2. Financial health indicators
                3. Market position and competitors
                4. Risk factors and opportunities
                5. Recent news or developments
                """
                
                try:
                    response = await self.model.generate_content_async(analysis_prompt)
                    research_data["analysis"] = response.text
                except Exception as e:
                    self.logger.error(f"Failed to analyze research data: {str(e)}")
            
            return create_success_response(
                f"Online research completed for {company_name}",
                data=research_data
            )
            
        except Exception as e:
            error_msg = f"Failed to research {company_name} online: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def search_excel_files(self, search_path: str = "~", filename_pattern: str = "*.xlsx", include_subdirs: bool = True) -> AgentResponse:
        """Search for Excel files on the filesystem"""
        try:
            await self.initialize_mcp_tools()
            
            # Get common Excel locations first
            common_locations = await self.mcp_tools.call_tool("get_common_excel_locations", {})
            
            # Search for Excel files
            search_results = await self.mcp_tools.call_tool("search_excel_files", {
                "search_path": search_path,
                "filename_pattern": filename_pattern,
                "include_subdirs": include_subdirs,
                "max_results": 50
            })
            
            if isinstance(search_results, str):
                try:
                    search_data = json.loads(search_results)
                except json.JSONDecodeError:
                    return create_error_response(f"Failed to parse search results: {search_results}")
            else:
                search_data = search_results
            
            if isinstance(common_locations, str):
                try:
                    locations_data = json.loads(common_locations)
                except json.JSONDecodeError:
                    locations_data = {}
            else:
                locations_data = common_locations
            
            result_data = {
                "search_results": search_data,
                "common_locations": locations_data,
                "timestamp": get_current_timestamp()
            }
            
            return create_success_response(
                f"Found {search_data.get('total_found', 0)} Excel files",
                data=result_data
            )
            
        except Exception as e:
            error_msg = f"Failed to search for Excel files: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
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