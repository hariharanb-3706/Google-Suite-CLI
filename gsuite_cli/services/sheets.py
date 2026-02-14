"""
Google Sheets service integration
"""

import logging
from typing import List, Dict, Any, Optional, Union

from googleapiclient.errors import HttpError

from ..auth.oauth import OAuthManager
from ..utils.formatters import print_error

logger = logging.getLogger(__name__)


class SheetsService:
    """Google Sheets API service wrapper"""
    
    def __init__(self, oauth_manager: OAuthManager):
        self.oauth_manager = oauth_manager
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """Initialize the Sheets service"""
        try:
            self.service = self.oauth_manager.build_service('sheets', 'v4')
            return self.service is not None
        except Exception as e:
            logger.error(f"Failed to initialize Sheets service: {e}")
            return False
    
    def list_spreadsheets(self) -> List[Dict[str, Any]]:
        """List all spreadsheets"""
        if not self.service:
            return []
        
        try:
            result = self.service.spreadsheets().list().execute()
            spreadsheets = result.get('spreadsheets', [])
            
            formatted_spreadsheets = []
            for spreadsheet in spreadsheets:
                formatted_spreadsheets.append({
                    'id': spreadsheet.get('spreadsheetId'),
                    'name': spreadsheet.get('name'),
                    'url': spreadsheet.get('spreadsheetUrl'),
                    'created_time': spreadsheet.get('createdTime', ''),
                    'modified_time': spreadsheet.get('modifiedTime', ''),
                })
            
            return formatted_spreadsheets
        except HttpError as e:
            logger.error(f"Failed to list spreadsheets: {e}")
            print_error(f"Failed to list spreadsheets: {e}")
            return []
    
    def get_spreadsheet(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """Get spreadsheet metadata"""
        if not self.service:
            return None
        
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                includeGridData=False
            ).execute()
            
            sheets = []
            for sheet in result.get('sheets', []):
                properties = sheet.get('properties', {})
                sheets.append({
                    'sheet_id': properties.get('sheetId'),
                    'title': properties.get('title'),
                    'index': properties.get('index'),
                    'sheet_type': properties.get('sheetType'),
                    'grid_properties': properties.get('gridProperties', {}),
                })
            
            return {
                'spreadsheet_id': result.get('spreadsheetId'),
                'properties': result.get('properties', {}),
                'sheets': sheets,
                'spreadsheet_url': result.get('spreadsheetUrl'),
            }
        except HttpError as e:
            logger.error(f"Failed to get spreadsheet {spreadsheet_id}: {e}")
            print_error(f"Failed to get spreadsheet: {e}")
            return None
    
    def read_range(self, 
                   spreadsheet_id: str, 
                   range_name: str,
                   value_render_option: str = 'FORMATTED_VALUE') -> List[List[Any]]:
        """Read a range of cells from a spreadsheet"""
        if not self.service:
            return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueRenderOption=value_render_option
            ).execute()
            
            values = result.get('values', [])
            return values
        except HttpError as e:
            logger.error(f"Failed to read range {range_name}: {e}")
            print_error(f"Failed to read range: {e}")
            return []
    
    def write_range(self,
                    spreadsheet_id: str,
                    range_name: str,
                    values: List[List[Any]],
                    value_input_option: str = 'USER_ENTERED') -> bool:
        """Write values to a range of cells"""
        if not self.service:
            return False
        
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            updated_rows = result.get('updatedRows')
            updated_columns = result.get('updatedColumns')
            updated_cells = result.get('updatedCells')
            
            logger.info(f"Updated {updated_cells} cells ({updated_rows} rows, {updated_columns} columns)")
            return True
        except HttpError as e:
            logger.error(f"Failed to write range {range_name}: {e}")
            print_error(f"Failed to write range: {e}")
            return False
    
    def append_rows(self,
                    spreadsheet_id: str,
                    range_name: str,
                    values: List[List[Any]],
                    value_input_option: str = 'USER_ENTERED') -> bool:
        """Append rows to a spreadsheet"""
        if not self.service:
            return False
        
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updated_rows = result.get('updates', {}).get('updatedRows')
            logger.info(f"Appended {updated_rows} rows")
            return True
        except HttpError as e:
            logger.error(f"Failed to append rows to {range_name}: {e}")
            print_error(f"Failed to append rows: {e}")
            return False
    
    def clear_range(self,
                    spreadsheet_id: str,
                    range_name: str) -> bool:
        """Clear a range of cells"""
        if not self.service:
            return False
        
        try:
            result = self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body={}
            ).execute()
            
            cleared_cells = result.get('clearedRange')
            logger.info(f"Cleared range: {cleared_cells}")
            return True
        except HttpError as e:
            logger.error(f"Failed to clear range {range_name}: {e}")
            print_error(f"Failed to clear range: {e}")
            return False
    
    def create_spreadsheet(self,
                          title: str,
                          sheets: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Create a new spreadsheet"""
        if not self.service:
            return None
        
        try:
            spreadsheet_body = {
                'properties': {
                    'title': title
                }
            }
            
            if sheets:
                spreadsheet_body['sheets'] = sheets
            
            result = self.service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            spreadsheet_id = result.get('spreadsheetId')
            logger.info(f"Created spreadsheet: {spreadsheet_id}")
            return spreadsheet_id
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            print_error(f"Failed to create spreadsheet: {e}")
            return None
    
    def add_sheet(self,
                  spreadsheet_id: str,
                  title: str) -> Optional[int]:
        """Add a new sheet to a spreadsheet"""
        if not self.service:
            return None
        
        try:
            body = {
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': title
                            }
                        }
                    }
                ]
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            sheet_id = result.get('replies', [{}])[0].get('addSheet', {}).get('properties', {}).get('sheetId')
            logger.info(f"Added sheet '{title}' with ID: {sheet_id}")
            return sheet_id
        except HttpError as e:
            logger.error(f"Failed to add sheet '{title}': {e}")
            print_error(f"Failed to add sheet: {e}")
            return None
    
    def delete_sheet(self,
                     spreadsheet_id: str,
                     sheet_id: int) -> bool:
        """Delete a sheet from a spreadsheet"""
        if not self.service:
            return False
        
        try:
            body = {
                'requests': [
                    {
                        'deleteSheet': {
                            'sheetId': sheet_id
                        }
                    }
                ]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"Deleted sheet with ID: {sheet_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete sheet {sheet_id}: {e}")
            print_error(f"Failed to delete sheet: {e}")
            return False
    
    def get_sheet_data(self,
                       spreadsheet_id: str,
                       sheet_name: str,
                       header_row: int = 1) -> List[Dict[str, Any]]:
        """Get sheet data as list of dictionaries (with headers)"""
        if not self.service:
            return []
        
        try:
            # Get headers
            header_range = f"'{sheet_name}'!A{header_row}:Z{header_row}"
            headers_result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=header_range
            ).execute()
            
            headers = headers_result.get('values', [[]])[0]
            if not headers:
                return []
            
            # Get data rows
            data_range = f"'{sheet_name}'!A{header_row + 1}"
            data_result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=data_range
            ).execute()
            
            rows = data_result.get('values', [])
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = value
                data.append(row_dict)
            
            return data
        except HttpError as e:
            logger.error(f"Failed to get sheet data for '{sheet_name}': {e}")
            print_error(f"Failed to get sheet data: {e}")
            return []
    
    def batch_update(self,
                     spreadsheet_id: str,
                     requests: List[Dict[str, Any]]) -> bool:
        """Perform batch updates on a spreadsheet"""
        if not self.service:
            return False
        
        try:
            body = {
                'requests': requests
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            total_updates = len(result.get('replies', []))
            logger.info(f"Performed {total_updates} batch updates")
            return True
        except HttpError as e:
            logger.error(f"Failed to perform batch updates: {e}")
            print_error(f"Failed to perform batch updates: {e}")
            return False
    
    def format_range(self,
                     spreadsheet_id: str,
                     range_name: str,
                     format: Dict[str, Any]) -> bool:
        """Format a range of cells"""
        if not self.service:
            return False
        
        try:
            body = {
                'requests': [
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': format.get('sheetId', 0),
                                'startRowIndex': format.get('startRowIndex', 0),
                                'endRowIndex': format.get('endRowIndex', 1000),
                                'startColumnIndex': format.get('startColumnIndex', 0),
                                'endColumnIndex': format.get('endColumnIndex', 26),
                            },
                            'cell': {
                                'userEnteredFormat': format.get('userEnteredFormat', {})
                            },
                            'fields': 'userEnteredFormat'
                        }
                    }
                ]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"Formatted range: {range_name}")
            return True
        except HttpError as e:
            logger.error(f"Failed to format range {range_name}: {e}")
            print_error(f"Failed to format range: {e}")
            return False
