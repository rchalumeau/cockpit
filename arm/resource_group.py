from azure.mgmt.resource.resources.models import ResourceGroup
import arm
import logging
from arm.storage import InstanceStorage
import copy

logger = logging.getLogger(__name__)

class InstanceGroupBadArguments(Exception):
    pass



""" An instance Group is a ResourceGroup holding a dedicated storage account
    So that resources, vm images and vhds are stored in a unit that can be handled
    all together.
"""
class InstanceGroup(ResourceGroup):

    def __init__(self, name, location=None):

        client = arm.instance()
        rm = client.resource.resource_groups

        # RG defined in Azure, return itself
        if rm.check_existence(name):
            logger.debug("RG %s exists..." % name)
            rg = rm.get(name)

        # Create a new one
        elif location is not None:
            logger.debug("RG %s does not exists so to be created" % name)
            if location is not None:
                rg = rm.create_or_update(
                    name,
                    ResourceGroup(
                        location=location
                    )
                )

        # Does not exist, and not enough information to create it
        # Eror case
        # TODO: Shall trigger an exception, this case should not occur
        else:
            msg = "RG %s does not exists and location is missing to create it" % name
            logger.error(msg)
            raise InstanceGroupBadArguments(msg)
            
        # Copy the rg instance as itself
        self.__dict__ = copy.deepcopy(rg.__dict__)

        # Now deal with the dedicated StorageAccount
        # Retrieve RG dedicated storage
        # Per convenience, an instanceGroup must have only one storage
        # account
        self.storage = InstanceStorage(self.name, self.location)
        logger.debug("Storage account : " + self.storage.name)

