import boto3


def lambda_handler(event, source):
    instance_ids = event["InstanceIds"]
    RUNNING = 16

    ec2 = boto3.resource("ec2")

    for ec2 in ec2.instances.filter(InstanceIds=instance_ids):
        if not ec2.id or not ec2.state["Code"] == RUNNING:
            continue

        ec2.stop()

    return {"message": "Ok"}
