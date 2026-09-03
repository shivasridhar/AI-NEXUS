from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.api.dependencies import get_db, get_current_workspace, require_admin
from app.models.tenant import User
from app.models.tenant import Workspace
from app.models.integration import Integration
from app.models.ingestion_job import IngestionJob
from app.core.encryption import encrypt_credentials, decrypt_credentials
from app.services.ingestion_sources.aws_cloudtrail import AwsCloudTrailSource
from app.api.v1.endpoints.ingestion import execute_ingestion_pipeline

import boto3
from botocore.exceptions import ClientError

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
def list_integrations(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    List configured integrations for the workspace.
    """
    integrations = db.query(Integration).filter(Integration.workspace_id == workspace.id).all()
    
    configured_providers = {i.provider: i for i in integrations}
    
    result = []
    
    # AWS CloudTrail
    aws_info = {
        "provider": "aws",
        "name": "AWS CloudTrail",
        "status": configured_providers.get("aws").status if "aws" in configured_providers else "available",
    }
    if "aws" in configured_providers:
        integration = configured_providers["aws"]
        aws_info.update({
            "id": str(integration.id),
            "config": integration.config,
            "last_sync_time": integration.last_sync_time.isoformat() if integration.last_sync_time else None,
            "events_retrieved": integration.events_retrieved,
            "error_message": integration.error_message
        })
    result.append(aws_info)
    
    # Wazuh SIEM
    wazuh_info = {
        "provider": "wazuh",
        "name": "Wazuh SIEM",
        "status": configured_providers.get("wazuh").status if "wazuh" in configured_providers else "available",
    }
    if "wazuh" in configured_providers:
        integration = configured_providers["wazuh"]
        wazuh_info.update({
            "id": str(integration.id),
            "config": integration.config,
            "last_sync_time": integration.last_sync_time.isoformat() if integration.last_sync_time else None,
            "events_retrieved": integration.events_retrieved,
            "error_message": integration.error_message
        })
    result.append(wazuh_info)

    # Suricata IDS
    suricata_info = {
        "provider": "suricata",
        "name": "Suricata IDS",
        "status": configured_providers.get("suricata").status if "suricata" in configured_providers else "available",
    }
    if "suricata" in configured_providers:
        integration = configured_providers["suricata"]
        suricata_info.update({
            "id": str(integration.id),
            "config": integration.config,
            "last_sync_time": integration.last_sync_time.isoformat() if integration.last_sync_time else None,
            "events_retrieved": integration.events_retrieved,
            "error_message": integration.error_message
        })
    result.append(suricata_info)

    # OpenVAS Vulnerability Scanner
    openvas_info = {
        "provider": "openvas",
        "name": "OpenVAS Scanner",
        "status": configured_providers.get("openvas").status if "openvas" in configured_providers else "available",
    }
    if "openvas" in configured_providers:
        integration = configured_providers["openvas"]
        openvas_info.update({
            "id": str(integration.id),
            "config": integration.config,
            "last_sync_time": integration.last_sync_time.isoformat() if integration.last_sync_time else None,
            "events_retrieved": integration.events_retrieved,
            "error_message": integration.error_message
        })
    result.append(openvas_info)

    # Coming soon
    result.append({"provider": "azure", "name": "Azure AD", "status": "coming_soon"})
    result.append({"provider": "okta", "name": "Okta", "status": "coming_soon"})
    result.append({"provider": "crowdstrike", "name": "CrowdStrike", "status": "coming_soon"})

    return result


@router.post("/aws/validate")
def validate_aws_credentials(
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Validate AWS credentials without saving them.
    Returns the verified account identity on success.
    """
    account_id = config.get("account_id", "").strip()
    region = config.get("region", "us-east-1").strip()
    auth_method = config.get("auth_method", "access_key")
    role_arn = config.get("role_arn", "").strip() or None
    external_id = config.get("external_id", "").strip() or None
    access_key = config.get("access_key", "").strip() or None
    secret_key = config.get("secret_key", "").strip() or None

    if not account_id:
        raise HTTPException(status_code=400, detail="AWS Account ID is required.")
    if not region:
        raise HTTPException(status_code=400, detail="AWS Region is required.")

    try:
        if auth_method == "access_key":
            if not access_key or not secret_key:
                raise HTTPException(status_code=400, detail="Access Key ID and Secret Access Key are required.")
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        elif auth_method == "role_arn":
            if not role_arn:
                raise HTTPException(status_code=400, detail="Role ARN is required for IAM Role authentication.")
            # Use environment/instance credentials to assume the role
            base_sts = boto3.client('sts', region_name=region)
            assume_kwargs = {
                "RoleArn": role_arn,
                "RoleSessionName": "SentinelAI_Validation"
            }
            if external_id:
                assume_kwargs["ExternalId"] = external_id
            
            assumed = base_sts.assume_role(**assume_kwargs)
            creds = assumed['Credentials']
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'],
                region_name=region
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported auth_method: {auth_method}")

        identity = sts_client.get_caller_identity()
        verified_account = identity.get("Account", "")
        verified_arn = identity.get("Arn", "")
        verified_user_id = identity.get("UserId", "")

        return {
            "valid": True,
            "account_id": verified_account,
            "arn": verified_arn,
            "user_id": verified_user_id,
            "message": "Credentials validated successfully."
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"AWS Error ({error_code}): {error_msg}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")


@router.post("/aws")
def configure_aws_integration(
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Configure or update AWS CloudTrail integration.
    Validates credentials via STS before saving.
    """
    account_id = config.get("account_id", "").strip()
    region = config.get("region", "us-east-1").strip()
    auth_method = config.get("auth_method", "access_key")

    if not account_id or not region or not auth_method:
        raise HTTPException(status_code=400, detail="account_id, region, and auth_method are required.")

    role_arn = config.get("role_arn", "").strip() or None
    external_id = config.get("external_id", "").strip() or None
    access_key = config.get("access_key", "").strip() or None
    secret_key = config.get("secret_key", "").strip() or None

    # --- Validate credentials via STS before saving ---
    try:
        if auth_method == "access_key":
            if not access_key or not secret_key:
                raise HTTPException(status_code=400, detail="Access Key ID and Secret Access Key are required.")
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            sts_client.get_caller_identity()

        elif auth_method == "role_arn":
            if not role_arn:
                raise HTTPException(status_code=400, detail="Role ARN is required for IAM Role auth.")
            base_sts = boto3.client('sts', region_name=region)
            assume_kwargs = {
                "RoleArn": role_arn,
                "RoleSessionName": "SentinelAI_ConfigValidation"
            }
            if external_id:
                assume_kwargs["ExternalId"] = external_id
            assumed = base_sts.assume_role(**assume_kwargs)
            creds = assumed['Credentials']
            temp_sts = boto3.client(
                'sts',
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'],
                region_name=region
            )
            temp_sts.get_caller_identity()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported auth_method: {auth_method}")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=f"Credential validation failed ({error_code}): {error_msg}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Credential validation failed: {str(e)}")

    # --- Persist encrypted credentials ---
    credentials = {
        "role_arn": role_arn,
        "external_id": external_id,
        "access_key": access_key,
        "secret_key": secret_key
    }
    encrypted_creds = encrypt_credentials(credentials)

    integration = db.query(Integration).filter(
        Integration.workspace_id == workspace.id,
        Integration.provider == "aws"
    ).first()

    if not integration:
        integration = Integration(workspace_id=workspace.id, provider="aws")
        db.add(integration)

    integration.config = {
        "account_id": account_id,
        "region": region,
        "auth_method": auth_method,
        "has_external_id": bool(external_id)
    }
    integration.encrypted_credentials = encrypted_creds
    integration.status = "configured"
    integration.error_message = None
    db.commit()

    return {"message": "AWS Integration configured and validated successfully."}


def _run_aws_sync(integration_id: str, job_id: str):
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        integration = db.query(Integration).filter(Integration.id == integration_id).first()
        if not integration:
            return

        integration.status = "syncing"
        integration.error_message = None
        db.commit()

        credentials = decrypt_credentials(integration.encrypted_credentials)
        source = AwsCloudTrailSource(
            account_id=integration.config.get("account_id"),
            region=integration.config.get("region"),
            auth_method=integration.config.get("auth_method"),
            role_arn=credentials.get("role_arn"),
            external_id=credentials.get("external_id"),
            access_key=credentials.get("access_key"),
            secret_key=credentials.get("secret_key"),
            start_time=integration.last_sync_time
        )

        stats = execute_ingestion_pipeline(source, job_id, str(integration.workspace_id))

        integration.last_sync_time = datetime.now(timezone.utc)
        events_fetched = stats.get("total_events", 0)

        if events_fetched == 0:
            integration.status = "synced_no_new_events"
        else:
            integration.status = "success"
            integration.events_retrieved = (integration.events_retrieved or 0) + events_fetched

        db.commit()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync failed: {e}")
        if integration:
            integration.status = "error"
            integration.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/aws/sync")
def sync_aws_integration(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Trigger AWS CloudTrail sync in the background.
    """
    integration = db.query(Integration).filter(
        Integration.workspace_id == workspace.id,
        Integration.provider == "aws"
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="AWS Integration not configured.")

    if integration.status == "syncing":
        raise HTTPException(status_code=409, detail="A sync is already in progress.")

    job = IngestionJob(
        workspace_id=workspace.id,
        s3_bucket_name="aws-live-sync",
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_aws_sync, str(integration.id), str(job.job_id))

    return {"message": "Sync started", "job_id": str(job.job_id)}


# ── Generic connector configure endpoint ─────────────────────────────────
SUPPORTED_CONNECTORS = {"wazuh", "suricata", "openvas"}

@router.post("/{provider}/configure")
def configure_connector(
    provider: str,
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Configure a Wazuh, Suricata, or OpenVAS integration.
    Stores the configuration and encrypted credentials.
    """
    if provider not in SUPPORTED_CONNECTORS:
        raise HTTPException(status_code=400, detail=f"Unsupported connector: {provider}. Supported: {', '.join(SUPPORTED_CONNECTORS)}")

    # Separate credentials from plain config
    credential_fields = {"password", "secret_key", "access_key"}
    credentials = {k: v for k, v in config.items() if k in credential_fields and v}
    plain_config = {k: v for k, v in config.items() if k not in credential_fields}

    encrypted_creds = encrypt_credentials(credentials) if credentials else ""

    integration = db.query(Integration).filter(
        Integration.workspace_id == workspace.id,
        Integration.provider == provider
    ).first()

    if not integration:
        integration = Integration(workspace_id=workspace.id, provider=provider)
        db.add(integration)

    integration.config = plain_config
    integration.encrypted_credentials = encrypted_creds
    integration.status = "configured"
    integration.error_message = None
    db.commit()

    return {"message": f"{provider.capitalize()} integration configured successfully."}
