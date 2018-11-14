import boto3
import logging

logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler()
logger_formatter = logging.Formatter("%(levelname)s::%(asctime)s %(message)s")

logger_handler.setFormatter(logger_formatter)

logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)


def lambda_handler(event, source):
    instance_ids = event["InstanceIds"]
    STOPPED = 80

    ec2 = boto3.resource("ec2")

    try:
        if len(instance_ids) < 1:
            raise RuntimeError("InstanceIds está vacío o no definido.")

        for ec2 in ec2.instances.filter(InstanceIds=instance_ids):
            if not ec2.id or not ec2.state["Code"] == STOPPED:
                continue

            ec2.start()

            logger.info(f"Iniciando instancia EC2 {ec2.id}. Listo!")
    except RuntimeError as e:
        logger.error(e, exc_info=True)

    return {"message": "Ok"}
