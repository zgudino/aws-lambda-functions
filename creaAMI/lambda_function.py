import json
import boto3
import time
import sys
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler()
logger_formatter = logging.Formatter("%(levelname)s::%(asctime)s %(message)s")

logger_handler.setFormatter(logger_formatter)

logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)

ec2Obj = boto3.client('ec2')


def lambda_handler(event, context):
    try:
        sourceInstanceId = event['InstanceID']
        Date = time.strftime("%Y%m%d")
        Time = time.strftime("%H%M%S")
        amiName = "AMIautobak_%s_%s%s" % (sourceInstanceId, Date, Time)
        configName = "AMIautobak_%s_%s%s" % (sourceInstanceId, Date, Time)

        CreateNewImage = ec2Obj.create_image(
            InstanceId=sourceInstanceId,
            Name=amiName,
            Description='Automatically Created Image from Lambda Service from instance "%s"' % (sourceInstanceId),
            NoReboot=True)

        image_id = CreateNewImage["ImageId"]
        tag = {"Key": "InstanceID", "Value": sourceInstanceId}

        logger.info(f"Creando AMI {CreateNewImage['ImageId']}. Listo!")

        # Etiqueta establece relacion entre Instancia EC2 y AMI
        ec2Obj.create_tags(Resources=[image_id], Tags=[tag])

        logger.info(f"Agregando etiqueta {tag} al AMI {image_id}. Listo!")

        Image = []

        Image.append(CreateNewImage)

        def getCreatedID(Image):
            for i in Image:
                ID = i['ImageId']
                return ID

        AMINewID = getCreatedID(Image)

        return 'A new AMI has been Created `%s` whith ID `%s`.' % (amiName, AMINewID)
    except (RuntimeError, ClientError) as e:
        logger.error(e, exc_info=True)
