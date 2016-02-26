from msrestazure.azure_active_directory import ServicePrincipalCredentials
from azure.mgmt.resource.resources import ResourceManagementClient, ResourceManagementClientConfiguration
from azure.mgmt.compute import ComputeManagementClient, ComputeManagementClientConfiguration
from azure.mgmt.network import NetworkManagementClient, NetworkManagementClientConfiguration
from azure.mgmt.storage import StorageManagementClient, StorageManagementClientConfiguration
import os
import json
import logging
import string
import random

logger = logging.getLogger(__name__)

# Generates a ramdom string for names unicity safety
def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class Client(object):
    """
    Class to store as a singleton the clients to access the resources compute,
    network, ...
    """
    def __init__(self, conf="../authent.json"):
        with open(conf) as f:
            data = json.load(f)

        # Get the AD authent
        logger.info("Connecting to AD...")
        credentials = ServicePrincipalCredentials(
            data["clientid"],
            data["secret"],
            token_uri=data["tokenuri"]
        )
        # Client to access resources
        logger.info("Creating ResourceManagementClient...")
        self.resource = ResourceManagementClient(
            ResourceManagementClientConfiguration(
                credentials,
                data["subscriptionid"]
            )
        )
        # Registering the needed pproviders
        self.resource.providers.register('Microsoft.Compute')
        self.resource.providers.register('Microsoft.Network')
        self.resource.providers.register('Microsoft.Storage')

        # Compute client
        logger.info("Creating ComputeManagementClient...")
        self.compute = ComputeManagementClient(
            ComputeManagementClientConfiguration(
                credentials,
                data["subscriptionid"]
            )
        )
        # Network client
        logger.info("Creating NetworkManagementClient...")
        self.network = NetworkManagementClient(
            NetworkManagementClientConfiguration(
                credentials,
                data["subscriptionid"]
            )
        )
        # Storage client
        logger.info("Creating StorageManagementClient...")
        self.storage = StorageManagementClient(
            StorageManagementClientConfiguration(
                credentials,
                data["subscriptionid"]
            )
        )

# Single instance of the client
INSTANCE = None

# Helper to get the instance of client
# Need this function to pass some relative path of conffiles
def instance(conffile=None):
    global INSTANCE
    # INit INstance if not already done
    if INSTANCE is None and conffile is not None:
        INSTANCE = Client(os.path.abspath(conffile))
    return INSTANCE

