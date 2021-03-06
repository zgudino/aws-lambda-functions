import boto3
import os
import logging
import json
import re
from itertools import groupby

logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler()
logger_formatter = logging.Formatter("%(levelname)s::%(asctime)s %(message)s")

logger_handler.setFormatter(logger_formatter)

logger.addHandler(logger_handler)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: dict):
    """Elimina AMIs y Snapshots recursivamente cuando umbral de antiguedad es excedido.

    Parameters
    ----------
    event: dict
        JSON con llave `InstanceIds` cuyo valor es una lista de AMI IDs.
        ```json
        {
          "InstanceIds": ["i-0e68a8e32921d400f", "..."]
        }
        ```
    context: dict
        [Modelo de ejecucion de AWS Lambda](https://docs.aws.amazon.com/es_es/lambda/latest/dg/running-lambda-code.html)

    Returns
    -------
    dict
        Simple respuesta {"message": "Ok"}
    """

    # Conserva ultima n AMIs. RESTRAIN_DAYS se obtiene de variable de entorno runtime y/o SO
    RESTRAIN_DAYS = os.getenv("RESTRAIN_DAYS", 2)
    PURGE = os.getenv("PURGE", "N")

    instance_ids = event.get("InstanceIds", [])  # Lista de instancias EC2
    restrain_days = int(RESTRAIN_DAYS)

    # True si, solamente si, PURGE es exactamente S-s-Y-y-1; i.e. "Nn" es False, sin embargo, "Y", o "y" es True
    purge = True if re.match(r"^[SsYy1]$", PURGE) else False

    def pluck_instance_id(image: dict) -> str:
        """Calcula un valor clave para cada elemento.

        Proposito de esta funcion es tomar un `dict`, transformar (si aplica) y devolver la llave de comparacion para
        High Order Function tales como sorted, groupby, etc...

        Parameters
        ----------
            image: dict
                Recurso de imagen EC2 representado libremente como tipo `dict`.

        Returns
        -------
            str
                EC2 Instance ID
        """

        # Ver https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Image.tags
        for tag in image.get('tags', []):
            # Convierte SOLO valores de `dict` a `tuple` –e.g. ('IntanceID', 'i-00997a5147c22cd03')
            values = tuple(tag.values())

            # Rompe iterador actual si valor 'InstanceID' no existe en `tuple` devolviendo control al proximo tag
            if "InstanceID" not in values:
                continue

            # `values` es convertido a `dict` devolviendo valor de 'InstanceID'
            return dict([values]).get('InstanceID')

    common_tag = [{"Name": "is-public", "Values": ["false"]}]  # AMIs privadas
    purge_tag = [{"Name": "tag-key", "Values": ["InstanceID"]}]  # AMIs con etiquetas EC2
    instances_tag = [{"Name": "tag:InstanceID", "Values": instance_ids}]  # AMIs con especificos EC2

    filters = common_tag + (purge_tag if purge else instances_tag)

    ec2 = boto3.resource("ec2")

    try:
        if not purge and len(instance_ids) < 1:
            raise RuntimeError("InstanceIds está vacío o no definido.")
    except RuntimeError as e:
        logger.error(e, exc_info=True)
        return

    # Resultado es una `list` de `dict` con atributos `image_id`, `creation_date` y `tags` del recurso EC2 Image
    amis = [
        {
            "image_id": image.image_id,
            "creation_date": image.creation_date,
            "tags": image.tags
        }
        for image in ec2.images.filter(Filters=filters)
    ]

    ordered_amis = sorted(amis, key=pluck_instance_id)

    # Ver https://docs.python.org/3.7/library/itertools.html#itertools.groupby
    grouped_amis = groupby(ordered_amis, key=pluck_instance_id)

    for k, g in grouped_amis:
        amis_ordered_by_creation_date = sorted(list(g), key=lambda i: i['creation_date'])
        j = None if purge else (-1 * restrain_days)  # j == end; s[[begin[: end]]]
        unwanted_amis = amis_ordered_by_creation_date[:j]  # AMIs para eliminar; No rebana (slice) si `j == None`

        if len(unwanted_amis) < 1:
            continue

        logger.info("--------------------AMIs-----------------------")
        logger.info("\n%s" % json.dumps(unwanted_amis, indent=2))

        for ami in ec2.images.filter(ImageIds=[ami.get("image_id") for ami in unwanted_amis]):
            blocks = ami.block_device_mappings

            logger.info(f"Desregistrando AMI {ami.image_id}. Listo!")

            ami.deregister()

            for block in blocks:
                snapshot_id = block.get("Ebs", {}).get("SnapshotId")

                if not snapshot_id:
                    continue

                snapshot = ec2.Snapshot(snapshot_id)

                logger.info(f"Eliminando Snapshot {snapshot_id}. Listo!")

                snapshot.delete()

        logger.info("-----------------------------------------------")

    return {"message": "Ok"}
