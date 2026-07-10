// Azure Functions: Linux Consumption (Y1) plan + Python 3.11 function app.
// Hosts the ingestion triggers (blob triggers on index-snapshots / weekly-reports
// and the daily catch-up sweep timer) — see functions/ at the repo root.

@description('Name of the Consumption (Y1) hosting plan.')
param planName string

@description('Name of the function app (globally unique).')
param functionAppName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Name of the storage account used for AzureWebJobsStorage and the ingestion containers (must exist in this resource group).')
param storageAccountName string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('SQL server FQDN (SQL_SERVER).')
param sqlServerFqdn string

@description('SQL database name (SQL_DATABASE).')
param sqlDatabaseName string

@description('Blob container watched for index snapshots (SNAPSHOT_CONTAINER).')
param snapshotContainer string = 'index-snapshots'

@description('Blob container watched for weekly reports (REPORT_CONTAINER).')
param reportContainer string = 'weekly-reports'

@description('NCRONTAB expression for the daily catch-up sweep (SWEEP_CRON).')
param sweepCron string = '0 0 6 * * *'

@description('Key Vault URI (KEY_VAULT_URI); optional fallback source for secrets.')
param keyVaultUri string = ''

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'FtpsOnly'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'SQL_SERVER'
          value: sqlServerFqdn
        }
        {
          name: 'SQL_DATABASE'
          value: sqlDatabaseName
        }
        {
          name: 'SNAPSHOT_CONTAINER'
          value: snapshotContainer
        }
        {
          name: 'REPORT_CONTAINER'
          value: reportContainer
        }
        {
          name: 'SWEEP_CRON'
          value: sweepCron
        }
        {
          name: 'STORAGE_CONNECTION'
          value: storageConnectionString
        }
        {
          name: 'KEY_VAULT_URI'
          value: keyVaultUri
        }
      ]
    }
  }
}

output functionAppName string = functionApp.name
output principalId string = functionApp.identity.principalId
output defaultHostName string = functionApp.properties.defaultHostName
