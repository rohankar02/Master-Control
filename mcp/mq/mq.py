import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.db import db
from mcp.db.db import Member, MemberSubscription
from mcp.mq.consumer import MqConsumer
from mcp.mq.publisher import MqPublisher

# Modular state management
logger: Optional[logging.Logger] = None
config: Optional[Any] = None
consumer: Optional[MqConsumer] = None
publisher: Optional[MqPublisher] = None

def init(inc_config: Any, obs: Any) -> None:
    """Initialize AMQP consumers and publishers.

    Args:
        inc_config: Config object containing 'amqp' section.
        obs: Observable instance for event handling.
    """
    global logger, config, consumer, publisher
    logger = logging.getLogger(__name__)
    config = inc_config
    
    # Event registration
    obs.on("door_unlock_attempt", handle_door_unlock)
    obs.on("door_ping", handle_heartbeat)
    
    logger.info("Initializing AMQP infrastructure...")
    
    mq_user = config.get('amqp', "username")
    mq_pass = config.get('amqp', "password")
    mq_host = f"{config.get('amqp', 'host')}:{config.get('amqp', 'port')}"
    mq_url = f"amqp://{mq_user}:{mq_pass}@{mq_host}"
    
    # Initialize components
    consumer = MqConsumer(config.get('amqp', "recv_queue"), mq_url, handle_mq_event)
    publisher = MqPublisher(config.get('amqp', "announce_exchange"), mq_url)

    # Start background workers
    for component in [consumer, publisher]:
        thread = threading.Thread(target=component.start)
        thread.daemon = True
        thread.start()
        logger.debug(f"Started background thread for {component.__class__.__name__}")

def handle_door_unlock(member: Optional[Member], door: Any, access_permitted: bool, fob_number: str) -> None:
    """Broadcasts a door unlock event to the network."""
    amp_info = None
    announce = False
    name = "UNKNOWN"
    
    if member:
        amp_info = {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name
        }
        announce = member.announce
        name = member.get_announce_name()
        
    event = {
        "type": "UNLOCK_ATTEMPT",
        "permitted": access_permitted,
        "doorName": door.name,
        "doorId": door.id,
        "fobNumber": fob_number,
        "announce": announce,
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "ampInfo": amp_info
    }
    
    if publisher:
        publisher.publish(event)

def handle_heartbeat(device: Any) -> None:
    """Broadcasts a device health check (ping)."""
    event = {
        "type": "DOOR_PING",
        "timestamp": datetime.now().isoformat(),
        "id": device.address,
        "active": device.is_active
    }
    if publisher:
        publisher.publish(event)

def handle_mq_event(body: str) -> None:
    """Processes incoming messages from the message queue.

    Currently supports:
    - MEMBER_UPDATED: Synchronizes local member cache with central server.
    """
    if not logger: return
    
    try:
        data: Dict[str, Any] = json.loads(body)
        event_type = data.get("type")
        
        if event_type == "MEMBER_UPDATED":
            _process_member_update(data)
        else:
            logger.warning(f"Unsupported event type received: {event_type}")
            
    except json.JSONDecodeError:
        logger.error(f"Failed to decode message body: {body}")
    except Exception as e:
        logger.error(f"Error processing MQ event: {str(e)}", exc_info=True)

def _process_member_update(data: Dict[str, Any]) -> None:
    """Internal helper to synchronize member records."""
    if not db.session:
        logger.error("Database session not initialized")
        return

    fob = data.get("fob_number")
    # Sanitize fob number
    if not fob or fob.strip() in [None, 'N/A', '']:
        fob = ''
    else:
        fob = fob.strip()

    member_id = data.get("id")
    member = db.session.query(Member).filter(Member.id == member_id).first()
    
    door_access = data.get("door_access", {})
    
    if member is None:
        member = Member(
            id=member_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            announce=door_access.get("announce", False),
            nickname=data.get("nickname"),
            fob=fob,
            last_unlock=datetime.min,
            director=data.get("is_director", False)
        )
        db.session.add(member)
    else:
        member.first_name = data.get("first_name")
        member.last_name = data.get("last_name")
        member.announce = door_access.get("announce", False)
        member.nickname = data.get("nickname")
        member.fob = fob
        member.director = data.get("is_director", False)

    # Sync subscriptions
    db.session.query(MemberSubscription).filter(MemberSubscription.member_id == member_id).delete()
    
    for access in door_access.get("access", []):
        end_date = access.get("end") or "2999-01-01"
        subscription = MemberSubscription(
            member=member,
            date_from=datetime.strptime(access["start"], "%Y-%m-%d"),
            date_to=datetime.strptime(end_date, "%Y-%m-%d"),
            buffer_days=access.get("buffer_days", 0)
        )
        db.session.add(subscription)
    
    logger.info(f"Synchronized member profile: {member.get_announce_name()} (ID: {member_id})")
    db.session.commit()
    db.session.expire_all()

