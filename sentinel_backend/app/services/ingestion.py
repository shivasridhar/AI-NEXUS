from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from typing import Dict, Any
from pydantic import ValidationError
import logging
import time

from app.services.cloudtrail_parser import CloudTrailParser
from app.services.identity_discovery import IdentityDiscoveryEngine
from app.models.access_log import AccessLog

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.discovery_engine = IdentityDiscoveryEngine(db)

    def process_cloudtrail_json(self, json_data: Dict[str, Any], job_id: str = None, filename: str = None, workspace_id: str = None) -> Dict[str, Any]:
        """
        Main pipeline for processing CloudTrail JSON logs.
        Returns processing statistics.
        """
        stats = {
            "total_events": 0,
            "identities_discovered": 0,
            "access_logs_created": 0,
            "inserted": 0,
            "duplicates": 0,
            "failed": 0,
            "new_logs": [],
            "new_identity_arns": set(),
            "identities_created_count": 0,
            "identities_updated_count": 0
        }

        start_time = time.time()

        try:
            events = CloudTrailParser.parse_log_file(json_data)
        except Exception as e:
            logger.error("Failed to parse CloudTrail log file: %s", e)
            stats["failed"] = 1
            # Re-raise standard value errors for endpoint user-friendly error formatting
            raise e

        stats["total_events"] = len(events)
        
        # Track unique identities updated in this batch for stats
        unique_arns = set()

        for event in events:
            try:
                # 1. Parse and extract AccessLog data
                access_log_data = CloudTrailParser.extract_access_log_data(event)
                access_log_data["workspace_id"] = workspace_id
                
                # 2. Insert AccessLog using Postgres-native ON CONFLICT DO NOTHING
                stmt = insert(AccessLog).values(**access_log_data).on_conflict_do_nothing(index_elements=['event_id', 'workspace_id'])
                res = self.db.execute(stmt)
                
                # Check rowcount to verify if the event was inserted or skipped as duplicate
                if res.rowcount == 0:
                    stats["duplicates"] += 1
                    continue
                
                # 3. Discover/Update Identity (only runs for new/inserted events)
                identity_type = event.userIdentity.type
                arn = access_log_data["identity_arn"]
                
                # Determine if identity already exists before discovery to track created/updated stats
                from app.models.machine_identity import MachineIdentity
                existing_identity = self.db.query(MachineIdentity).filter(MachineIdentity.arn == arn, MachineIdentity.workspace_id == workspace_id).first()
                
                identity = self.discovery_engine.discover_identity(
                    arn=arn,
                    identity_type=identity_type,
                    account_id=access_log_data["account_id"],
                    event_time=access_log_data["event_time"],
                    workspace_id=workspace_id
                )
                
                if identity:
                    if existing_identity:
                        stats["identities_updated_count"] += 1
                    else:
                        stats["identities_created_count"] += 1
                        
                    if arn not in unique_arns:
                        unique_arns.add(arn)
                        stats["identities_discovered"] += 1

                # Construct log model representation for downstream services without duplicating inserts
                access_log = AccessLog(**access_log_data)
                stats["new_logs"].append(access_log)
                stats["new_identity_arns"].add(arn)

                stats["inserted"] += 1
                stats["access_logs_created"] += 1
                    
            except Exception as e:
                logger.error("Error processing event {event.eventID}: %s", e)
                stats["failed"] += 1
                # Rollback transaction immediately and stop ingestion on real database failures
                self.db.rollback()
                raise e

        self.db.commit()
        
        duration = time.time() - start_time
        logger.info(
            f"Ingestion completed: job_id={job_id}, filename={filename}, "
            f"inserted={stats['inserted']}, duplicates={stats['duplicates']}, "
            f"failed={stats['failed']}, duration_sec={duration:.3f}s"
        )
        
        return stats
