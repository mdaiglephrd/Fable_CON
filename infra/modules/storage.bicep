// StorageV2 account (LRS, TLS 1.2, no public blob access) + ingestion containers.

@description('Storage account name (3-24 chars, lowercase alphanumeric, globally unique).')
@maxLength(24)
param storageAccountName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Blob containers to create. The default deployment provisions: index-snapshots, weekly-reports, tag-exports, and document-text (raw text extracted by Document Intelligence, consumed by ingest/load_document_text.py). The concrete list is assembled in main.bicep.')
param containerNames array

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    accessTier: 'Hot'
    // Shared-key access stays on: the function app's AzureWebJobsStorage /
    // STORAGE_CONNECTION use the account connection string. Flip to false once
    // identity-based connections are configured (see README "Hardening").
    allowSharedKeyAccess: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for name in containerNames: {
    parent: blobService
    name: name
    properties: {
      publicAccess: 'None'
    }
  }
]

output storageAccountName string = storageAccount.name
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
