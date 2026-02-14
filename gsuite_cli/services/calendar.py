"""
Google Calendar service integration
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from googleapiclient.errors import HttpError

from ..auth.oauth import OAuthManager
from ..utils.formatters import print_error
from ..utils.cache import ServiceCache, cached

logger = logging.getLogger(__name__)


class CalendarService:
    """Google Calendar API service wrapper"""
    
    def __init__(self, oauth_manager: OAuthManager, cache_manager=None):
        self.oauth_manager = oauth_manager
        self.service = None
        self.cache = ServiceCache('calendar', cache_manager) if cache_manager else None
        self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """Initialize the Calendar service"""
        try:
            self.service = self.oauth_manager.build_service('calendar', 'v3')
            return self.service is not None
        except Exception as e:
            logger.error(f"Failed to initialize Calendar service: {e}")
            return False
    
    @cached('calendar.list', ttl=300)
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars"""
        if not self.service:
            return []
        
        # Try cache first
        if self.cache:
            cached_result = self.cache.get('list_calendars')
            if cached_result is not None:
                return cached_result
        
        try:
            result = self.service.calendarList().list().execute()
            calendars = result.get('items', [])
            
            formatted_calendars = []
            for calendar in calendars:
                formatted_calendars.append({
                    'id': calendar.get('id'),
                    'summary': calendar.get('summary'),
                    'description': calendar.get('description', ''),
                    'timezone': calendar.get('timeZone'),
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole'),
                })
            
            # Cache the result
            if self.cache:
                self.cache.set('list_calendars', formatted_calendars)
            
            return formatted_calendars
        except HttpError as e:
            logger.error(f"Failed to list calendars: {e}")
            print_error(f"Failed to list calendars: {e}")
            return []
    
    def list_events(self, 
                   calendar_id: str = 'primary',
                   time_min: Optional[datetime] = None,
                   time_max: Optional[datetime] = None,
                   max_results: int = 50,
                   query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List events from a calendar"""
        if not self.service:
            return []
        
        # Generate cache key
        cache_args = (calendar_id, time_min, time_max, max_results, query)
        if self.cache:
            cached_result = self.cache.get('list_events', *cache_args)
            if cached_result is not None:
                return cached_result
        
        try:
            # Build request parameters
            params = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if time_min:
                params['timeMin'] = time_min.isoformat() + 'Z'
            if time_max:
                params['timeMax'] = time_max.isoformat() + 'Z'
            if query:
                params['q'] = query
            
            result = self.service.events().list(**params).execute()
            events = result.get('items', [])
            
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': self._format_datetime(event.get('start', {})),
                    'end': self._format_datetime(event.get('end', {})),
                    'status': event.get('status'),
                    'created': self._format_datetime(event.get('created')),
                    'updated': self._format_datetime(event.get('updated')),
                }
                formatted_events.append(formatted_event)
            
            # Cache the result
            if self.cache:
                self.cache.set('list_events', formatted_events, 180, *cache_args)
            
            return formatted_events
        except HttpError as e:
            logger.error(f"Failed to list events: {e}")
            print_error(f"Failed to list events: {e}")
            return []
    
    def get_event(self, event_id: str, calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Get a specific event"""
        if not self.service:
            return None
        
        # Try cache first
        cache_args = (calendar_id, event_id)
        if self.cache:
            cached_result = self.cache.get('get_event', *cache_args)
            if cached_result is not None:
                return cached_result
        
        try:
            result = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            formatted_event = {
                'id': result.get('id'),
                'summary': result.get('summary', 'No title'),
                'description': result.get('description', ''),
                'location': result.get('location', ''),
                'start': self._format_datetime(result.get('start', {})),
                'end': self._format_datetime(result.get('end', {})),
                'status': result.get('status'),
                'created': self._format_datetime(result.get('created')),
                'updated': self._format_datetime(result.get('updated')),
                'attendees': result.get('attendees', []),
                'organizer': result.get('organizer', {}),
            }
            
            # Cache the result
            if self.cache:
                self.cache.set('get_event', formatted_event, *cache_args)
            
            return formatted_event
        except HttpError as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            print_error(f"Failed to get event: {e}")
            return None
    
    def create_event(self, 
                    calendar_id: str = 'primary',
                    summary: str = '',
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    description: str = '',
                    location: str = '',
                    attendees: Optional[List[str]] = None) -> Optional[str]:
        """Create a new event"""
        if not self.service:
            return None
        
        try:
            event_body = {
                'summary': summary,
                'description': description,
                'location': location,
            }
            
            # Set start and end times
            if start_time:
                event_body['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                }
            if end_time:
                event_body['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC'
                }
            
            # Add attendees
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            result = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            event_id = result.get('id')
            
            # Invalidate cache
            if self.cache:
                self.cache.invalidate('list_events')
            
            logger.info(f"Created event: {event_id}")
            return event_id
        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            print_error(f"Failed to create event: {e}")
            return None
    
    def update_event(self, 
                    event_id: str,
                    calendar_id: str = 'primary',
                    summary: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    description: Optional[str] = None,
                    location: Optional[str] = None) -> bool:
        """Update an existing event"""
        if not self.service:
            return False
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            if start_time:
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                }
            if end_time:
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC'
                }
            
            result = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            # Invalidate cache
            if self.cache:
                self.cache.invalidate('list_events')
                self.cache.invalidate('get_event', calendar_id, event_id)
            
            logger.info(f"Updated event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            print_error(f"Failed to update event: {e}")
            return False
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete an event"""
        if not self.service:
            return False
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Invalidate cache
            if self.cache:
                self.cache.invalidate('list_events')
                self.cache.invalidate('get_event', calendar_id, event_id)
            
            logger.info(f"Deleted event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            print_error(f"Failed to delete event: {e}")
            return False
    
    def search_events(self, 
                     query: str,
                     calendar_id: str = 'primary',
                     time_min: Optional[datetime] = None,
                     time_max: Optional[datetime] = None,
                     max_results: int = 50) -> List[Dict[str, Any]]:
        """Search events by query"""
        return self.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            query=query
        )
    
    def _format_datetime(self, dt_dict: Dict[str, Any]) -> str:
        """Format datetime dictionary to string"""
        if 'dateTime' in dt_dict:
            return dt_dict['dateTime']
        elif 'date' in dt_dict:
            return dt_dict['date']
        else:
            return ''
    
    def get_free_busy(self, 
                     time_min: datetime,
                     time_max: datetime,
                     calendar_ids: List[str] = None) -> Dict[str, Any]:
        """Get free/busy information for calendars"""
        if not self.service:
            return {}
        
        if calendar_ids is None:
            calendar_ids = ['primary']
        
        try:
            body = {
                'timeMin': time_min.isoformat() + 'Z',
                'timeMax': time_max.isoformat() + 'Z',
                'items': [{'id': cal_id} for cal_id in calendar_ids]
            }
            
            result = self.service.freebusy().query(body=body).execute()
            return result
        except HttpError as e:
            logger.error(f"Failed to get free/busy: {e}")
            print_error(f"Failed to get free/busy: {e}")
            return {}

    def create_calendar(self, summary: str, description: str = '', time_zone: str = 'UTC') -> Optional[Dict[str, Any]]:
        """Create a new secondary calendar"""
        if not self.service:
            return None
        
        try:
            calendar = {
                'summary': summary,
                'description': description,
                'timeZone': time_zone
            }
            
            created_calendar = self.service.calendars().insert(body=calendar).execute()
            
            # Invalidate cache
            if self.cache:
                self.cache.invalidate('list_calendars')
            
            logger.info(f"Created calendar: {created_calendar.get('id')}")
            return created_calendar
        except HttpError as e:
            logger.error(f"Failed to create calendar: {e}")
            print_error(f"Failed to create calendar: {e}")
            return None
