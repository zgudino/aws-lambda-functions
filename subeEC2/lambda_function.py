import boto3


def lambda_handler(event, source):
    instance_ids = event["InstanceIds"]
    STOPPED = 80

    ec2 = boto3.resource("ec2")

    for ec2 in ec2.instances.filter(InstanceIds=instance_ids):
        if not ec2.id or not ec2.state["Code"] == STOPPED:
            continue

        ec2.start()

    return {"message": "Ok"}
