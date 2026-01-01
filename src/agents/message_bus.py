"""
Agent Message Bus
Peer-to-peer message bus for multi-agent coordination

Enables multiple AI agents to collaborate on complex tasks without
a central orchestrator, using pub/sub pattern over WebSockets.
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Any
import asyncio
import json
from datetime import datetime


class AgentMessageBus:
    """
    Peer-to-peer message bus for agent coordination
    Supports topic-based publish/subscribe pattern
    """
    
    def __init__(self):
        self._agents: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> agent_ids
        self._agent_capabilities: Dict[str, List[str]] = {}  # agent_id -> capabilities
    
    async def register_agent(self, agent_id: str, websocket: WebSocket, capabilities: List[str] = None):
        """
        Register agent with message bus
        
        Args:
            agent_id: Unique agent identifier
            websocket: WebSocket connection
            capabilities: Optional list of agent capabilities
        """
        await websocket.accept()
        self._agents[agent_id] = websocket
        
        if capabilities:
            self._agent_capabilities[agent_id] = capabilities
        
        print(f"✓ Agent registered: {agent_id} (total: {len(self._agents)})")
        
        # Notify other agents
        await self.publish('agent_lifecycle', {
            'event': 'agent_connected',
            'agent_id': agent_id,
            'capabilities': capabilities or []
        }, sender_id='system')
    
    async def unregister_agent(self, agent_id: str):
        """
        Unregister agent from message bus
        
        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
        
        # Remove from all subscriptions
        for topic_subscribers in self._subscriptions.values():
            topic_subscribers.discard(agent_id)
        
        # Remove capabilities
        if agent_id in self._agent_capabilities:
            del self._agent_capabilities[agent_id]
        
        print(f"✓ Agent unregistered: {agent_id} (remaining: {len(self._agents)})")
        
        # Notify other agents
        await self.publish('agent_lifecycle', {
            'event': 'agent_disconnected',
            'agent_id': agent_id
        }, sender_id='system')
    
    async def subscribe(self, agent_id: str, topics: List[str]):
        """
        Subscribe agent to topics
        
        Args:
            agent_id: Agent identifier
            topics: List of topic names to subscribe to
        """
        for topic in topics:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(agent_id)
        
        print(f"  → Agent {agent_id} subscribed to topics: {', '.join(topics)}")
    
    async def unsubscribe(self, agent_id: str, topics: List[str]):
        """
        Unsubscribe agent from topics
        
        Args:
            agent_id: Agent identifier
            topics: List of topic names to unsubscribe from
        """
        for topic in topics:
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(agent_id)
    
    async def publish(self, topic: str, message: Dict[str, Any], sender_id: str):
        """
        Publish message to all subscribed agents
        
        Args:
            topic: Topic name
            message: Message payload
            sender_id: ID of sending agent
        """
        if topic not in self._subscriptions:
            return
        
        message_payload = {
            'topic': topic,
            'sender': sender_id,
            'data': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to all subscribers except sender
        subscribers = self._subscriptions[topic]
        for agent_id in subscribers:
            if agent_id != sender_id and agent_id in self._agents:
                try:
                    await self._agents[agent_id].send_json(message_payload)
                except Exception as e:
                    print(f"  ✗ Failed to send to {agent_id}: {e}")
    
    async def request_collaboration(
        self, 
        requester_id: str,
        capability_needed: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request collaboration from agents with specific capability.
        Used for complex multi-step workflows.
        
        Args:
            requester_id: ID of requesting agent
            capability_needed: Required capability
            context: Collaboration context data
        
        Returns:
            Response summary
        """
        # Find agents with required capability
        capable_agents = [
            agent_id 
            for agent_id, capabilities in self._agent_capabilities.items()
            if capability_needed in capabilities and agent_id != requester_id
        ]
        
        if not capable_agents:
            return {
                'status': 'no_capable_agents',
                'capability': capability_needed,
                'available_agents': []
            }
        
        # Broadcast collaboration request
        await self.publish('collaboration_request', {
            'capability': capability_needed,
            'context': context,
            'requester': requester_id,
            'target_agents': capable_agents
        }, requester_id)
        
        print(f"  → Collaboration request: {capability_needed} from {requester_id} to {len(capable_agents)} agents")
        
        return {
            'status': 'broadcast_sent',
            'capability': capability_needed,
            'target_agents': capable_agents,
            'count': len(capable_agents)
        }
    
    async def direct_message(self, sender_id: str, recipient_id: str, message: Dict[str, Any]):
        """
        Send direct message to specific agent
        
        Args:
            sender_id: Sending agent ID
            recipient_id: Receiving agent ID
            message: Message payload
        """
        if recipient_id not in self._agents:
            raise ValueError(f"Recipient agent not found: {recipient_id}")
        
        message_payload = {
            'type': 'direct_message',
            'sender': sender_id,
            'data': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            await self._agents[recipient_id].send_json(message_payload)
            print(f"  → Direct message: {sender_id} → {recipient_id}")
        except Exception as e:
            print(f"  ✗ Direct message failed: {e}")
            raise
    
    def get_connected_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of connected agents
        
        Returns:
            List of agent information
        """
        return [
            {
                'agent_id': agent_id,
                'capabilities': self._agent_capabilities.get(agent_id, [])
            }
            for agent_id in self._agents.keys()
        ]
    
    def get_agent_subscriptions(self, agent_id: str) -> List[str]:
        """
        Get topics agent is subscribed to
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            List of topic names
        """
        return [
            topic 
            for topic, subscribers in self._subscriptions.items()
            if agent_id in subscribers
        ]


# Global message bus instance
message_bus = AgentMessageBus()


async def handle_agent_websocket(websocket: WebSocket, agent_id: str):
    """
    WebSocket handler for agent connections
    
    Args:
        websocket: WebSocket connection
        agent_id: Agent identifier
    """
    try:
        # Register agent
        await message_bus.register_agent(agent_id, websocket)
        
        # Message loop
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get('action')
                
                if action == 'subscribe':
                    topics = data.get('topics', [])
                    await message_bus.subscribe(agent_id, topics)
                    await websocket.send_json({'status': 'subscribed', 'topics': topics})
                
                elif action == 'unsubscribe':
                    topics = data.get('topics', [])
                    await message_bus.unsubscribe(agent_id, topics)
                    await websocket.send_json({'status': 'unsubscribed', 'topics': topics})
                
                elif action == 'publish':
                    topic = data.get('topic')
                    message = data.get('message', {})
                    await message_bus.publish(topic, message, agent_id)
                    await websocket.send_json({'status': 'published', 'topic': topic})
                
                elif action == 'request_collaboration':
                    capability = data.get('capability')
                    context = data.get('context', {})
                    result = await message_bus.request_collaboration(agent_id, capability, context)
                    await websocket.send_json({'status': 'collaboration_requested', 'result': result})
                
                elif action == 'direct_message':
                    recipient = data.get('recipient')
                    message = data.get('message', {})
                    await message_bus.direct_message(agent_id, recipient, message)
                    await websocket.send_json({'status': 'message_sent', 'recipient': recipient})
                
                elif action == 'get_agents':
                    agents = message_bus.get_connected_agents()
                    await websocket.send_json({'status': 'ok', 'agents': agents})
                
                else:
                    await websocket.send_json({'status': 'error', 'message': f'Unknown action: {action}'})
            
            except json.JSONDecodeError:
                await websocket.send_json({'status': 'error', 'message': 'Invalid JSON'})
            except Exception as e:
                await websocket.send_json({'status': 'error', 'message': str(e)})
    
    except WebSocketDisconnect:
        print(f"  → Agent {agent_id} disconnected")
    except Exception as e:
        print(f"  ✗ Agent {agent_id} error: {e}")
    finally:
        await message_bus.unregister_agent(agent_id)

