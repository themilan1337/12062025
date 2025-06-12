import asyncio
import json
import logging
import base64
from typing import Dict, Optional
from fastapi import WebSocket
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

class VoiceChatManager:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.active_voice_sessions: Dict[str, Dict] = {}
        
    async def start_voice_session(self, websocket: WebSocket, session_id: str, user_id: int):
        """Start a new voice chat session with OpenAI Realtime API"""
        try:
            # Connect to OpenAI Realtime API
            async with self.openai_client.beta.realtime.connect(
                model="gpt-4o-realtime-preview"
            ) as connection:
                
                # Configure session for audio
                await connection.session.update(session={
                    'modalities': ['audio', 'text'],
                    'instructions': 'You are a helpful voice assistant. Respond naturally and conversationally.',
                    'voice': 'alloy',
                    'input_audio_format': 'pcm16',
                    'output_audio_format': 'pcm16',
                    'input_audio_transcription': {
                        'model': 'whisper-1'
                    }
                })
                
                # Store session info
                self.active_voice_sessions[session_id] = {
                    'connection': connection,
                    'websocket': websocket,
                    'user_id': user_id,
                    'is_active': True
                }
                
                logger.info(f"Voice session {session_id} started for user {user_id}")
                
                # Handle OpenAI events and WebSocket messages concurrently
                await asyncio.gather(
                    self._handle_openai_events(session_id, connection),
                    self._handle_websocket_messages(session_id, websocket, connection),
                    return_exceptions=True
                )
                
        except Exception as e:
            logger.error(f"Error in voice session {session_id}: {e}")
            await self._cleanup_session(session_id)
            
    async def _handle_openai_events(self, session_id: str, connection):
        """Handle events from OpenAI Realtime API"""
        try:
            async for event in connection:
                if session_id not in self.active_voice_sessions:
                    break
                    
                session = self.active_voice_sessions[session_id]
                websocket = session['websocket']
                
                if event.type == 'response.audio.delta':
                    # Send audio data to client
                    audio_data = base64.b64encode(event.delta).decode('utf-8')
                    await websocket.send_text(json.dumps({
                        'type': 'audio_delta',
                        'audio': audio_data
                    }))
                    
                elif event.type == 'response.audio.done':
                    # Audio response completed
                    await websocket.send_text(json.dumps({
                        'type': 'audio_done'
                    }))
                    
                elif event.type == 'response.text.delta':
                    # Send text transcription to client
                    await websocket.send_text(json.dumps({
                        'type': 'text_delta',
                        'text': event.delta
                    }))
                    
                elif event.type == 'response.text.done':
                    # Text response completed
                    await websocket.send_text(json.dumps({
                        'type': 'text_done',
                        'text': event.text
                    }))
                    
                elif event.type == 'input_audio_buffer.speech_started':
                    # User started speaking
                    await websocket.send_text(json.dumps({
                        'type': 'speech_started'
                    }))
                    
                elif event.type == 'input_audio_buffer.speech_stopped':
                    # User stopped speaking
                    await websocket.send_text(json.dumps({
                        'type': 'speech_stopped'
                    }))
                    
                elif event.type == 'conversation.item.input_audio_transcription.completed':
                    # User's speech transcription completed
                    await websocket.send_text(json.dumps({
                        'type': 'user_transcription',
                        'text': event.transcript
                    }))
                    
                elif event.type == 'error':
                    logger.error(f"OpenAI API error in session {session_id}: {event.error}")
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': str(event.error)
                    }))
                    
        except Exception as e:
            logger.error(f"Error handling OpenAI events for session {session_id}: {e}")
            
    async def _handle_websocket_messages(self, session_id: str, websocket: WebSocket, connection):
        """Handle messages from WebSocket client"""
        try:
            while session_id in self.active_voice_sessions:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get('type') == 'audio_data':
                        # Receive audio data from client and send to OpenAI
                        audio_bytes = base64.b64decode(message['audio'])
                        await connection.input_audio_buffer.append(audio=audio_bytes)
                        
                    elif message.get('type') == 'audio_commit':
                        # Commit audio buffer and generate response
                        await connection.input_audio_buffer.commit()
                        await connection.response.create()
                        
                    elif message.get('type') == 'text_message':
                        # Handle text message
                        await connection.conversation.item.create(
                            item={
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": message['text']}],
                            }
                        )
                        await connection.response.create()
                        
                    elif message.get('type') == 'interrupt':
                        # Interrupt current response
                        await connection.response.cancel()
                        
                    elif message.get('type') == 'end_session':
                        # End the voice session
                        await self._cleanup_session(session_id)
                        break
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received in voice session {session_id}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message in session {session_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in WebSocket handler for session {session_id}: {e}")
            
    async def _cleanup_session(self, session_id: str):
        """Clean up voice session"""
        if session_id in self.active_voice_sessions:
            session = self.active_voice_sessions[session_id]
            session['is_active'] = False
            
            try:
                # Send session end message to client
                await session['websocket'].send_text(json.dumps({
                    'type': 'session_ended'
                }))
            except Exception as e:
                logger.error(f"Error sending session end message: {e}")
                
            del self.active_voice_sessions[session_id]
            logger.info(f"Voice session {session_id} cleaned up")
            
    async def end_session(self, session_id: str):
        """Manually end a voice session"""
        await self._cleanup_session(session_id)
        
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get all active voice sessions"""
        return {sid: {'user_id': session['user_id'], 'is_active': session['is_active']} 
                for sid, session in self.active_voice_sessions.items()}

# Global voice chat manager instance
voice_manager = VoiceChatManager()