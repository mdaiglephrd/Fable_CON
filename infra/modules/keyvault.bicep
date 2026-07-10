// Key Vault with RBAC authorization and soft delete.
// Secrets (SEARCH-API-KEY, AZURE-OPENAI-API-KEY, ...) are created out-of-band —
// never in Bicep. See infra/README.md "Put secrets in Key Vault".

@description('Key Vault name (3-24 chars, globally unique).')
@minLength(3)
@maxLength(24)
param keyVaultName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Enable purge protection. Irreversible once on — leave off for dev/test so the vault name can be reclaimed after delete+purge.')
param enablePurgeProtection bool = false

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    // enablePurgeProtection may only be true or omitted (false is rejected).
    enablePurgeProtection: enablePurgeProtection ? true : null
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
