// Azure SQL logical server (Entra-only auth) + serverless database + firewall.
//
// NOTE: database access for managed identities is NOT grantable via ARM.
// After deployment, connect as the Entra admin and run
// CREATE USER [<app-name>] FROM EXTERNAL PROVIDER — exact T-SQL in infra/README.md.

@description('Name of the SQL logical server (globally unique).')
param serverName string

@description('Name of the application database.')
param databaseName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Login (display) name of the Entra administrator.')
param adminLogin string

@description('Object ID of the Entra administrator.')
param adminObjectId string

@description('Tenant ID of the Entra administrator.')
param adminTenantId string = tenant().tenantId

@description('Principal type of the Entra administrator.')
@allowed(['User', 'Group', 'Application'])
param adminPrincipalType string = 'Group'

@description('Allow public network access (plus the AllowAzureServices rule). Hardening path: private endpoints — see README.')
param enablePublicNetworkAccess bool = true

@description('Maximum database size in bytes (default 32 GB).')
param maxSizeBytes int = 34359738368

@description('Serverless auto-pause delay in minutes (-1 disables auto-pause).')
param autoPauseDelayMinutes int = 60

@description('Serverless minimum vCores (as a decimal string, e.g. "0.5").')
param minCapacity string = '0.5'

resource sqlServer 'Microsoft.Sql/servers@2023-08-01' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: enablePublicNetworkAccess ? 'Enabled' : 'Disabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: adminLogin
      sid: adminObjectId
      tenantId: adminTenantId
      principalType: adminPrincipalType
    }
  }
}

// GP_S_Gen5_1: General Purpose serverless, Gen5, 1 vCore max.
resource database 'Microsoft.Sql/servers/databases@2023-08-01' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: maxSizeBytes
    autoPauseDelay: autoPauseDelayMinutes
    minCapacity: json(minCapacity)
    zoneRedundant: false
    requestedBackupStorageRedundancy: 'Local'
  }
}

// 0.0.0.0 - 0.0.0.0 is the special "allow Azure services" rule (required for the
// Function App / Web App outbound connections while public access is enabled).
resource allowAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01' = if (enablePublicNetworkAccess) {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output serverName string = sqlServer.name
output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
