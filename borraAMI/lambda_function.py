import boto3
import os
import logging
import json
from itertools import groupby

"""Elimina EC2 AMIs recursivamente cuya antiguedad excede umbral deseado.

Parameters:
    event (dict): Data del evento.
    context (LambdaContext): Informacion del runtime.
    
Returns:
    dict: Simple respuesta {'message': 'Ok'}.
"""


def lambda_handler(event, context):
    # Conserva ultima n AMIs. AMI_RESTRAIN_DAYS se obtiene de variable de entorno runtime y/o
    # SO -e.g. bash$ export AMI_RESTRAIN_DAYS=10
    AMI_RESTRAIN_DAYS = os.getenv("AMI_RESTRAIN_DAYS", 2)

    """Calcula un valor clave para cada elemento.
    
    Proposito de esta funcion es tomar un `dict`, transformar (si aplica) y devolver la llave de comparacion para
    High Order Function tales como sorted, groupby, etc...
    
    Parameters:
        image (dict): Un recurso de imagen EC2 representado libremente como tipo `dict`.
    
    Returns:
        str: EC2 Instance ID
    """

    def image_instance_id(image: dict) -> str:
        # Ver https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Image.tags
        for tag in image.get('tags', []):
            # Convierte SOLO valores de `dict` a `tuple` –e.g. ('IntanceID', 'i-00997a5147c22cd03')
            values = tuple(tag.values())

            # Rompe iterador actual si valor 'InstanceID' no existe en `tuple` devolviendo control al proximo tag
            if "InstanceID" not in values:
                continue

            # `values` es convertido a `dict` devolviendo valor de 'InstanceID'
            return dict([values]).get('InstanceID')

    # Configuracion basica de sistema logging
    logging.basicConfig(level=logging.INFO,
                        format="[%(levelname)s] %(asctime)s :: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    # Aplica filtros contra coleccion de AMIs
    filters = [
        # AMIs privadas
        {
            "Name": "is-public",
            "Values": ["false"]
        },
        # AMIs posee llave 'InstanceID'
        {
            "Name": "tag-key",
            "Values": ["InstanceID"]
        }
    ]
    ec2 = boto3.resource("ec2")

    # Resultado es una `list` de `dict` con atributos `image_id`, `creation_date` y `tags` del recurso EC2 Image
    amis = [{"image_id": image.image_id, "creation_date": image.creation_date, "tags": image.tags} for image in
            ec2.images.filter(Filters=filters)]

    ordered_amis = sorted(amis, key=image_instance_id)

    # Ver https://docs.python.org/3.7/library/itertools.html#itertools.groupby
    grouped_amis = groupby(ordered_amis, key=image_instance_id)

    for k, g in grouped_amis:
        amis_ordered_by_creation_date = sorted(list(g), key=lambda e: e['creation_date'])
        unwanted_amis = amis_ordered_by_creation_date[:(-1 * AMI_RESTRAIN_DAYS)]  # AMIs para eliminar

        if len(unwanted_amis) < 1:
            continue

        logging.info("--------------------AMIs-----------------------")
        logging.info("\n%s" % json.dumps(unwanted_amis, indent=2))

        for ami in ec2.images.filter(ImageIds=[ami.get("image_id") for ami in unwanted_amis]):
            blocks = ami.block_device_mappings

            logging.info(f"Desregistrar AMI {ami.image_id} (Listo)")

            ami.deregister()

            for block in blocks:
                snapshot_id = block.get("Ebs", {}).get("SnapshotId")
                snapshot = ec2.Snapshot(snapshot_id)

                logging.info(f"Eliminar Snapshot {snapshot_id} (Listo)")

                snapshot.delete()

        logging.info("-----------------------------------------------")

    return {"message": "Ok"}