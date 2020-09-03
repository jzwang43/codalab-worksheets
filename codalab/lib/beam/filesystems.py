import os
from apache_beam.io.filesystems import FileSystems
from codalab.lib.beam.blobstoragefilesystem import BlobStorageFileSystem

"""
Modifies Beam to add support for Azure Blob Storage filesystems.

Based on work from https://github.com/apache/beam/pull/12581. Once that PR is added into Beam,
we will switch to using a Beam library instead.
"""

# Test key for Azurite (local development)
os.environ[
    'AZURE_STORAGE_CONNECTION_STRING'
] = 'DefaultEndpointsProtocol=https;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=https://127.0.0.1:10000/devstoreaccount1;'