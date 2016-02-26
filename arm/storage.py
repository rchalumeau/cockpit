"""
Helper class to manage the sotarage account linked to an instanceGroup
"""
from azure.mgmt.storage.models import StorageAccount, StorageAccountCreateParameters, AccountType
from azure.mgmt.resource.features.models import GenericResourceFilter
import arm
import os
import logging
from azure.storage.blob import BlockBlobService, BlobPermissions
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StorageAccountBadArguments(Exception):
    pass

def format_date_time (t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')

class InstanceStorage(object):

    def __init__(self, group_name, location=None, create_if_not_exist=True):

        client = arm.instance()
        sm = client.storage.storage_accounts

        # Check existence of a storage account in the resource group
        # TODO : better with rm.list_resources for direct filtering
        # but issing doc on Genric filtering format
        # So, taking the first result of the iterator : Ouch !
        new=True
        for sa in sm.list_by_resource_group(group_name):
            new=False
            self.name = sa.name
            self.location=sa.location
            logger.debug("Found SA %s" % self.name)
            break

        if new:
            logger.info("Creating storage account...")
            #Generating unique name for Azure
            unique_name = "%s%s" % (
                    str(group_name).translate(None, '-_.').lower(),
                    arm.id_generator()
                )
            # TODO : Check how to deal with account type...
            # Warning : the name of the storageaccount cannot be > 24 chars
            self.location=location
            result = sm.create(
                group_name,
                unique_name[:24],
                StorageAccountCreateParameters(
                    location=self.location,
                    account_type=AccountType.standard_lrs
                )
            )

            # Asysnchronous operation, so wait...
            res = result.result()
            self.name = res.name

        # retrieve the keys and store them in the instance
        self.keys = sm.list_keys(group_name, self.name)
        logger.debug("Key1 : %s " % repr(self.keys.key1))
        logger.debug("Key2 : %s " % repr(self.keys.key2))

        # retrieve the blob service
        self.blob = BlockBlobService(
            account_name=self.name,
            account_key=self.keys.key1
        )
        # Define the storage tree :
        # sources for the images imported to create the VM
        # vhds for the VM images
        self.sources_container= "sources"
        self.vhds_container= "vhds"
        self.blob.create_container(self.sources_container)
        self.blob.create_container(self.vhds_container)

    def list_blobs(self):
        for blob in self.blob.list_blobs('system'):
            print(blob.name)

    def copy_source_images_from(self, source_storage, container, filepath):
        # Generate a token for 10 minutes read access
        token = source_storage.blob.generate_blob_shared_access_signature(
            container,
            filepath,
            BlobPermissions.READ,
            datetime.utcnow() + timedelta(minutes=10),
        )
        # Generate the sour URL of the blob
        source_url = source_storage.blob.make_blob_url(
            container,
            filepath,
            sas_token=token
        )
        # Launch the copy from the distant storage to the current one
        self.blob.copy_blob(
            self.sources_container,
            os.path.basename(filepath),
            source_url
        )

