import boto3
from botocore.exceptions import ClientError

import logging

logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler()
logger_formatter = logging.Formatter("%(levelname)s::%(asctime)s %(message)s")

logger_handler.setFormatter(logger_formatter)

logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    db_instance_ids = event.get("DBInstanceIds", [])

    rds = boto3.client("rds")

    filters = [
        {
            "Name": "db-instance-id",
            "Values": db_instance_ids
        }
    ]

    try:
        if not db_instance_ids:
            raise RuntimeError("`DBInstanceIds` está vacío o no definido.")

        db_instances = (rds.describe_db_instances(Filters=filters)).get("DBInstances", [])
        db_instances_with_status = filter(lambda instance: instance["DBInstanceStatus"] == "available", db_instances)

        for db_instance in db_instances_with_status:
            if not db_instance:
                continue

            db_instance_id = db_instance["DBInstanceIdentifier"]
            db_instance_action_response = rds.stop_db_instance(DBInstanceIdentifier=db_instance_id)

            if db_instance_action_response:
                logger.info(f"Deteniendo RDS {db_instance['DBInstanceIdentifier']}.")
    except ClientError as error:
        logger.error(error, exc_info=True)

    return {"message": "Ok"}
