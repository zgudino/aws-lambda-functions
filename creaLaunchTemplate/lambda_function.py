import json
import time
import boto3
import logging
from functools import reduce
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler()
logger_formatter = logging.Formatter("%(message)s")

logger_handler.setFormatter(logger_formatter)

logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: dict):
    """Crea EC2 Launch Templates.

    Parameters
    ----------
    event: dict
        Contiene una lista de tipo Amazon SQS Message incrustrado en campo Records. Internamente solo campo `body`es de
        interes particular; demas son ignorados.

        e.g.

        ```json
        {
          "Records": [
            {
              "messageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
              "receiptHandle": "MessageReceiptHandle",
              "body": "{\"Images\": [{\"Id\": \"ami-0ba641b97631f366f\", \"InstanceId\": \"i-0e68a8e32921d400f\"}]}",
              "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1523232000000",
                "SenderId": "123456789012",
                "ApproximateFirstReceiveTimestamp": "1523232000001"
              },
              "messageAttributes": {},
              "md5OfBody": "7b270e59b47ff90a553787216d55d91d",
              "eventSource": "aws:sqs",
              "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
              "awsRegion": "us-east-1"
            }
          ]
        }
        ```
    context: dict
        Objeto `context` AWS Lambda. A través de este objeto context, el código puede interactuar con AWS Lambda.
        Por ejemplo, el código puede encontrar el tiempo que falta para que AWS Lambda
        finalice la ejecución de la función de Lambda.
    """
    records = event.get("Records", [])
    body = [json.loads(record["body"]) for record in records if len(records) > 0]
    images = reduce(lambda a, c: a + c.get("Images", []), body, [])

    # Nada que hacer si `images` es vacio o nada (None)
    if not images:
        return

    try:
        client = boto3.client("ec2")

        for image in images:
            image_id = image["Id"]
            instance_id = image["InstanceId"]

            # Launch Templates cuya etiqueta tenga llave "ImageID" y valor "ami-xxx"
            filters = [
                {
                    "Name": "tag:ImageID",
                    "Values": [f"{image_id}"]
                }
            ]
            launch_templates = (client.describe_launch_templates(Filters=filters)).get("LaunchTemplates", [])

            if launch_templates:
                logger.warning(f"Omitir {image_id}.")

                continue

            yyyymmdd = time.strftime("%Y%m%d")
            hhmmss = time.strftime("%H%M%S")

            name = f"LT_{instance_id}_{yyyymmdd}_{hhmmss}"
            data = (client.get_launch_template_data(InstanceId=instance_id)).get("LaunchTemplateData", {})

            # Asigna AMI id. De no asignar "explicitamente" AMI id tomara aquel devuelto por `get_launch_template_date`.
            data["ImageId"] = image_id

            launch_template_response = client.create_launch_template(LaunchTemplateName=name, LaunchTemplateData=data)
            launch_template = launch_template_response["LaunchTemplate"]
            launch_template_id = launch_template["LaunchTemplateId"]

            resources = [launch_template_id]
            tags = [
                {
                    "Key": "ImageID",
                    "Value": image_id
                },
                {
                    "Key": "InstanceID",
                    "Value": instance_id
                }
            ]

            client.create_tags(Resources=resources, Tags=tags)

            logger.info(f"Creado {launch_template_id}.")
    except ClientError as error:
        raise error
