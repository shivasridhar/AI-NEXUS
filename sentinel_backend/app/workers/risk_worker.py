import asyncio
import json
import logging
from sqlalchemy.orm import Session
from app.core.redis_client import get_redis_client
from app.db.session import SessionLocal
from app.graph.session import neo4j_manager
from app.models.ingestion_job import IngestionJob
from app.services.risk_engine.engine import RiskEngine
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

async def risk_worker():
    redis = await get_redis_client()
    stream_name = "risk_evaluation_events"
    group_name = "risk_workers_group"
    consumer_name = "worker-1"
    
    # Ensure group exists
    try:
        await redis.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP Consumer Group name already exists" not in str(e):
            logger.error(f"Error creating consumer group: {e}")
            
    logger.info(f"Started risk worker on stream {stream_name}")

    while True:
        try:
            # Block for up to 2 seconds waiting for new events
            events = await redis.xreadgroup(group_name, consumer_name, {stream_name: ">"}, count=1, block=2000)
            
            if not events:
                await asyncio.sleep(1)
                continue
                
            for stream, messages in events:
                for message_id, data in messages:
                    job_id = data.get("job_id")
                    workspace_id = data.get("workspace_id")
                    arns_str = data.get("new_identity_arns")
                    
                    if not all([job_id, workspace_id, arns_str]):
                        logger.error(f"Invalid event data: {data}")
                        await redis.xack(stream_name, group_name, message_id)
                        continue
                        
                    db = SessionLocal()
                    neo4j_session = None
                    try:
                        arns = json.loads(arns_str)
                        
                        neo4j_session = neo4j_manager.get_session()
                        engine = RiskEngine(db, neo4j_session)
                        
                        logger.info(f"Evaluating {len(arns)} identities for job {job_id}")
                        # In run_in_threadpool if this was FastAPI, but here we can just call it
                        # Since it's synchronous DB IO, it blocks this worker's event loop.
                        # For a dedicated worker process, this is acceptable.
                        findings_count = engine.evaluate_new_identities(arns, workspace_id)
                        
                        # Mark job as completed
                        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
                        if job:
                            job.status = 'completed'
                            job.risk_findings_generated = findings_count
                            job.completed_at = func.now()
                            db.commit()
                            
                    except Exception as e:
                        logger.error(f"Error processing job {job_id}: {e}")
                        db.rollback()
                        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
                        if job:
                            job.status = 'failed'
                            job.error_message = str(e)[:1000]
                            job.completed_at = func.now()
                            db.commit()
                    finally:
                        if neo4j_session:
                            neo4j_session.close()
                        db.close()
                        
                    # Ack message
                    await redis.xack(stream_name, group_name, message_id)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(risk_worker())
