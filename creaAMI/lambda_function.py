import json
import boto3
import time
import sys

ec2Obj = boto3.client('ec2')


def lambda_handler(event, context):
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

    # Etiqueta establece relacion entre Instancia EC2 y AMI
    ec2Obj.create_tags(Resources=[CreateNewImage["ImageId"]], Tags=[{"Key": "InstanceID", "Value": sourceInstanceId}])

    Image = []

    Image.append(CreateNewImage)

    def getCreatedID(Image):
        for i in Image:
            ID = i['ImageId']
            return ID

    AMINewID = getCreatedID(Image)

    return 'A new AMI has been Created `%s` whith ID `%s`.' % (amiName, AMINewID)
