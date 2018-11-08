import os

import boto3


def lambda_handler(event, source):
    EC2_INSTANCES = os.getenv("EC2_INSTANCE_IDS", "")
    STOPPED = 80

    ec2 = boto3.resource("ec2")

    instance_ids = [instance.strip() for instance in EC2_INSTANCES.split(',')]

    for ec2 in ec2.instances.filter(InstanceIds=instance_ids):
        if not ec2.id and not ec2.state.code == STOPPED:
            continue

        ec2.start()

    return {"message": "Ok"}


if __name__ == "__main__":
    lambda_handler(None, None)
